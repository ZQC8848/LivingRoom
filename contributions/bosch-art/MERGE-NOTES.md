# Engineer integration notes

## Branch layout

This branch starts from the latest `origin/main` observed during handoff (`636c39a`). The upstream `web/`, `scenes/` and technical tools are unchanged. All art-side work is under `contributions/bosch-art/`; merge this branch, then port selected modules/media into the technical app as needed.

## Current modules

- `deployment/bosch-demo/src/demo.js`: prepared-media player; single packed decoder and shared texture; validated full-Blob preloading; mode swaps freeze the old picture and preserve camera orientation.
- `src/revealMaterial.js`: angular reveal on the sphere; packed-pane sampling, half-texel padding and video sRGB correction.
- `src/demoModes.js`: five authored modes, desktop controls, in-world mode panel, hand-only MODES target and captions.
- `src/vrPanel.js`: controller/hand-ray selectable canvas panel. Menu selection must consume the gesture before Reveal.
- `src/liveGarden.js`, `liveEnvironment.js`, `liveSession.js`: isolated true-live environment experiment, compositing shader, scoped connection and event/frame timing. They load only on the Live Lab route.
- `public/audio/soundscape-r7.js`: one music clock, environmental mix, narration queue, English captions, mute/resume and per-mode cues.

Do not replace the root technical app's latest `live.js` with the older similarly named file inside the exported app. Those unused legacy source files are preserved as provenance; use the explicit r6 Live Lab modules above if integrating this experiment.

## Media contracts

`public/scenes/bosch-demo/media/manifest.json` and `modes/manifest.json` are the authoritative dimensions, durations and SHA-256 contracts. `paired.mp4` remains the approved r4 packed main story: 2048 x 2048, two 2048 x 1024 equirectangular panes, eight seconds, 30 fps. Its SHA-256 is `8db9a9e774c31e94b46cf0a782c5a8dfb3f3c287bad0c535f08afd8ac640ece2`.

Optional light/season media: 1536 x 768, 24 fps, 12/8 seconds. Standalone modes sample the full frame; returning to Reveal restores packed-pane UVs. Reuse the video and VideoTexture objects and keep view orientation unchanged.

Live Lab uses environment-only reference imagery with an explicit contained content region (48/736 offset, 640/736 height), plus approved painting plates and sky/foreground masks. Do not feed an arbitrary widescreen movie into a 2:1 sphere. Protected narrative subjects are drawn from the approved plate; unconstrained model output is not assumed to preserve architecture or cross-world correspondence.

## Backend boundary

The browser's broker API is `POST /v1/lease`, `POST /v1/lease/{id}/register`, `/heartbeat`, `/stop`; requests carry a private `x-live-code` header. The broker fixes the Dynamic model and issues a single-model, single-session JWT. A connection must reuse the same JWT, register its own session, stop explicitly, and tolerate 429 capacity errors. No browser API key or general dev-server token/edit routes should be exposed.

The currently published operator service is a separate Windows process and temporary tunnel; source is `tools/live/broker.mjs`. Replace the endpoint/configuration when operating on another machine or integrate the narrow contract with the teammate's existing backend. Configure an appropriate exact-origin allow-list. Do not touch another keeper-owned session.

## Presentation agreement

Two independent applications: realistic hillside technical study and painterly storytelling. Direct scenario selection; no invented religious bridge or special transition. Most storytelling remains in the painted garden/aftermath. Stable Reveal is the default. Prepared day/night/seasons are labeled recordings; live prompt steering is labeled Live Lab. Eight English narration cues are shipped. Keep research attribution and the distinction between historical interpretation and contemporary adaptation.

The nested `.openai/hosting.json` records the existing art-side Site identity. Its hosted source repository is separate from this GitHub repository. Do not run the Site workflow helper from this handoff checkout to rewrite the GitHub remote.

No merge, deployment change or keeper operation is requested by this handoff. The technical owner controls integration.


## r7 follow-up

The visitor brief at public/guide/artwork.html is intentionally short: work identity, gesture, authored layers/masks, optional bounded generation and reuse as a design method. Longer sources are collapsed. The first-screen credit and short English narration foreground Bosch. Follow sky light is authored scene relighting estimated from received sky pixels; geometry and viewing direction are not animated. Pole colour averaging replaces the old repeated-column lookup. Public offline replay verification is recorded in deployment/review/lighting-public-r7 and does not claim a new live model run.
