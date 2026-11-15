# Bosch art and storytelling handoff

This directory contains the art-side work for Living Room. It is isolated from the latest technical implementation in the repository root so the engineer can merge deliberately. Nothing in `web/`, the original scene definitions, or the teammate's live-session implementation is replaced by this branch.

## Start here

- **30-second demo:** [MP4](video-edit/output/garden-of-consequences-30s.mp4), [English submission brief](video-edit/output/devpost-brief.en.txt), [edit notes and reproduction](video-edit/README.txt). Actual Quest recording; four optional prepared modes are labelled 3x.
- **Current runnable prototype:** [deployment/bosch-demo](deployment/bosch-demo/). This is the source and shipped media for public release r7; see deployment/publication-r7.json for the exact published source snapshot.
- **Published experience:** https://livingroom-bosch-demo.sandy-toad-8179.chatgpt.site/
- **Controls and research:** [stable guide](deployment/bosch-demo/public/guide/index.html), [Live Lab guide](deployment/bosch-demo/public/guide/live.html), [English narration/credits](deployment/bosch-demo/public/audio/transcript.en.html).
- **Integration notes:** [MERGE-NOTES.md](MERGE-NOTES.md).

```sh
git lfs pull
cd contributions/bosch-art/deployment/bosch-demo
npm ci
npm run build
npm run preview
```

Open `http://127.0.0.1:5183/`. `npm run dev` serves the same app on localhost port 5182. A secure HTTPS origin is required for headset use outside localhost.

From this handoff directory, run `node tools/verify-export.mjs` to verify the exported file hashes. The file manifest covers this contribution, not the upstream repository. No installed dependencies are committed.

## Current experience

**Reveal is the default main story.** Hold pinch/trigger in VR to reveal the other reading of the garden, then release. Desktop click toggles the reveal. The head-locked spherical projection has no automatic camera path. The single packed 2048 x 2048 video contains two 2048 x 1024 panoramas and shares one decoder/clock.

Four optional prepared-media modes are included: Garden Day/Night, Aftermath Day/Night, Garden Seasons and Aftermath Seasons. Light modes loop in 12 seconds, with a six-second light change; seasonal modes loop in eight seconds. The persistent desktop Mode menu and in-world MODES panel select them.

Eight English narration cues use the ElevenLabs stock voice Lily. The existing exported Suno score and authored environmental beds are shipped. Research is attributed in speech and captions; contemporary recovery/rest interpretations are distinguished from historical claims about Bosch. No Chinese narration or captions are added.

**Live Lab** at `/?experience=live` is a separate opt-in real Orbis Dynamic connection. It generates environmental sky/foreground material and composites it over the approved painting with a protected mask. It does not select a prerecorded clip when a weather prompt is sent. Default Reveal and the four optional prepared studies never request a model session.

The realistic sheep/hillside study remains the teammate's independent technical application. The two applications demonstrate different styles; no religious sheep-to-Bosch bridge or authored transition is planned. About 80% of the narrative emphasis belongs to the painted experience. Do not describe the hillside as running in this published art-side build.

## Live service setup

The public frontend contains **no API key or operator code**. The broker source is [tools/live/broker.mjs](tools/live/broker.mjs). Its local credentials, leases, budget state and operator code are intentionally excluded.

1. Copy `.env.example` to `.env` in this handoff directory and set a server-side `REACTOR_API_KEY`, or set that environment variable directly. `BOSCH_ENV_FILE` can name a different local environment file.
2. Install the official `cloudflared` executable separately. Its downloaded Windows binary is not committed.
3. Run `node tools/live/broker.mjs`, bound to loopback port 41243. In another terminal run `cloudflared tunnel --url http://127.0.0.1:41243 --no-autoupdate`.
4. Update `deployment/bosch-demo/public/live-config.json` to that tunnel's HTTPS URL and rebuild/redeploy the frontend. The checked-in URL records the r6 demonstration endpoint; it is temporary and may be offline later.
5. Open `http://127.0.0.1:41243/operator` locally for the private launch link/code. On Quest, enter that code before Enter VR. Select Garden or Aftermath, Start Live, then a weather request. Stop Live releases the owned session.

The broker fixes the model and token constraints server-side: one session per token, 180-second session cap, one lease at a time, a bounded daily request budget, exact-origin CORS, private operator authentication, registered session ownership checks and heartbeat cleanup. It neither adopts nor resets the teammate's keeper sessions. Stop and pagehide cleanup are included. Shared sponsor capacity can return 429; the UI shows busy rather than claiming to be live. This is an experimental service, not an always-available hosted model pool.

## What is included

| Directory | Contents |
| --- | --- |
| `deployment/bosch-demo/` | Current application source, locked dependencies, complete shipped imagery/video/audio, controls, research and guides |
| `deployment/review/` | Browser QA reports/screenshots and actual live stream evidence; failed attempts remain identifiable as failures |
| `deployment/*.json` | Published version provenance and explicit verification limits |
| `art-lab/` | Production/compositing scripts, prompts, masks, source art, historical iterations and model-test recordings |
| `handoff/` | Earlier packaged deliverables and live/season/day-night studies; these are history, not a replacement for the r6 app |
| `audio/` | User-exported Suno source recordings |
| `LivingRoom-sphere-review/` | Thirty spatial concepts, images, editable deck data and presentation exports |
| `LivingRoom-concept-review/`, `ConceptEditforME/` | Earlier concept outputs and paired painting sources |
| `conversation-previews/` | Standalone review pages previously shown in the conversation |
| `tools/` | Broker, A2A configuration templates/source, export and verification utilities |

`FILES.sha256.json` indexes content hashes. `EXPORT-REPORT.json` describes scope/exclusions. Large binaries and embedded-image snapshot artifacts use Git LFS; pull LFS before running or reviewing media.

Excluded: `.env` files, API keys, A2A/operator tokens, private runtime state, installed libraries/virtual environments, downloaded executables, numerical/object caches and regenerable per-frame image directories. Video masters, reference images, scripts, prompts, masks, reports and representative live recordings are retained. Original chat/session exports and unrelated starter projects are not published.

## Validation and limits

- Stable five-mode integration passed in `deployment/review/modes-local-r6/verification.json`.
- Final owned live run received 570 real video frames, accepted hot weather prompts, returned generated chunks, re-anchored the aftermath environment and stopped its session: `deployment/review/live-local-r6-final/verification.json` and `received-live-stream.webm`.
- Public r6 was deployed successfully. Its subsequent public smoke test reached the sponsor but returned shared-capacity 429; see `deployment/review/live-public-r6/failure.json`. Do not claim that attempt produced live frames.
- Audio r5 tests completed all eight English cues and checked mute/resume. Independent teammate checks are recorded in `deployment/review/peer-r5.json` and `peer-r6.json`.
- Controller/hand targeting checks are simulated browser tests. Physical Quest comfort, decoding performance, sound quality and hand tracking still need wearer acceptance. Weather rendering can remain stylized, especially rain/snow.

Historical documents may describe earlier formats or limitations. This README, MERGE-NOTES and the current app manifests take precedence when choosing what to integrate.


## r7 update

The visitor brief is now concise and technology-led: original artwork identity, a hand-revealed relationship between layers, authored masks/layouts, and bounded generation. Sources are collapsed under the brief. The first screen and eight short English cues identify Bosch and the original artwork. Live sky-driven exposure/tint and gentle cloud lighting affect the approved composition without UV or geometric displacement; averaged poles remove the old single-column dome lookup. Rendering checks replay recorded model frames and make no new live-model claim.
