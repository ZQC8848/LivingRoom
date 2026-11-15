"""Try a non-Orbis Reactor model on the scene's panorama reference (personal account).

    tools/.venv/bin/python tools/alt_model_test.py hillside helios [--seconds 60]
    tools/.venv/bin/python tools/alt_model_test.py hillside lingbot-world-2

Same measurements as tools/orbis_test.py (snapshots, diff vs the anchor image, seam diff) so
results compare directly. Uses REACTOR_API_KEY_ALT (the hackathon key cannot open these
models) -- billed to that account: Helios $0.102/min, LingBot World 2 $0.420/min.

Per model:
- helios: centre-crops input to 5:3, so the reference is *squashed* to 1600x960 first (the
  frame still covers 360 deg). set_conditioning (prompt + image atomically), image strength 1.0.
  At 45 s the image is swapped to the Evening reference mid-run (Helios allows it).
- lingbot-world-2: 1664x960 native = our reference size. Camera axes stay at their default
  idle, i.e. a locked camera.
Both get the scene's opening prompt and a "Golden hour" steer at 35 s.
"""

import argparse
import asyncio
import io
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
from orbis_test import seam, small  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SNAP_AT = [4, 8, 15, 25, 34, 40, 44, 50, 56]
NATIVE = {"helios": (1600, 960), "lingbot-world-2": (1664, 960)}


def png_bytes(path, size):
    img = Image.open(path).convert("RGB").resize(size, Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue(), img


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("model", choices=sorted(NATIVE))
    ap.add_argument("--seconds", type=float, default=60)
    args = ap.parse_args()
    load_env()

    scene_dir = ASSETS / args.scene
    cfg = json.loads((ROOT / "scenes" / args.scene / "scene.json").read_text())["orbis"]["pano"]
    events = {e["label"]: e for e in cfg.get("retired_events", []) + cfg["events"]}
    size = NATIVE[args.model]
    ref_bytes, ref_img = png_bytes(scene_dir / "reference.png", size)
    eve_bytes, eve_img = png_bytes(scene_dir / events["Evening"]["reference"], size)
    current = {"ref_small": small(np.asarray(ref_img)), "label": "opening"}

    out = scene_dir / "tests" / f"{args.model}-{time.strftime('%Y%m%d-%H%M%S')}"
    (out / "frames").mkdir(parents=True)
    ref_img.save(out / "reference_used.png")

    model = f"reactor/{args.model}"
    stats = {"model": model, "first_frame_s": None, "size": None, "frames": 0, "snapshots": {}, "events": []}
    snaps = list(SNAP_AT)
    t_start = None
    first = {}

    def since():
        return None if t_start is None else round(time.time() - t_start, 2)

    def on_frame(frame):
        if t_start is None:
            return
        now = time.time() - t_start
        stats["frames"] += 1
        if stats["first_frame_s"] is None:
            stats["first_frame_s"] = round(now, 2)
            stats["size"] = [int(frame.shape[1]), int(frame.shape[0])]
            first["s"] = small(frame)
            print(f"[{now:.1f}] first frame {stats['size']}", flush=True)
        if snaps and now >= snaps[0]:
            snaps.pop(0)
            Image.fromarray(frame).save(out / "frames" / f"t{now:05.1f}.png")
            s = small(frame)
            stats["snapshots"][f"{now:.0f}"] = {
                "anchor": current["label"],
                "diff_vs_anchor": round(float(np.abs(s - current["ref_small"]).mean()), 1),
                "diff_vs_first_frame": round(float(np.abs(s - first["s"]).mean()), 1),
                "seam_diff": round(seam(s), 1),
            }

    r = None
    for attempt in range(8):
        r = Reactor(model_name=model, api_key=os.environ["REACTOR_API_KEY_ALT"],
                    max_session_duration_seconds=int(args.seconds) + 90)
        r.on_message(lambda m: (m.get("type") in ("command_error", "generation_started", "image_accepted"))
                     and print(f"[{since()}] {json.dumps(m, default=str)[:220]}", flush=True))
        try:
            await asyncio.wait_for(r.connect(), 90)
            break
        except RateLimitedError as e:
            print(f"connect attempt {attempt + 1}: {str(e)[-80:]}", flush=True)
            await asyncio.sleep(15)
    else:
        sys.exit("no capacity")

    try:
        r.track("main_video").on_frame(on_frame)
        print(f"session {r.get_session_id()}", flush=True)
        ref = await r.upload_file(ref_bytes, name="reference.png", mime_type="image/png")
        eve = await r.upload_file(eve_bytes, name="evening.png", mime_type="image/png")
        if args.model == "helios":
            await r.send_command("set_conditioning", {"prompt": cfg["opening"], "image": ref})
            await r.send_command("set_image_strength", {"image_strength": 1.0})
        else:
            await r.send_command("set_image", {"image": ref})
            await r.send_command("set_prompt", {"prompt": cfg["opening"]})
        t_start = time.time()
        await r.send_command("start", {})

        plan = [(35, "steer", events["Golden hour"]["prompt"])]
        if args.model == "helios":
            plan.append((45, "image", None))
        for at, kind, text in plan:
            await asyncio.sleep(max(0, at - (time.time() - t_start)))
            if kind == "steer":
                await r.send_command("set_prompt", {"prompt": text})
                print(f"[{since()}] steer: Golden hour", flush=True)
            else:
                await r.send_command("set_conditioning", {"prompt": events["Evening"]["prompt"], "image": eve})
                current.update(label="Evening", ref_small=small(np.asarray(eve_img)))
                print(f"[{since()}] mid-run image + prompt -> Evening", flush=True)
            stats["events"].append({"t": since(), "kind": kind})
        await asyncio.sleep(max(0, args.seconds - (time.time() - t_start)))
    finally:
        await r.disconnect()

    stats["first_frame_ref_diff"] = round(float(np.abs(first["s"] - small(np.asarray(ref_img))).mean()), 1) if first else None
    stats["reference_seam_diff"] = round(seam(small(np.asarray(ref_img))), 1)
    (out / "report.json").write_text(json.dumps(stats, indent=1))
    print(json.dumps({k: v for k, v in stats.items() if k != "snapshots"}, indent=1), flush=True)
    for k, v in stats["snapshots"].items():
        print(f"  {k:>3}s {v}", flush=True)
    print(f"output -> {out}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
