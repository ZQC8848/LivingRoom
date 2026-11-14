#!/usr/bin/env bash
# Build the static demo site: web/dist, no dev-server routes, no Reactor, no API keys.
#
#   tools/build_static.sh [--media DIR] [--scene bosch-demo]
#
# DIR holds heaven.mp4, hell.mp4, poster.jpg, manifest.json (default:
# ~/Assets/LivingRoom/scenes/<scene>/media). Only that folder is staged into the site, so
# nothing else under ~/Assets (test captures, other scenes) ends up in dist. Runs the media
# check first and refuses to build on failure.
set -euo pipefail
cd "$(dirname "$0")/.."
SCENE=bosch-demo
MEDIA=""
while [ $# -gt 0 ]; do
  case "$1" in
    --media) MEDIA="$2"; shift 2 ;;
    --scene) SCENE="$2"; shift 2 ;;
    *) echo "unknown arg $1" >&2; exit 2 ;;
  esac
done
MEDIA="${MEDIA:-$HOME/Assets/LivingRoom/scenes/$SCENE/media}"
python3 tools/check_media.py "$MEDIA"
STAGE="$(pwd)/web/.static-public"
rm -rf "$STAGE" web/dist
mkdir -p "$STAGE/scenes/$SCENE/media"
# Stage exactly the files the manifest names for its mode (packed: paired.mp4 only, no dual videos).
python3 - "$MEDIA" "$STAGE/scenes/$SCENE/media" <<'PY'
import json, shutil, sys, pathlib
src, dst = map(pathlib.Path, sys.argv[1:3])
m = json.loads((src / "manifest.json").read_text())["media"]
names = {"manifest.json", m.get("poster", "poster.jpg"), m.get("hellPoster") or "hell-poster.jpg"}
names |= {m["packed"]} if m.get("packed") else {m.get("heaven", "heaven.mp4"), m.get("hell", "hell.mp4")}
for n in sorted(names):
    if (src / n).is_file(): shutil.copy2(src / n, dst / n)
PY
(cd web && VITE_STATIC=1 VITE_DEFAULT_SCENE="$SCENE" LR_PUBLIC_DIR="$STAGE" npx vite build)
rm -rf "$STAGE"
cat > web/dist/_headers <<'H'
/scenes/*/media/*
  Cache-Control: public, max-age=300
  Accept-Ranges: bytes
H
echo "built web/dist  (scene $SCENE)"; du -sh web/dist
