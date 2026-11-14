# One Orbis Dynamic stream, shown as a 360° panorama on a head-locked sphere

**2026-11-14 ・ status: standing ・ scope: how the world is generated and displayed; interaction details live in the code**

## What forced the choice

Only Orbis Dynamic holds a reference image and a static camera (Stable re-composes from the
first frame), and Dynamic serves **one session at a time for everyone on Reactor** — proven
with a second, unrelated account. A design that needs four to six concurrent Dynamic streams
cannot run.

## Decision

Marble pano → rotate so the front is the image centre and the seam is behind the viewer →
soften the poles → squash 2:1 to 1664×960 (`tools/pano_reference.py`) → one Orbis Dynamic
session (`set_image` + opening prompt) → the browser maps the full 16:9 frame back to
360°×180° on a **head-locked sphere** (skybox trick: view translation dropped, so it sits at
infinity). Seam cross-blended over 2% of width; poles fade to colours measured from the
picture. Interaction is by **pointing** (trigger / pinch / click) — the sphere cannot be
touched. The Mac only mints JWTs (`/api/token`); the stream goes straight to the headset.
The Marble still is shown until the stream arrives, and whenever Dynamic is busy.

## Why not the alternatives

| Alternative | Its case | Why not |
|---|---|---|
| Box room, one Dynamic stream per wall (the previous design) | 4× the pixel density per degree; walls you can touch | Needs 4–6 concurrent Dynamic sessions; only one exists |
| Box room, front wall live + other walls still | Keeps touchable walls | Only one wall is generated; global events (evening, rain) cannot reach the rest except by colour grading |
| Box room sampling the equirect stream in the shader | Same picture as the sphere, plus touchable walls | User chose the sphere (2026-11-14) |
| Near sphere, radius ≈ 2.4 m (option A) | Touch to ripple | User chose a head-locked sphere (option B, 2026-11-14): stable under head movement |
| Stable instead of Dynamic | Spare capacity, half the price | Re-composes the reference from the first frame; camera keeps moving (four prompt strategies tested) |

## What this rests on

| Assumption | Status | Evidence, or the check that would settle it |
|---|---|---|
| Dynamic keeps the squashed equirect layout (curved horizon, no straightening) | **holds ~70 s unsteered with the time-lapse prompt; a scene-wide steer breaks it** (11:05, 90 s): oak, sun, sheep and mountains stayed put to 70 s (seam diff 3.6→11.8), "Golden hour" at 35 s warmed the light without moving anything, but "Evening" at 67 s re-composed the frame within 13 s — flat horizon, oak shrunk then gone, lake widened (seam 14→16). Earlier: the first prompt pushed in within ~20 s in one run; naming grazing sheep pulled sheep into the foreground | Steer prompts that restate the fixed-panorama framing; or make big events a re-anchor to a pre-made reference variant (reset + `set_image`) |
| Frame edges stay close enough for the 2% blend to hide the seam | **ok while the layout holds**: left/right edge difference 4.3/255 at 10–20 s (reference 2.7), 12.3 at 30 s; failed in the run that pushed in | Watch `seam_diff` in `tools/orbis_test.py` reports |
| 832 px over 360° is acceptable | accepted by the user | ≈2.3 px/deg native (4K delivery is upscaling) |
| The pipeline works end to end | **verified** on Stable: token → session → `set_image` → stream → sphere at 2560×1440, 15–18 fps | `?model=stable` |

## Accepted costs

A quarter of the per-degree detail of the wall design. Nothing to touch. At any moment the
one Dynamic server may belong to someone else; the still covers that.

## What would reverse this

Dynamic straightens the panorama within a minute even with periodic re-anchoring → go back to
a perspective wall (box room front wall) for the live stream. Visko adds Dynamic capacity →
the per-wall design becomes possible again (it is in git history before this change).
