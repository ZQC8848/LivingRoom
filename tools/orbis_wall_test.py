"""Run ONE face of a scene on Orbis and record what happens.

    tools/.venv/bin/python tools/orbis_wall_test.py hillside front [--seconds 80]

Uploads faces/<face>.png as the reference image, sends the compiled opening prompt
(tools/scene_prompts.py), starts, then sends the scene's test steering prompts on a
schedule. Writes to ~/Assets/LivingRoom/scenes/<scene>/tests/<face>-<time>/:
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
from scene_prompts import compile_prompts  # noqa: E402

SNAP_AT = [5, 10, 20, 30, 40, 50, 60, 70, 80, 100, 120]

# State changes sent mid-run (seconds after start). One change each, written as a
# transition from the current scene, per the Orbis prompt guide.
STEERING = {
    "front": [
        (35, "The morning light turns warm and golden as the sun sinks lower, and long soft shadows stretch across the grass."),
        (60, "One of the sheep lifts its head and bleats while the others keep grazing."),
        (90, "Evening falls: the sky deepens to orange and violet and the hillside dims."),
    ],
}


def small(img, size=(208, 120)):
    return np.asarray(Image.fromarray(img).convert("RGB").resize(size, Image.BILINEAR), dtype=np.float32)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("face")
    ap.add_argument("--seconds", type=float, default=80)
    ap.add_argument("--model", choices=["stable", "dynamic"], default="stable")
    ap.add_argument("--passthrough", action="store_true", help="skip the server-side prompt rewrite")
    ap.add_argument("--variant", help="use orbis.variants.<face>.<name> from scene.json instead of the compiled prompt")
    ap.add_argument("--no-steer", action="store_true", help="do not send the mid-run steering prompts")
    ap.add_argument("--tag", default="", help="suffix for the output folder")
    args = ap.parse_args()
    model = f"reactor/visko-orbis-{args.model}"

    load_env()
    scene_dir = ASSETS / args.scene
    ref_path = scene_dir / "faces" / f"{args.face}.png"
    if args.variant:
        cfg = json.loads((Path(__file__).resolve().parent.parent / "scenes" / args.scene / "scene.json").read_text())
        prompt = cfg["orbis"]["variants"][args.face][args.variant]
    else:
        prompt = compile_prompts(args.scene)[args.face]
    tag = f"-{args.tag}" if args.tag else ""
    out = scene_dir / "tests" / f"{args.face}-{time.strftime('%Y%m%d-%H%M%S')}{tag}"
    (out / "frames").mkdir(parents=True)
    ref_small = small(np.asarray(Image.open(ref_path).convert("RGB")))

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
                "diff_vs_reference": round(float(np.abs(s - ref_small).mean()), 1),
                "diff_vs_first_frame": round(float(np.abs(s - first_small["img"]).mean()), 1),
            }

    print(f"connecting to {model} (passthrough={args.passthrough}, variant={args.variant}) ...", flush=True)
    for attempt in range(5):  # Dynamic sometimes answers 429 "no available capacity"
        try:
            await asyncio.wait_for(r.connect(), 90)
            break
        except RateLimitedError as e:
            print(f"connect attempt {attempt + 1}: {e}", flush=True)
            await asyncio.sleep(10)
            r = Reactor(model_name=model, api_key=os.environ["REACTOR_API_KEY"],
                        max_session_duration_seconds=int(args.seconds) + 120)
            r.on_message(on_msg)
            r.on_error(on_err)
    else:
        sys.exit("no capacity after 5 attempts")
    r.track("main_video").on_frame(on_frame)
    print(f"session {r.get_session_id()}", flush=True)

    ref = await r.upload_file(ref_path)
    await r.send_command("set_image", {"image": ref})
    await r.send_command("set_prompt", {"prompt": prompt, "passthrough": args.passthrough})
    print(f"prompt ({len(prompt.split())} words): {prompt}", flush=True)
    t_start = time.time()
    await r.send_command("start", {})

    for at, text in ([] if args.no_steer else STEERING.get(args.face, [])):
        if at >= args.seconds:
            break
        await asyncio.sleep(max(0, at - (time.time() - t_start)))
        await r.send_command("set_prompt", {"prompt": text})
        log.write(json.dumps({"t": since(), "sent_prompt": text}) + "\n")
        print(f"[{since()}] steer: {text}", flush=True)
    await asyncio.sleep(max(0, args.seconds - (time.time() - t_start)))

    stats["first_frame_ref_diff"] = (
        round(float(np.abs(first_small["img"] - ref_small).mean()), 1) if first_small else None
    )
    stats["steering"] = STEERING.get(args.face, [])
    stats["prompt"] = prompt
    stats["model"] = model
    stats["passthrough"] = args.passthrough
    stats["variant"] = args.variant
    stats["seconds"] = args.seconds
    (out / "report.json").write_text(json.dumps(stats, indent=1))
    print(json.dumps({k: v for k, v in stats.items() if k not in ("prompt", "steering")}, indent=1), flush=True)

    try:
        await r.send_command("pause", {})
        await asyncio.wait_for(r.download_recording(out / "recording.mp4", ready_timeout=60), 120)
        print(f"recording -> {out / 'recording.mp4'}", flush=True)
    except Exception as e:  # recorder may be disabled on this deployment
        print(f"no recording: {type(e).__name__}: {e}", flush=True)
    await r.disconnect()
    log.close()
    print(f"output -> {out}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
