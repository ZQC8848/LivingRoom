# Paired-video reveal demo (bosch-demo): static, two videos, angular-distance mask

**Decided 2026-11-14.** Branch `feat/paired-video-reveal`.

## Context
The live Orbis page needs the dev server (`/api/token`, `/api/scene`) and a billed Reactor session.
The demo scene is two pre-rendered 2:1 equirect videos (heaven, hell) that must play on a plain
static host.

## Decision
- `web/src/main.js` is only a router: a scene with `scenes/<name>/media/manifest.json` runs
  `demo.js`; anything else runs the old `liveMain.js` (unchanged apart from the rename).
- Static build (`tools/build_static.sh`) sets `VITE_STATIC=1`, so the live code and the Reactor SDK
  are folded out of `web/dist`, and stages only the demo media (not the symlinked ~/Assets scenes).
- Heaven is everywhere; hell shows inside spherical caps opened by pointing. Mask =
  `1 - smoothstep(r - feather, r, acos(dot(dir, centre)))` in the fragment shader: round at any
  latitude, identical in both eyes. Trigger/pinch held = cap follows the ray; release closes.
  Desktop: click toggles.
- The two `<video>`s are kept in lockstep by comparing `currentTime` every 400 ms and re-seeking
  hell to heaven beyond 1.5 frames (wrap-around handled).
- No pole fade, no seam blend by default (the videos are already full 2:1 panoramas); both are
  manifest options (`projection.edge_crop`, `projection.seam_band`, `projection.front_yaw_deg`).

## Checks
`tools/check_media.py <dir>` (h264/yuv420p, 2:1, equal size/fps/frames/duration, faststart).
