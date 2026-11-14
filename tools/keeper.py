"""Orbis session keeper: hold the single Orbis Dynamic session for a limited time, so your
own commands (the web page, tools/orbis_test.py --attach) can attach to it one after
another without ever giving the server up in between.

    tools/.venv/bin/python tools/keeper.py start     # wait for capacity, hold for 1 h
    tools/.venv/bin/python tools/keeper.py status
    tools/.venv/bin/python tools/keeper.py extend    # reset the clock to 1 h from now
    tools/.venv/bin/python tools/keeper.py release   # end the session now

Rules (agreed with the user 2026-11-14):
- One hold lasts at most HOLD_SECONDS (1 h). It is released when the time runs out, not
  when idle. `extend` is an explicit action that moves the deadline to 1 h from *now* -- it
  never stacks beyond that.
- The session itself is created with a hard ceiling (SESSION_CEILING_SECONDS) so that even
  a crashed keeper cannot hold it longer than that. Past the ceiling, start a new hold.
- While held, Dynamic is unavailable to everyone else on Reactor and billing runs
  ($1.254/min even idle). `status` always reports time left and cost so far.

The keeper owns the session; clients adopt it with a token bound to the session id
(`/api/token?attach=1` in the web dev server). When a client disconnects, only its own
connection closes; the keeper's session stays.
"""

import argparse
import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from marble_pano import load_env  # noqa: E402

MODELS = {"dynamic": ("reactor/visko-orbis-dynamic", 1.254), "stable": ("reactor/visko-orbis-stable", 0.582)}
# USD per minute, docs.reactor.inc/resources/billing (2026-11-14). Stable is only for testing the
# keeper itself: it has spare capacity, but it does not hold the reference (see CLAUDE.md).
HOLD_SECONDS = 3600
SESSION_CEILING_SECONDS = 3 * 3600
PORT = 5199
STATE_DIR = ROOT / ".keeper"
STATE = STATE_DIR / "state.json"
LOG = STATE_DIR / "keeper.log"


def write_state(**kw):
    STATE_DIR.mkdir(exist_ok=True)
    cur = read_state()
    cur.update(kw, updated_at=time.time())
    STATE.write_text(json.dumps(cur, indent=1))


def read_state():
    try:
        return json.loads(STATE.read_text())
    except (OSError, ValueError):
        return {}


def summary(st):
    now = time.time()
    if st.get("phase") != "holding":
        return {k: st.get(k) for k in ("phase", "detail", "session_id", "pid")}
    held = now - st["ready_at"]
    price = MODELS[st.get("model_key", "dynamic")][1]
    return {
        "phase": "holding",
        "session_id": st["session_id"],
        "model": MODELS[st.get("model_key", "dynamic")][0],
        "minutes_left": round((st["hold_until"] - now) / 60, 1),
        "hold_until": time.strftime("%H:%M:%S", time.localtime(st["hold_until"])),
        "held_minutes": round(held / 60, 1),
        "cost_so_far_usd": round(held / 60 * price, 2),
        "ceiling_at": time.strftime("%H:%M:%S", time.localtime(st["ready_at"] + SESSION_CEILING_SECONDS)),
        "pid": st.get("pid"),
    }


# ---------------------------------------------------------------- daemon ("run") ---

async def run_daemon(wait_minutes, model_key):
    from reactor_sdk import RateLimitedError, Reactor

    load_env()
    model, price = MODELS[model_key]
    write_state(phase="waiting", detail=f"waiting for {model} capacity", pid=os.getpid(), session_id=None,
                model_key=model_key)
    deadline = time.time() + wait_minutes * 60
    while True:
        r = Reactor(model_name=model, api_key=os.environ["REACTOR_API_KEY"],
                    max_session_duration_seconds=SESSION_CEILING_SECONDS)
        try:
            await asyncio.wait_for(r.connect(), 90)
            break
        except RateLimitedError:
            if time.time() > deadline:
                write_state(phase="failed", detail=f"no capacity within {wait_minutes} min")
                return
            write_state(detail=f"busy elsewhere, retrying ({time.strftime('%X')})")
            await asyncio.sleep(15)

    ready_at = time.time()
    write_state(phase="holding", detail="holding", session_id=r.get_session_id(),
                ready_at=ready_at, hold_until=ready_at + HOLD_SECONDS)
    log(f"holding session {r.get_session_id()} until {time.strftime('%X', time.localtime(ready_at + HOLD_SECONDS))}")

    stop = asyncio.Event()

    async def handle(reader, writer):
        try:
            line = (await reader.readline()).decode().split()
            while (await reader.readline()) not in (b"\r\n", b"\n", b""):
                pass  # skip headers
            method, path = (line + ["", ""])[:2]
            st = read_state()
            if method == "GET" and path == "/status":
                body = summary(st)
            elif method == "POST" and path == "/extend":
                new_until = min(time.time() + HOLD_SECONDS, st["ready_at"] + SESSION_CEILING_SECONDS - 60)
                write_state(hold_until=new_until)
                log(f"extended to {time.strftime('%X', time.localtime(new_until))}")
                body = summary(read_state())
            elif method == "POST" and path == "/release":
                stop.set()
                body = {"phase": "releasing"}
            else:
                body = {"error": "GET /status, POST /extend, POST /release"}
            data = json.dumps(body).encode()
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
                         + f"Content-Length: {len(data)}\r\nConnection: close\r\n\r\n".encode() + data)
            await writer.drain()
        finally:
            writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", PORT)
    for sig in (signal.SIGTERM, signal.SIGINT):
        asyncio.get_running_loop().add_signal_handler(sig, stop.set)
    warned = set()
    try:
        while not stop.is_set():
            left = read_state().get("hold_until", 0) - time.time()
            if left <= 0:
                log("hold time is up; releasing")
                break
            for mark in (600, 300, 60):
                if left <= mark and mark not in warned:
                    warned.add(mark)
                    log(f"{int(left // 60)} min left -- `keeper.py extend` to keep the session")
            if str(getattr(r.get_status(), "value", r.get_status())).lower().endswith("disconnected"):
                log("session ended from outside")
                break
            try:
                await asyncio.wait_for(stop.wait(), 5)
            except asyncio.TimeoutError:
                pass
    finally:
        server.close()
        st = read_state()
        held = time.time() - st.get("ready_at", time.time())
        await r.disconnect()  # the owner disconnecting ends the session (and its billing)
        write_state(phase="released", detail=f"released after {held / 60:.1f} min, ~${held / 60 * price:.2f}")
        log(read_state()["detail"])


