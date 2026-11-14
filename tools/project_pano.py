"""Project an equirectangular panorama onto the six faces of the room, from the eye.

    tools/.venv/bin/python tools/project_pano.py hillside [--yaw 20] [--width 1664]

Every pixel of every face is coloured by the pano direction from the player's eye
(room centre, 1.6 m high) to that point on the face. Because all faces share one eye
point, adjacent faces match exactly along their shared edge, and the horizon lands at the
same height on all four walls (eye height / wall height from the bottom).

Room geometry matches web/src/config.js and web/src/room.js:
  x right, y up, -z = front wall. Walls 4.8 x 2.7 m (16:9). Floor/ceiling 4.8 x 4.8 m.
Floor and ceiling are written as 16:9 images too (the plane extended sideways to
8.53 x 4.8 m) because Orbis only takes 16:9; the room shows their centre 1:1.

Writes to ~/Assets/LivingRoom/scenes/<scene>/:
  faces/<face>.png   16:9 reference image per face (Orbis set_image input)
  atlas.jpg          3x2 atlas in the web room's layout (static preview in the headset)
  seams.jpg          the pano with the four wall boundaries drawn, to choose --yaw
"""

import argparse
import json
import math
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ASSETS = Path(os.environ.get("LR_ASSETS", Path.home() / "Assets" / "LivingRoom")) / "scenes"

SIZE, HEIGHT, EYE = 4.8, 2.7, 1.6
HALF = SIZE / 2
WIDE = SIZE * 16 / 9  # floor/ceiling extended to 16:9

# centre, right vector, up vector (image space), half-width, half-height
FACES = {
    "front":   ((0, HEIGHT / 2, -HALF), (1, 0, 0),  (0, 1, 0),  HALF, HEIGHT / 2),
    "right":   ((HALF, HEIGHT / 2, 0),  (0, 0, 1),  (0, 1, 0),  HALF, HEIGHT / 2),
    "back":    ((0, HEIGHT / 2, HALF),  (-1, 0, 0), (0, 1, 0),  HALF, HEIGHT / 2),
    "left":    ((-HALF, HEIGHT / 2, 0), (0, 0, -1), (0, 1, 0),  HALF, HEIGHT / 2),
    # floor: camera looking down, image top toward the front wall
    "floor":   ((0, 0, 0),              (1, 0, 0),  (0, 0, -1), WIDE / 2, HALF),
    # ceiling: camera looking up, image top toward the front wall (so image right = -x)
    "ceiling": ((0, HEIGHT, 0),         (-1, 0, 0), (0, 0, -1), WIDE / 2, HALF),
}
# Atlas cells, same as web/src/config.js FACES[].cell ([col, row], row 0 on top)
ATLAS_CELL = {"front": (0, 0), "right": (1, 0), "back": (2, 0),
              "left": (0, 1), "floor": (1, 1), "ceiling": (2, 1)}


def face_directions(face, w, h):
    c, r, u, hw, hh = (np.array(v, dtype=np.float64) if isinstance(v, tuple) else v for v in FACES[face])
    s = (np.arange(w) + 0.5) / w * 2 - 1
    t = 1 - (np.arange(h) + 0.5) / h * 2
    S, T = np.meshgrid(s, t)
    p = c + S[..., None] * r * hw + T[..., None] * u * hh
    return p - np.array([0, EYE, 0])


def sample(pano, dirs, yaw_deg):
    """Bilinear sample of an equirect pano. lon 0 = pano centre = front (before yaw)."""
    ph, pw, _ = pano.shape
    dx, dy, dz = dirs[..., 0], dirs[..., 1], dirs[..., 2]
    lon = np.arctan2(dx, -dz) + math.radians(yaw_deg)  # +x (right wall) = +90 deg
    lat = np.arctan2(dy, np.hypot(dx, dz))
    x = ((lon / (2 * math.pi) + 0.5) % 1.0) * pw - 0.5
    y = np.clip((0.5 - lat / math.pi) * ph - 0.5, 0, ph - 1)
    x0 = np.floor(x).astype(int)
    y0 = np.floor(y).astype(int)
    fx = (x - x0)[..., None]
    fy = (y - y0)[..., None]
    x0w, x1w = x0 % pw, (x0 + 1) % pw
    y1 = np.minimum(y0 + 1, ph - 1)
    top = pano[y0, x0w] * (1 - fx) + pano[y0, x1w] * fx
    bot = pano[y1, x0w] * (1 - fx) + pano[y1, x1w] * fx
    return top * (1 - fy) + bot * fy


