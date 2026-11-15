"""Run a scene's single Orbis stream headless and record what happens.

    tools/.venv/bin/python tools/orbis_test.py hillside [--seconds 60]

Uploads reference.png (tools/pano_reference.py) and the scene's orbis.pano.opening prompt,
starts, optionally sends steering prompts on a schedule. Writes to
~/Assets/LivingRoom/scenes/<scene>/tests/pano-<time>/:
  events.jsonl   every model message with seconds since start
  frames/        snapshots (first frame, then on a schedule)
  report.json    first-frame latency, fps, delivered size, drift vs reference
  recording.mp4  server-side recording of the run, if the recorder is enabled
Needs REACTOR_API_KEY in .env.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
from reactor_sdk import RateLimitedError, Reactor

sys.path.insert(0, str(Path(__file__).resolve().parent))
from marble_pano import ASSETS, load_env  # noqa: E402

SNAP_AT = [5, 10, 20, 30, 40, 50, 60, 70, 80, 88, 100, 120]

# State changes sent mid-run (seconds after start). One change each, written as a
# transition from the current scene, per the Orbis prompt guide.
# Default schedule (seconds after start -> scene event label from orbis.pano.events).
# Override with --steer "35:Golden hour,65:Evening".
STEER_DEFAULT = "35:Golden hour,65:Evening"


def top(img_small):
    """Upper 38% of a small frame: sky and far mountains, which should not change if the camera is still."""
    return img_small[: int(img_small.shape[0] * 0.38)]


def seam(img_small):
    """Mean |left 2 columns - right 2 columns|: the two frame edges meet behind the viewer."""
    return float(np.abs(img_small[:, :2] - img_small[:, -2:][:, ::-1]).mean())


def small(img, size=(208, 120)):
    return np.asarray(Image.fromarray(img).convert("RGB").resize(size, Image.BILINEAR), dtype=np.float32)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("--seconds", type=float, default=80)
    ap.add_argument("--model", choices=["stable", "dynamic"], default="dynamic")
    ap.add_argument("--passthrough", action="store_true", help="skip the server-side prompt rewrite")
    ap.add_argument("--no-steer", action="store_true", help="do not send the mid-run steering prompts")
    ap.add_argument("--tag", default="", help="suffix for the output folder")
    ap.add_argument("--steer", default=STEER_DEFAULT, help="'sec:Event label,...' from orbis.pano.events")
    ap.add_argument("--prompt", default="opening", help="'opening' or a key of orbis.pano.variants")
    ap.add_argument("--record", action="store_true",
                    help="after the run, wait for the server recording (the session stays billed while waiting)")
    ap.add_argument("--seed", type=int, help="set_seed before start (server default 42)")
    ap.add_argument("--steer-every", type=float, help="re-send --steer-text every N seconds")
    ap.add_argument("--steer-text", default="The camera stays fixed on its tripod.")
    ap.add_argument("--wait-minutes", type=float, default=5, help="keep retrying while Dynamic is busy")
    ap.add_argument("--reference", help="anchor on this image instead of the scene's reference.png (e.g. custom/<id>.jpg)")
    ap.add_argument("--prompt-text", help="use this prompt text instead of --prompt")
    args = ap.parse_args()
    model = f"reactor/visko-orbis-{args.model}"

    load_env()
    scene_dir = ASSETS / args.scene
    ref_path = Path(args.reference).expanduser() if args.reference else scene_dir / "reference.png"
    if not ref_path.is_absolute():
        ref_path = scene_dir / ref_path
    cfg = json.loads((Path(__file__).resolve().parent.parent / "scenes" / args.scene / "scene.json").read_text())
    pano_cfg = cfg["orbis"]["pano"]
    prompt = args.prompt_text or (pano_cfg["opening"] if args.prompt == "opening" else pano_cfg["variants"][args.prompt])
    tag = f"-{args.tag}" if args.tag else ""
    out = scene_dir / "tests" / f"pano-{time.strftime('%Y%m%d-%H%M%S')}{tag}"
    (out / "frames").mkdir(parents=True)
    ref_small = small(np.asarray(Image.open(ref_path).convert("RGB")))
    current = {"ref_small": ref_small, "label": "opening", "pending": None}
    stats_events = []

    r = Reactor(model_name=model, api_key=os.environ["REACTOR_API_KEY"],
                max_session_duration_seconds=int(args.seconds) + 120)
    log = open(out / "events.jsonl", "w")
    t_start = None
    stats = {"frames": 0, "first_frame_s": None, "size": None, "fps_windows": [], "snapshots": {}}
    snaps = list(SNAP_AT)
    window = {"t": None, "n": 0}
    first_small = {}

    def since():
        return None if t_start is None else round(time.time() - t_start, 2)

    @r.on_message
    def on_msg(msg):
        log.write(json.dumps({"t": since(), "msg": msg}, default=str) + "\n")
        log.flush()
        kind = msg.get("type") if isinstance(msg, dict) else None
        pend = current["pending"]
        if pend and kind == "chunk_complete" and (msg.get("data") or {}).get("frames_emitted", 0) > 0:
            now = since()
            pend["frames_back_s"] = round(now - pend["sent_s"], 2)
            current["pending"] = None
            print(f"[{now}] {pend['label']}: frames back after {pend['frames_back_s']} s", flush=True)
            for extra in (now + 3, now + 12):  # look at each new run soon after it starts, and a bit later
                snaps.append(extra)
            snaps.sort()
        if kind in ("state", "generation_started", "command_error", "generation_complete"):
            print(f"[{since()}] {kind}: {json.dumps(msg, default=str)[:300]}", flush=True)

    @r.on_error
    def on_err(err):
        print("error:", err, flush=True)

    def on_frame(frame):
        if t_start is None:
            return
        now = time.time() - t_start
        stats["frames"] += 1
        if stats["first_frame_s"] is None:
            stats["first_frame_s"] = round(now, 2)
            stats["size"] = [int(frame.shape[1]), int(frame.shape[0])]
            Image.fromarray(frame).save(out / "frames" / f"t{now:05.1f}-first.png")
            first_small["img"] = small(frame)
            print(f"[{now:.1f}] first frame {stats['size']}", flush=True)
        if window["t"] is None:
            window.update(t=now, n=0)
        window["n"] += 1
        if now - window["t"] >= 5:
            stats["fps_windows"].append(round(window["n"] / (now - window["t"]), 1))
            window.update(t=now, n=0)
        if snaps and now >= snaps[0]:
            snaps.pop(0)
            Image.fromarray(frame).save(out / "frames" / f"t{now:05.1f}.png")
            s = small(frame)
            stats["snapshots"][f"{now:.0f}"] = {
                "anchor": current["label"],
                "diff_vs_reference": round(float(np.abs(s - current["ref_small"]).mean()), 1),
                "diff_vs_first_frame": round(float(np.abs(s - first_small["img"]).mean()), 1),
                "sky_diff_vs_first_frame": round(float(np.abs(top(s) - top(first_small["img"])).mean()), 1),
                "seam_diff": round(seam(s), 1),
            }

    print(f"connecting to {model} (passthrough={args.passthrough}) ...", flush=True)
    deadline = time.time() + args.wait_minutes * 60
    attempt = 0
    while True:  # Dynamic answers 429 "no available capacity" while anyone else holds it
        attempt += 1
        try:
            await asyncio.wait_for(r.connect(), 90)
            break
        except RateLimitedError as e:
            if time.time() > deadline:
                sys.exit(f"no capacity after {attempt} attempts / {args.wait_minutes} min")
            print(f"[{time.strftime('%X')}] connect attempt {attempt}: busy", flush=True)
            await asyncio.sleep(15)
            r = Reactor(model_name=model, api_key=os.environ["REACTOR_API_KEY"],
                        max_session_duration_seconds=int(args.seconds) + 120)
            r.on_message(on_msg)
            r.on_error(on_err)
    try:
        r.track("main_video").on_frame(on_frame)
        print(f"session {r.get_session_id()}", flush=True)

        if args.seed is not None:
            await r.send_command("set_seed", {"seed": args.seed})
        ref = await r.upload_file(ref_path)
        await r.send_command("set_image", {"image": ref})
        await r.send_command("set_prompt", {"prompt": prompt, "passthrough": args.passthrough})
        print(f"prompt ({len(prompt.split())} words): {prompt}", flush=True)
        t_start = time.time()
        await r.send_command("start", {})

        events = {e["label"]: e for e in pano_cfg.get("events", [])}
        steering = [(float(t), events[label]) for t, label in (x.split(":", 1) for x in args.steer.split(",") if x)]
        uploads = {}
        schedule = [] if args.no_steer else list(steering)
        if args.steer_every:
            t = args.steer_every
            while t < args.seconds:
                schedule.append((t, {"label": "steer-every", "mode": "steer", "prompt": args.steer_text}))
                t += args.steer_every
            schedule.sort()
        for at, ev in schedule:
            if at >= args.seconds:
                break
            await asyncio.sleep(max(0, at - (time.time() - t_start)))
            if ev.get("mode") == "reanchor":
                # Same session: reset -> new reference -> event prompt -> start (as web/src/live.js).
                path = scene_dir / ev["reference"]
                if path not in uploads:
                    uploads[path] = await r.upload_file(path)
                sent = since()
                await r.send_command("reset", {})
                await r.send_command("set_image", {"image": uploads[path]})
                await r.send_command("set_prompt", {"prompt": ev["prompt"], "passthrough": args.passthrough})
                await r.send_command("start", {})
                current.update(label=ev["label"], ref_small=small(np.asarray(Image.open(path).convert("RGB"))),
                               pending={"label": ev["label"], "sent_s": sent})
                stats_events.append(current["pending"])
                print(f"[{sent}] re-anchor: {ev['label']}", flush=True)
            else:
                await r.send_command("set_prompt", {"prompt": ev["prompt"], "passthrough": args.passthrough})
                print(f"[{since()}] steer: {ev['label']}", flush=True)
            log.write(json.dumps({"t": since(), "event": ev.get("label"), "mode": ev.get("mode")}) + "\n")
        await asyncio.sleep(max(0, args.seconds - (time.time() - t_start)))

        stats["first_frame_ref_diff"] = (
            round(float(np.abs(first_small["img"] - ref_small).mean()), 1) if first_small else None
        )
        stats["steering"] = [] if args.no_steer else [(t, e["label"], e.get("mode")) for t, e in steering]
        stats["reanchors"] = stats_events
        stats["prompt"] = prompt
        stats["model"] = model
        stats["passthrough"] = args.passthrough
        stats["seed"] = args.seed
        stats["prompt_key"] = args.prompt
        stats["reference_seam_diff"] = round(seam(ref_small), 1)
        stats["steer_every"] = args.steer_every
        stats["seconds"] = args.seconds
        (out / "report.json").write_text(json.dumps(stats, indent=1))
        print(json.dumps({k: v for k, v in stats.items() if k not in ("prompt", "steering")}, indent=1), flush=True)

        if args.record:  # billed while waiting; the recording was never ready within 60 s on 2026-11-14
            try:
                await r.send_command("pause", {})
                await asyncio.wait_for(r.download_recording(out / "recording.mp4", ready_timeout=60), 120)
                print(f"recording -> {out / 'recording.mp4'}", flush=True)
            except Exception as e:
                print(f"no recording: {type(e).__name__}: {e}", flush=True)
        pass  # disconnect happens in finally
        log.close()
        print(f"output -> {out}", flush=True)
    finally:
        await r.disconnect()  # never leave a billed session behind, even on a crash


if __name__ == "__main__":
    asyncio.run(main())
