# Architecture — one frame, one point, one prompt

**Last verified: 2026-11-14 (pipeline verified on Orbis Stable; Dynamic look not yet seen — it was busy)**

```
Browser (desktop or Quest WebXR)                     Mac dev server (Vite, web/vite.config.js)
  POST /api/token ───────────────────────────────▶  mints a 1 h JWT for one model,
                                                     sessions capped at 15 min (key stays here)
  Reactor JS SDK ── WebRTC ──▶ Reactor ── one Orbis Dynamic session
     set_image(reference.png) · set_resolution(2k) · set_prompt(opening) · start
  ◀── main_video (2560×1440, 18 fps) + main_audio
  POST /api/end-session/<id> ────────────────────▶  DELETE /sessions/<id> with the API key
                                                     (only when a client lost its handle)
```

## One frame

1. `main_video` plays into a `<video>`; a `VideoTexture` feeds the sphere shader
   (`web/src/panoMaterial.js`).
2. Each sphere fragment takes its view direction → lon/lat → (u, v) in the 16:9 frame. The
   2:1 stretch-back happens here; no resampling step exists anywhere else.
3. Near u = 0/1 (behind the viewer) the two frame edges are cross-blended over 2% of width.
   Above/below ±68° latitude the picture fades to zenith/nadir colours sampled from the
   video twice a second.
4. Until the first video frame, `uLiveMix` = 0 shows the Marble still (`pano_front.jpg`);
   it crossfades to 1 over 1.5 s.

## One point

Controller trigger / hand pinch (`selectstart`) or a desktop click → world direction →
`addRipple(dir, t)`; the shader bends the lookup direction around that point and adds a
glow on crests. A `sky-point` window event carries lon/lat for future steering hooks.

## One event

`scene.json` events are `steer` (a `set_prompt` on the running session — light changes only)
or `reanchor`. A re-anchor freezes the current video frame into the still texture
(`uLiveMix` = 0, same picture, no jump), plays a ring of ripples, then on the same session:
`reset` → `set_resolution` → `set_image(event reference, uploaded once per session)` →
`set_prompt(event opening)` → `start`. When a `chunk_complete` reports frames again (~6 s) the
live picture fades back in. Measured 8.8 s click-to-faded-in. Offline, the event's reference
becomes the still at once and the next Go live starts from it.

## One prompt

The HUD's event buttons and text box call `set_prompt` on the live session. Prompts are
scene content: describe the change only, never the camera or rig (see CLAUDE.md).

## Fallback line (LingBot World 2)

`web/src/live.js` runs one *line* (session) at a time. Go live tries Orbis Dynamic (adopting the
keeper's held session if there is one). If Dynamic answers "no available capacity" and the
scene has `orbis.pano.fallback`, it opens LingBot World 2 on the personal account instead
(`/api/token?model=reactor/lingbot-world-2` is minted with `REACTOR_API_KEY_ALT`, sessions
capped at 10 min) and probes Dynamic every 30 s. A probe that connects is promoted: freeze the
frame, attach its tracks, reset → anchor → start, fade in, then close LingBot. On LingBot the
page re-anchors quietly every 40 s, and the shader crops 1% off each frame edge (LingBot's
dark border columns). Measured 11:55: fallback live 7.5 s after the click; Evening re-anchor on
LingBot 2.4 s; ~50 fps.

## Failure paths

- Dynamic busy (429 "no available capacity"): keep the still, retry every 10 s, nothing billed.
- Connect fails after the session exists: disconnect, then `/api/end-session/<id>`.
- Tab closes: `pagehide` disconnects. Worst case the 15-minute cap ends the session.