def seams_overlay(pano_img, yaw_deg):
    img = pano_img.convert("RGB").copy()
    d = ImageDraw.Draw(img)
    pw, ph = img.size
    labels = {0: "FRONT", 90: "RIGHT", 180: "BACK", -90: "LEFT"}
    for lon_deg in (45, 135, -45, -135):  # wall boundaries
        x = ((math.radians(lon_deg + yaw_deg) / (2 * math.pi) + 0.5) % 1.0) * pw
        d.line([(x, 0), (x, ph)], fill=(255, 40, 40), width=max(2, pw // 800))
    for lon_deg, name in labels.items():
        x = ((math.radians(lon_deg + yaw_deg) / (2 * math.pi) + 0.5) % 1.0) * pw
        d.text((x - 20, ph * 0.05), name, fill=(255, 255, 0))
    # where the top/bottom edges of the walls fall (corner = highest/lowest angle)
    for h in (HEIGHT - EYE, -EYE):
        for dist in (HALF, HALF * math.sqrt(2)):
            y = (0.5 - math.atan2(h, dist) / math.pi) * ph
            d.line([(0, y), (pw, y)], fill=(80, 200, 255), width=1)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("--yaw", type=float, help="degrees; overrides scene.json projection.yaw_deg")
    ap.add_argument("--width", type=int, default=1664, help="face image width (16:9)")
    ap.add_argument("--cell", type=int, default=1280, help="atlas cell width (16:9)")
    args = ap.parse_args()

    cfg = json.loads((ROOT / "scenes" / args.scene / "scene.json").read_text())
    yaw = args.yaw if args.yaw is not None else cfg.get("projection", {}).get("yaw_deg", 0)
    out = ASSETS / args.scene
    pano_path = next(out.glob("pano.*"))
    pano_img = Image.open(pano_path)
    pano = np.asarray(pano_img.convert("RGB"), dtype=np.float32)
    print(f"pano {pano_path.name}: {pano_img.size[0]}x{pano_img.size[1]}, yaw {yaw} deg")
    print(f"  pano px per degree: {pano_img.size[0] / 360:.1f}  (a wall shows ~90 deg; Orbis uses 832 px)")

    w, h = args.width, round(args.width * 9 / 16)
    cw, ch = args.cell, round(args.cell * 9 / 16)
    atlas = Image.new("RGB", (cw * 3, ch * 2))
    (out / "faces").mkdir(exist_ok=True)
    edges = {}
    for face in FACES:
        img = sample(pano, face_directions(face, w, h), yaw)
        edges[face] = img
        im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
        im.save(out / "faces" / f"{face}.png")
        col, row = ATLAS_CELL[face]
        atlas.paste(im.resize((cw, ch), Image.LANCZOS), (col * cw, row * ch))
    atlas.save(out / "atlas.jpg", quality=92)
    seams_overlay(pano_img, yaw).save(out / "seams.jpg", quality=88)

    # Sanity check: stepping across a shared wall edge should change the image no more than
    # stepping one column inside a face. ratio ~1 = continuous; >>1 = a visible seam.
    pairs = [("front", "right"), ("right", "back"), ("back", "left"), ("left", "front")]
    for a, b in pairs:
        across = np.abs(edges[a][:, -1] - edges[b][:, 0]).mean()
        inside = np.abs(edges[a][:, -1] - edges[a][:, -2]).mean() + 1e-6
        print(f"  edge {a}|{b}: across {across:.2f}, one column inside {inside:.2f}, ratio {across / inside:.2f}")
    horizon = EYE / HEIGHT
    print(f"  horizon on every wall at {horizon:.0%} from the bottom")
    print(f"wrote faces/*.png ({w}x{h}), atlas.jpg ({cw * 3}x{ch * 2}), seams.jpg -> {out}")


if __name__ == "__main__":
    main()
