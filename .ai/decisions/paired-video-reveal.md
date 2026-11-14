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

## Packed single-decoder mode (2026-11-14)
`manifest.media.packed = paired.mp4`, `packedLayout = heaven-top-hell-bottom`: one 2048x2048 file,
one `<video>`, one `VideoTexture`; heaven and hell are the same object, so they cannot drift (two
videos drifted up to 5.2 frames under load in QA). Heaven v = 0.5 + 0.5*uv.y, hell v = 0.5*uv.y
(Three flipY), clamped half a texel inside each pane. Needs H.264 level >= 5.0 (16384
macroblocks). Custom ShaderMaterials get **no** video sRGB decode: the shader applies
`sRGBTransferEOTF` to video samples only (not the poster). After the first good frames,
`uVideoMix` stays at 1 through pause/seek/buffering; only a media error falls back to the poster.
Dual mode (heaven.mp4 + hell.mp4 + resync) is kept.

## Packed video is downloaded whole and played from a Blob (2026-11-14)
On the public host a plain `<video src>` had `seekable [0,0]` (seeks snapped back to 0). Packed
mode now `fetch`es `paired.mp4` (no Range; cache key `?v=<sha256 prefix>`), checks size
(<= 64 MiB, == `manifest.files[packed].bytes`) and sha256, and plays from a `blob:` URL: fully
buffered, exactly seekable. The poster shows during the download; any failure keeps the poster and
reports "cannot load packed video" (no Tap-to-start). Debug: `__reveal.storageMode`
(`loading|blob|failed`, dual = `url`) and `__reveal.fullyBuffered`. Dual mode is unchanged.
