"""Generate a Marble world from a text prompt and keep only its panorama.

    tools/.venv/bin/python tools/marble_pano.py hillside

Reads scenes/<scene>/scene.json ("marble": model, seed, prompt), writes to
~/Assets/LivingRoom/scenes/<scene>/: pano.<ext>, world.json (full operation result).
Needs WORLDLABS_API_KEY in .env. marble-1.0-draft text prompt = 230 credits (~$0.18).
"""

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

API = "https://api.worldlabs.ai/marble/v1"
ROOT = Path(__file__).resolve().parent.parent
ASSETS = Path(os.environ.get("LR_ASSETS", Path.home() / "Assets" / "LivingRoom")) / "scenes"


def load_env():
    env = ROOT / ".env"
    for line in env.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def call(method, path, body=None):
    req = urllib.request.Request(
        API + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"WLT-Api-Key": os.environ["WORLDLABS_API_KEY"], "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def fetch_pano(world_id, out):
    # The finished operation's response has imagery.pano_url = null (seen 2026-11-14);
    # GET /worlds/{id} has it. Retry briefly in case it is filled in late.
    for _ in range(12):
        world = call("GET", f"/worlds/{world_id}")
        world = world.get("world", world)
        pano_url = ((world.get("assets") or {}).get("imagery") or {}).get("pano_url")
        if pano_url:
            break
        time.sleep(5)
    else:
        sys.exit(f"world {world_id} has no pano_url yet")
    (out / "world.json").write_text(json.dumps(world, indent=1))
    ext = Path(pano_url.split("?")[0]).suffix or ".png"
    dest = out / f"pano{ext}"
    urllib.request.urlretrieve(pano_url, dest)
    print(f"pano -> {dest}")


def main(scene, world_id=None):
    load_env()
    cfg = json.loads((ROOT / "scenes" / scene / "scene.json").read_text())["marble"]
    out = ASSETS / scene
    out.mkdir(parents=True, exist_ok=True)
    if world_id:  # re-download from an existing world, no new generation / credits
        return fetch_pano(world_id, out)

    op = call("POST", "/worlds:generate", {
        "display_name": f"living-room-{scene}",
        "model": cfg["model"],
        "seed": cfg.get("seed"),
        "world_prompt": {"type": "text", "text_prompt": cfg["prompt"]},
    })
    op_id = op["operation_id"]
    print(f"operation {op_id} started")

    t0 = time.time()
    while True:
        time.sleep(5)
        op = call("GET", f"/operations/{op_id}")
        if op.get("error"):
            sys.exit(f"failed: {op['error']}")
        if op.get("done"):
            break
        print(f"  {time.time() - t0:5.0f}s  {json.dumps(op.get('metadata'))[:120]}")

    (out / "operation.json").write_text(json.dumps(op, indent=1))
    print(f"done in {time.time() - t0:.0f}s, cost {op.get('cost')}")
    fetch_pano(op["response"]["world_id"], out)


if __name__ == "__main__":
    # usage: marble_pano.py <scene> [--world <world_id>]
    argv = sys.argv[1:]
    wid = argv[argv.index("--world") + 1] if "--world" in argv else None
    main(argv[0] if argv and argv[0] != "--world" else "hillside", wid)
