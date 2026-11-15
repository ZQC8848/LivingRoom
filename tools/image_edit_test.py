"""Time image-edit models (OpenRouter) on a scene reference and score how well each keeps
the panorama's layout. Used to pick the model behind custom prompts ("snow begins to fall").

    tools/.venv/bin/python tools/image_edit_test.py --scene hillside \
        --models google/gemini-3.1-flash-lite-image,google/gemini-3.1-flash-image \
        --edits "snow:Heavy snow is falling and the ground is covered in snow"

Per run it prints: seconds, output size, layout (correlation of the vertical-gradient map
with the reference's, 1 = same structure), seam (mean abs diff between the left and right
edge columns, 0-255; the reference's own value is printed first). Images go to
~/Assets/LivingRoom/scenes/<scene>/tests/edit-<time>/.
"""
import argparse, base64, io, json, os, sys, time, urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from marble_pano import load_env  # noqa: E402

INSTRUCTION = (
    "Edit this image: {change}. This is an equirectangular 360-degree panorama squeezed to 16:9. "
    "Keep the composition exactly: the horizon line, every hill, tree, animal and object stays at the "
    "same position and size, and the left and right edges must still join seamlessly. Change only the "
    "weather, light and surface appearance. Output a single 16:9 image, no text, no border."
)


def structure(img):
    g = np.asarray(img.convert("L").resize((208, 120), Image.LANCZOS), dtype=np.float32)
    return (g[1:, :] - g[:-1, :]).ravel()


def seam(img):
    a = np.asarray(img.convert("RGB"), dtype=np.float32)
    return float(np.abs(a[:, :4].mean(1) - a[:, -4:].mean(1)).mean())


def edit(model, ref_b64, change, key):
    body = {
        "model": model,
        "modalities": ["image", "text"],
        "image_config": {"aspect_ratio": "16:9"},
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": INSTRUCTION.format(change=change)},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{ref_b64}"}},
        ]}],
    }
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=240) as r:
        out = json.load(r)
    dt = time.time() - t0
    msg = out["choices"][0]["message"]
    imgs = msg.get("images") or []
    if not imgs:
        raise RuntimeError(f"no image returned: {str(msg.get('content'))[:200]}")
    url = imgs[0]["image_url"]["url"]
    return Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1]))), dt, out.get("usage", {})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="hillside")
    ap.add_argument("--models", required=True)
    ap.add_argument("--edits", default="snow:Heavy snow is falling and the ground is covered in snow")
    args = ap.parse_args()
    load_env()
    key = os.environ["OPENROUTER_API_KEY"]
    base = Path.home() / "Assets/LivingRoom/scenes" / args.scene
    ref = Image.open(base / "reference.png").convert("RGB")
    buf = io.BytesIO()
    ref.save(buf, "JPEG", quality=92)
    ref_b64 = base64.b64encode(buf.getvalue()).decode()
    out_dir = base / "tests" / f"edit-{time.strftime('%Y%m%d-%H%M%S')}"
    out_dir.mkdir(parents=True)
    s_ref = structure(ref)
    print(f"reference {ref.size}, seam {seam(ref):.1f}; output -> {out_dir}")
    for spec in args.edits.split("|"):
        name, change = spec.split(":", 1)
        for model in args.models.split(","):
            try:
                img, dt, usage = edit(model, ref_b64, change, key)
            except Exception as e:  # keep going: one model failing must not hide the others
                detail = e.read().decode()[:200] if hasattr(e, "read") else str(e)[:200]
                print(f"{name:8} {model:40} FAILED {detail}")
                continue
            img = img.convert("RGB")
            img.save(out_dir / f"{name}-{model.split('/')[-1]}.jpg", quality=92)
            fit = img.resize(ref.size, Image.LANCZOS)
            corr = float(np.corrcoef(s_ref, structure(fit))[0, 1])
            print(f"{name:8} {model:40} {dt:5.1f}s  {img.size[0]}x{img.size[1]}  layout {corr:.2f}  seam {seam(fit):5.1f}  cost ${usage.get('cost', 0):.4f}")


if __name__ == "__main__":
    main()
