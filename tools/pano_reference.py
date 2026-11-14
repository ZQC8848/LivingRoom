"""Turn a scene's Marble pano into the single Orbis reference image (and a matching still).

    tools/.venv/bin/python tools/pano_reference.py hillside [--yaw 12]

1. Rotate the equirect pano so the scene's front (projection.yaw_deg in scene.json) is at
   the image centre. The left/right edges -- where Orbis' two independent edges meet on the
   sphere -- then sit directly behind the viewer.
2. Soften the poles (|lat| > 60 deg, ramping to fully blurred by 80 deg): Marble's zenith and
   nadir are its weakest pixels, and the viewer's sphere fades them out anyway.
3. Squash 2:1 -> 1664x960, twice Orbis' 832x480 generation raster, so Orbis does not resize
   the aspect a second time. The sphere stretches it back: a full frame maps to 360 x 180 deg.

Writes ~/Assets/LivingRoom/scenes/<scene>/:
  pano_front.jpg   rotated full-resolution pano (the sphere's still fallback)
  reference.png    1664x960 image for Orbis set_image
"""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from marble_pano import ASSETS

ROOT = Path(__file__).resolve().parent.parent
REF_SIZE = (1664, 960)


def soften_poles(img):
    w, h = img.size
    blurred = np.asarray(img.filter(ImageFilter.GaussianBlur(radius=w / 200)), dtype=np.float32)
    lat = 90 - (np.arange(h) + 0.5) / h * 180
    weight = np.clip((np.abs(lat) - 60) / 20, 0, 1)[:, None, None]
    soft = np.asarray(img, dtype=np.float32) * (1 - weight) + blurred * weight
    return Image.fromarray(np.clip(soft, 0, 255).astype(np.uint8))


def normalise_event(scene, name, source):
    """An edited copy of reference.png (e.g. dusk) -> events/<name>.png at the reference size.
    The whole image is taken as the full 360x180 frame, exactly like reference.png."""
    out = ASSETS / scene / "events"
    out.mkdir(parents=True, exist_ok=True)
    img = Image.open(source).convert("RGB").resize(REF_SIZE, Image.LANCZOS)
    soften_poles(img).save(out / f"{name}.png")
    print(f"wrote {out / f'{name}.png'} {REF_SIZE[0]}x{REF_SIZE[1]} from {source.name} ({Image.open(source).size[0]}x{Image.open(source).size[1]})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("--yaw", type=float, help="degrees; pano direction that becomes the front")
    ap.add_argument("--event", help="normalise an edited full-frame image into events/<name>.png instead")
    ap.add_argument("--source", help="with --event: the edited image (any size, covering 360x180)")
    args = ap.parse_args()
    if args.event:
        return normalise_event(args.scene, args.event, Path(args.source))

    cfg = json.loads((ROOT / "scenes" / args.scene / "scene.json").read_text())
    yaw = args.yaw if args.yaw is not None else cfg.get("projection", {}).get("yaw_deg", 0)
    out = ASSETS / args.scene
    pano = Image.open(next(out.glob("pano.*"))).convert("RGB")
    w, h = pano.size

    # Output column u shows pano longitude (u - 0.5) * 360 + yaw.
    arr = np.asarray(pano)
    arr = np.roll(arr, -int(round(yaw / 360 * w)), axis=1)
    rotated = Image.fromarray(arr)
    rotated.save(out / "pano_front.jpg", quality=92)

    soften_poles(rotated).resize(REF_SIZE, Image.LANCZOS).save(out / "reference.png")
    print(f"pano {w}x{h}, front = pano lon {yaw} deg; seam (image edges) is directly behind")
    print(f"wrote {out / 'pano_front.jpg'} and {out / 'reference.png'} {REF_SIZE[0]}x{REF_SIZE[1]}")


if __name__ == "__main__":
    main()
