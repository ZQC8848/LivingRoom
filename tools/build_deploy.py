"""Assemble the media for the public, static deployment of the hillside (the deploy/vercel
branch; the page is built with VITE_DEPLOY=1 and plays recordings, see web/src/recorded.js).

    tools/.venv/bin/python tools/build_deploy.py hillside

Copies from ~/Assets/LivingRoom/scenes/<scene>/ into web/deploy-public/scenes/<scene>/:
the front still, the reference of every preset and its recorded clip (clips/<label>.mp4, made
with `tools/orbis_test.py --mp4`), and writes scene.deploy.json -- what /api/scene returns on
the dev server, plus a clip per preset. Presets without a clip are left out. No prompts and no
keys go into the output: the deployed page generates nothing.
"""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = Path.home() / "Assets/LivingRoom/scenes"
GARDEN_URL = "https://livingroom-bosch-demo.sandy-toad-8179.chatgpt.site/"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    args = ap.parse_args()
    src = ASSETS / args.scene
    pano = json.loads((ROOT / "scenes" / args.scene / "scene.json").read_text())["orbis"]["pano"]
    out = ROOT / "web" / "deploy-public" / "scenes" / args.scene
    if out.exists():
        shutil.rmtree(out)
    (out / "clips").mkdir(parents=True)
    base = f"/scenes/{args.scene}"

    def copy(rel):
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / rel, out / rel)
        return f"{base}/{rel}"

    events = []
    for e in pano["events"]:
        clip = src / "clips" / f"{e['label'].lower()}.mp4"
        if e.get("mode") != "reanchor" or not clip.exists():
            print(f"skipping {e['label']}: no clip")
            continue
        shutil.copy2(clip, out / "clips" / clip.name)
        dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(clip)],
                             capture_output=True, text=True).stdout.strip()
        events.append({"label": e["label"], "mode": "reanchor", "reference": copy(e["reference"]),
                       "clip": f"{base}/clips/{clip.name}", "seconds": round(float(dur), 1)})
        print(f"{e['label']:10} {clip.stat().st_size / 1e6:5.1f} MB  {dur} s")
    config = {
        "name": args.scene,
        "model": "recorded",
        "loop": {"fade_seconds": pano.get("loop", {}).get("fade_seconds", 3)},
        "events": events,
        "reference": copy("reference.png"),
        "still": copy("pano_front.jpg"),
        "garden_url": GARDEN_URL,
    }
    (out / "scene.deploy.json").write_text(json.dumps(config, indent=1))
    total = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"wrote {out}  ({total / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
