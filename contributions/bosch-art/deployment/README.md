# Published Living Room demo

Public HTTPS: https://livingroom-bosch-demo.sandy-toad-8179.chatgpt.site/

Flat-painting motion review (51 numbered regions, pause/seek/half-speed; G03 intentionally still):
https://livingroom-bosch-demo.sandy-toad-8179.chatgpt.site/review/

Current release: **2026-11-14-r4**. Complete original-paint silhouettes replace
fragmented color keys for G01/G02/G04/G06/G07/G14, G03 is disabled, G20 opens a
complete wing with its sweep kept clear of the upper bird, fountain streaks and
droplets travel downward, and distant fire/smoke and roof-pipe smoke are stronger.
The horse fix, single packed video, source projection and reveal mechanism remain.

Choose **Enable sound**. One user-exported Suno score feeds bright/dark filter
branches on a shared audio clock; the reveal mixes in the darker perspective.
Environmental water/wind/bird/ember beds are **authored synthesis**, not mislabeled
Suno or ElevenLabs output. English ElevenLabs George stock-voice cues play once
on arrival, first reveal and first return; they do not repeat with the image loop.
Voice/captions, volume, mute/resume and replay are independent controls. No MP3
requests occur before opt-in. All audio is static; credentials stay out of the
site and release bundle. Physical Quest sound/performance remains unverified.

The existing LivingRoom prototype is integrated on `feat/paired-video-reveal`.
The deployed application uses the functional upstream commit recorded in
`bosch-demo/SOURCE_PROVENANCE.json`. The exact pushed Sites source, saved version
and successful deployment IDs are recorded in `production.json`.

Desktop: drag to look; click to reveal hell, click again to close. WebXR is wired
for held controller trigger / hand pinch, with one angular mask per hand and
release to close. Physical Quest testing was explicitly deferred by the user.

The white horse retains one painted head and mouth texture with a small anchored
nod. Release r3 adds 51 user-marked regions: source-paint RGBA wind, wing/leg
articulation, floating objects, fountains, both rivers, horizon fire and smoke.
Eight Orbis Dynamic crops were captured in an explicitly authorized idle keeper.
New generated RGB was rejected for exposure changes and weak wing articulation;
four stabilized motion fields are applied only to the original herd, stag,
bank-bird and bather cutouts, bounded to 2.5 source pixels. Earlier Orbis foreground
bird and keyed fire remain. The public demo needs no model sessions or API keys.

Playback uses ONE H.264 video and ONE VideoTexture. Heaven and hell are vertically
packed in a 2048×2048 container; each sampled panorama stays 2048×1024 (2:1).
Both states share every decoded frame, so there is no independent video clock.
The 5.41 MB packed file is fully downloaded and checksum-verified before Blob
playback. It is then seekable over the complete eight seconds and does not depend
on the host supporting open-ended media Range requests. A poster remains visible
while it loads. Host Range diagnostics are recorded separately from this contract.
Each loop is 8 seconds, 240 encoded frames, 30 fps; encoded rate does not constitute
an in-headset performance measurement. Loading errors fall back to the two posters.

## Pipeline

For r4, `compose_bosch_v9.py` uses `bosch_marked_motion_v9.py`; then run
`package_bosch_v9.py` and `integrate_bosch_v9.py`.
`motion-v9/verify_revision.py` checks coverage at reviewed
body/tail/wing/foot landmarks, the moving wing's clearance from its neighbor and
the intentionally still G03. `encoded-fix-contact.jpg` shows real encoded poses.
This is original-paint articulation and authored advection, not physical fluid
simulation or a claim that Orbis generated stable full panoramas.

`audio-v1/prepare_audio.py` reads the user's music export, synthesizes the explicitly
attributed environmental beds, normalizes all six MP3s and makes loop joins.
`audio-v1/soundscape-r4.js` is the shipped optional Web Audio client. The reviewed
English text is in `audio-v1/delivery/transcript.en.html`. No key is stored there.

Earlier r3 generation/review history:

1. `art-lab/prepare_bosch_v8.py`: numbered annotation catalog and clean model references.
2. `art-lab/run_bosch_v8_held.py`: short serial captures, no keeper lifecycle operations.
   Python SDK `disconnect()` ends sessions; this isolated adopted-session client
   pauses and exits without calling it. Never start it without an agreed idle window.
3. `art-lab/analyze_bosch_v8.py`: registration, exposure normalization, bounded motion
   fields and explicit rejection of generated RGB.
4. `art-lab/bosch_marked_motion.py` + `compose_bosch_v8.py`: isolated original-paint
   articulation, v7 horse/bird baseline, periodic 8-second composition and projection.
5. `art-lab/package_bosch_v8.py`: immutable r3 masters, packed file, posters, catalog,
   manifest and checksums under `handoff/bosch-demo-20261114/r3`.
6. `art-lab/integrate_bosch_v8.py`: media-only update of the existing prototype and
   a separate one-video flat-painting reviewer. No original application/player changes.
7. `bosch-demo/`: static build; Sites source helper pushes, packages, saves and deploys.

QA: `tools/verify-bosch-deployment.cjs <url> <report-name>`. Reports and screenshots
are under `deployment/review/`. Tests exercise real video loops, zero shared-clock
drift, mouse reveal, simulated production controller events, angular masks across
the back seam, color fidelity, exact buffered seek, narrow layout and poster fallback.
The hand-tracking session request is simulated; it is not a physical hand test.
Motion QA and generation decisions: `art-lab/motion-v8/render-review.json`,
`generation-review.json`, `expanded-motion-contact.jpg`. All 51 marked boxes have
measurable temporal changes; that diagnostic does not certify the artistic quality
of every tiny gesture. The flat reviewer supports further human review by region ID.

r4 reports: `deployment/review/{local-r4,public-r4}/verification.json`,
`deployment/review/{sound-local-r4,sound-public-r4}/sound-verification.json`, and
`deployment/review/{review-local-r4,review-public-r4}/review-verification.json`.
These cover desktop Chrome and simulated XR/controller wiring, not a physical
headset. Audio tests use a real button click without an autoplay-policy override.

Model generation and framing tests from older iterations remain in `art-lab/`.
This demo verifies this scene's pipeline, not automatic segmentation or animation
quality for arbitrary paintings.
