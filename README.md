# Living Room

A VR panorama that is alive. The viewer stands inside a 360° world streamed in real time by
Orbis, points at the sky to send ripples through it, and changes the world with words —
golden hour, evening, rain, night.

Built for the **Visko · Living Worlds** track (Orbis real-time video, Reactor platform).
Demo: Sunday, 2026-11-15.

## How it works

```
Marble text-to-pano (2:1)  →  tools/pano_reference.py  →  reference.png 1664×960 (squashed)
                                                              │ set_image + opening prompt
                                                              ▼
                                   ONE Orbis Dynamic session (Reactor, WebRTC, 2k, 18 fps)
                                                              │
                                                              ▼
            browser: full frame mapped back to 360°×180° on a head-locked sphere (WebXR)
```

- **One stream on purpose.** Orbis Dynamic is the only model that holds the reference and a
  still camera, and it serves one session at a time for everyone on Reactor.
- **The sphere sits at infinity** (view translation dropped), so head movement never
  distorts it. The left/right edges of the frame meet behind the viewer and are
  cross-blended; the poles fade to colours sampled from the picture.
- **Pointing, not touching:** trigger / pinch in VR, click on desktop, makes a ripple where
  you point.
- **Events:** Golden hour steers the running picture; Morning, Evening, Rain and Night
  re-anchor the same session to a pre-made reference (`events/*.png`, edited copies of the
  reference with the same layout) behind a freeze-frame transition, ~9 s.
- **Still first:** the Marble pano shows until the stream arrives, and whenever Dynamic is
  busy (the page retries every 10 s).
- The Mac's dev server keeps the API key and mints short-lived JWTs (`/api/token`); it can
  end any session by id (`/api/end-session/<id>`).

Why it is built this way: [.ai/decisions/single-stream-panorama.md](.ai/decisions/single-stream-panorama.md).
Current state: [.ai/handoff.md](.ai/handoff.md). Platform facts and limits: [CLAUDE.md](CLAUDE.md).

## Setup

```bash
cp .env.example .env          # put REACTOR_API_KEY (and WORLDLABS_API_KEY) in it — never commit it
cd web && npm install && cd ..
uv venv --python 3.12 tools/.venv && uv pip install --python tools/.venv/bin/python -r tools/requirements.txt reactor-sdk
```

Scene media lives in `~/Assets/LivingRoom/scenes/<scene>/` (symlinked into `web/public/scenes`):

```bash
tools/.venv/bin/python tools/marble_pano.py hillside --world e60f6310-08a9-4e1a-84ab-044b02844ffe
```

```bash
cd tools && ../tools/.venv/bin/python pano_reference.py hillside
```

## Run

Desktop (plain HTTP on localhost): drag to look, click to ripple, **Go live** to stream.

```bash
npm --prefix web run dev:local
```

**Quest 3 over USB (no LAN needed, recommended).** One-time: developer mode on the Quest
(Meta Horizon app), `brew install android-platform-tools`, a USB-C data cable, accept
"Allow USB debugging" in the headset. Then:

```bash
tools/quest.sh
```

It forwards the Quest's `localhost:5174` to this Mac over USB (`adb reverse`) and starts the
dev server. In the headset open `http://localhost:5174` and press **Enter VR** — localhost
counts as secure, so no certificate is needed. The Quest still needs its own internet for the
video stream. Debug the headset's page at `chrome://inspect` on the Mac.

**In VR** a panel floats in front of you: **Go live / Stop** and every scene event. Point and
pull the trigger (or pinch) to press; pointing anywhere else ripples the sky. Squeeze grip to
bring the panel back in front of you. `?panel=1` shows the panel on desktop for checking.

Quest over Wi-Fi (HTTPS, self-signed) still works when the LAN allows it:
`npm --prefix web run dev`, then `https://<mac-lan-ip>:5174`.

`?model=stable` swaps in Orbis Stable to test the plumbing when Dynamic is busy (its camera
drifts, so it is not the look). Live sessions are billed per second from `ready`; **Stop**
or closing the tab ends them, and the token caps any session at 15 minutes.

## Art and storytelling handoff

The independent painted Garden/Aftermath experience, shipped media, narration, concepts, production scripts and QA evidence are in [contributions/bosch-art](contributions/bosch-art/README.md). Read its merge notes before integrating; the existing technical app is preserved. Large media requires Git LFS.