def log(msg):
    print(f"[{time.strftime('%X')}] {msg}", flush=True)


# ---------------------------------------------------------------- CLI ---

def call(method, path):
    import urllib.request
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", method=method)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except (OSError, TypeError):
        return False


def cmd_start(args):
    st = read_state()
    if st.get("phase") in ("waiting", "holding") and alive(st.get("pid")):
        print(json.dumps(summary(st), indent=1))
        sys.exit("a keeper is already running")
    STATE_DIR.mkdir(exist_ok=True)
    with open(LOG, "a") as logf:
        proc = subprocess.Popen([sys.executable, __file__, "run", "--wait-minutes", str(args.wait_minutes),
                                 "--model", args.model],
                                stdout=logf, stderr=subprocess.STDOUT, start_new_session=True, cwd=ROOT)
    write_state(phase="starting", pid=proc.pid, session_id=None, detail="starting")
    t0 = time.time()
    last = None
    while time.time() - t0 < args.wait_minutes * 60 + 120:
        st = read_state()
        if st.get("detail") != last:
            last = st.get("detail")
            print(f"[{time.strftime('%X')}] {st.get('phase')}: {last}", flush=True)
        if st.get("phase") in ("holding", "failed", "released") or not alive(proc.pid):
            break
        time.sleep(2)
    print(json.dumps(summary(read_state()), indent=1))


def cmd_status(_):
    st = read_state()
    out = summary(st)
    if st.get("phase") == "holding" and not alive(st.get("pid")):
        out["warning"] = "keeper process is gone but the session may still be open -- run `release`"
    print(json.dumps(out, indent=1))


def cmd_extend(_):
    st = read_state()
    if st.get("phase") != "holding":
        sys.exit(f"nothing to extend: keeper is {st.get('phase', 'not running')} ({st.get('detail', '')})")
    try:
        print(json.dumps(call("POST", "/extend"), indent=1))
    except OSError:
        sys.exit("keeper control API not reachable; `status` shows whether the process is gone")


def cmd_release(_):
    st = read_state()
    try:
        call("POST", "/release")
        for _ in range(30):
            time.sleep(1)
            if read_state().get("phase") == "released":
                break
    except OSError:
        # Keeper process is gone: end the session directly with the API key.
        sid = st.get("session_id")
        if sid:
            import urllib.request
            load_env()
            req = urllib.request.Request(f"https://api.reactor.inc/sessions/{sid}", method="DELETE",
                                         headers={"Authorization": f"Bearer {os.environ['REACTOR_API_KEY']}"})
            try:
                urllib.request.urlopen(req, timeout=20)
            except Exception as e:  # already closed is fine
                print(f"DELETE {sid}: {e}")
            write_state(phase="released", detail="released by DELETE (keeper process was gone)")
    print(json.dumps(summary(read_state()), indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start")
    s.add_argument("--wait-minutes", type=float, default=15, help="how long to wait for Dynamic capacity")
    s.add_argument("--model", choices=list(MODELS), default="dynamic", help="stable only to test the keeper")
    sub.add_parser("status")
    sub.add_parser("extend")
    sub.add_parser("release")
    r = sub.add_parser("run")  # the daemon itself; started by `start`
    r.add_argument("--wait-minutes", type=float, default=15)
    r.add_argument("--model", choices=list(MODELS), default="dynamic")
    args = ap.parse_args()
    if args.cmd == "run":
        asyncio.run(run_daemon(args.wait_minutes, args.model))
    else:
        {"start": cmd_start, "status": cmd_status, "extend": cmd_extend, "release": cmd_release}[args.cmd](args)


if __name__ == "__main__":
    main()
