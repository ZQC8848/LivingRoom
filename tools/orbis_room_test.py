"""Run the four walls of a scene on Orbis at the same time and record them side by side.

    tools/.venv/bin/python tools/orbis_room_test.py hillside [--seconds 120] [--model dynamic]

Opens one session per wall (staggered: session creation is rate-limited), uploads each
wall's reference image and compiled opening prompt, then sends `start` to all four at
once. Global steering prompts go to every wall at the same moment. Snapshots are saved as
a room strip in the order you see turning right from the left wall: left | front | right |
back, so the three visible corners sit between neighbouring tiles.

Writes ~/Assets/LivingRoom/scenes/<scene>/tests/room-<time>/:
  strips/t<sec>.jpg   the four walls side by side at that moment
  report.json         per-wall first frame / fps, per-snapshot seam and tone numbers
  contact.jpg         all strips stacked
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from reactor_sdk import RateLimitedError, Reactor

sys.path.insert(0, str(Path(__file__).resolve().parent))
from marble_pano import ASSETS, load_env  # noqa: E402
from scene_prompts import compile_prompts  # noqa: E402

WALLS = ["left", "front", "right", "back"]  # strip order; each is the right-hand neighbour of the one before
CORNERS = [("left", "front"), ("front", "right"), ("right", "back"), ("back", "left")]
SNAP_AT = [8, 15, 30, 45, 60, 75, 90, 105, 118]
STEERING = [  # global events: same sentence to every wall at the same moment
    (40, "The morning light turns warm and golden as the sun sinks lower, and long soft shadows stretch across the grass."),
    (80, "Evening falls: the sky deepens to orange and violet and the land dims."),
]
TILE = (480, 270)


class Wall:
    def __init__(self, face, model, seconds):
        self.face = face
        self.model = model
        self.seconds = seconds
        self.latest = None
        self.frames = 0
        self.first_frame_s = None
        self.t0 = None
        self.errors = []

    def on_frame(self, frame):
        if self.t0 is None:
            return
        self.latest = frame
        self.frames += 1
        if self.first_frame_s is None:
            self.first_frame_s = round(time.time() - self.t0, 2)
            print(f"  [{self.face}] first frame at {self.first_frame_s}s {frame.shape[1]}x{frame.shape[0]}", flush=True)

    async def open(self, scene, image, prompt):
        for attempt in range(6):
            self.r = Reactor(model_name=self.model, api_key=os.environ["REACTOR_API_KEY"],
                             max_session_duration_seconds=int(self.seconds) + 180)
            self.r.on_error(lambda e: self.errors.append(str(e)))
            try:
                await asyncio.wait_for(self.r.connect(), 90)
                break
            except RateLimitedError as e:
                print(f"  [{self.face}] connect attempt {attempt + 1}: {str(e)[-120:]}", flush=True)
                await asyncio.sleep(10)
        else:
            raise RuntimeError(f"{self.face}: no capacity")
        self.r.track("main_video").on_frame(self.on_frame)
        ref = await self.r.upload_file(image)
        await self.r.send_command("set_image", {"image": ref})
        await self.r.send_command("set_prompt", {"prompt": prompt})
        print(f"  [{self.face}] ready, session {self.r.get_session_id()}", flush=True)


def tone(img):
    return np.asarray(Image.fromarray(img).resize((64, 36)), dtype=np.float32).reshape(-1, 3).mean(0)


def edge(img, side, rows=270):
    im = np.asarray(Image.fromarray(img).resize((480, rows)), dtype=np.float32)
    return im[:, -4:] if side == "right" else im[:, :4]


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("--seconds", type=float, default=120)
    ap.add_argument("--model", choices=["stable", "dynamic"], default="dynamic")
    args = ap.parse_args()
    load_env()
    model = f"reactor/visko-orbis-{args.model}"
    scene_dir = ASSETS / args.scene
    prompts = compile_prompts(args.scene)
    out = scene_dir / "tests" / f"room-{time.strftime('%Y%m%d-%H%M%S')}-{args.model}"
    (out / "strips").mkdir(parents=True)

    walls = {f: Wall(f, model, args.seconds) for f in WALLS}
    print(f"opening {len(walls)} sessions on {model} ...", flush=True)
    try:
        for i, f in enumerate(WALLS):  # staggered: creation is limited to 10/min per model
            if i:
                await asyncio.sleep(4)
            await walls[f].open(args.scene, scene_dir / "faces" / f"{f}.png", prompts[f])
    except Exception:
        # Never leave opened sessions behind: an orphan keeps holding a server (and
        # Dynamic capacity is scarce) until its max duration runs out.
        await asyncio.gather(*(w.r.disconnect() for w in walls.values() if hasattr(w, "r")),
                             return_exceptions=True)
        raise

    t0 = time.time()
    for w in walls.values():
        w.t0 = t0
    await asyncio.gather(*(w.r.send_command("start", {}) for w in walls.values()))
    print("started all walls", flush=True)

    report = {"model": model, "walls": {}, "snapshots": {}, "steering": STEERING}
    snaps = list(SNAP_AT)
    steers = list(STEERING)
    strips = []
    while time.time() - t0 < args.seconds:
        now = time.time() - t0
        if steers and now >= steers[0][0]:
            at, text = steers.pop(0)
            await asyncio.gather(*(w.r.send_command("set_prompt", {"prompt": text}) for w in walls.values()))
            print(f"[{now:.1f}] steer all: {text}", flush=True)
        if snaps and now >= snaps[0]:
            snaps.pop(0)
            frames = {f: walls[f].latest for f in WALLS}
            if all(v is not None for v in frames.values()):
                strip = Image.new("RGB", (TILE[0] * 4, TILE[1]))
                for i, f in enumerate(WALLS):
                    strip.paste(Image.fromarray(frames[f]).resize(TILE), (i * TILE[0], 0))
                strip.save(out / "strips" / f"t{now:05.1f}.jpg", quality=88)
                strips.append((now, strip))
                tones = {f: tone(frames[f]) for f in WALLS}
                report["snapshots"][f"{now:.0f}"] = {
                    "corner_seam_diff": {f"{a}|{b}": round(float(np.abs(edge(frames[a], 'right') - edge(frames[b], 'left')).mean()), 1)
                                         for a, b in CORNERS},
                    "tone_rgb": {f: [round(float(x)) for x in tones[f]] for f in WALLS},
                    "tone_spread": round(float(np.ptp(np.stack(list(tones.values())), axis=0).mean()), 1),
                }
                print(f"[{now:.1f}] snapshot; tone spread {report['snapshots'][f'{now:.0f}']['tone_spread']}", flush=True)
        await asyncio.sleep(0.2)

    for f, w in walls.items():
        report["walls"][f] = {"first_frame_s": w.first_frame_s, "avg_fps": round(w.frames / max(1e-6, args.seconds - (w.first_frame_s or 0)), 1),
                              "errors": w.errors[:5]}
    (out / "report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report["walls"], indent=1), flush=True)

    if strips:
        bar = 22
        sheet = Image.new("RGB", (TILE[0] * 4, (TILE[1] + bar) * len(strips)), "black")
        d = ImageDraw.Draw(sheet)
        for i, (t, s) in enumerate(strips):
            y = i * (TILE[1] + bar)
            sheet.paste(s, (0, y + bar))
            d.text((6, y + 4), f"{t:.0f}s   left | front | right | back   ({model})", fill="white")
        sheet.save(out / "contact.jpg", quality=85)

    await asyncio.gather(*(w.r.disconnect() for w in walls.values()), return_exceptions=True)
    print(f"output -> {out}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
