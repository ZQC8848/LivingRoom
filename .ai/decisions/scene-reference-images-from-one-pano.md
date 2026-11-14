# Each face's Orbis reference image is projected from one Marble panorama

**2026-11-14 ・ status: superseded in part by [single-stream-panorama](single-stream-panorama.md) ・ scope: how first frames are made; not what each face's prompt says (that follows from the images)**

## What forced the choice

Six independent Orbis sessions only look like one place if their first frames agree. And a
prompt that describes something the reference image does not contain makes Orbis morph the
opening toward the text, so prompts have to be written *from* the images, not before them.

## Decision

1. Marble generates one 360° pano **directly from text** (`tools/marble_pano.py`, draft
   model, ~$0.18).
2. `tools/project_pano.py` colours every pixel of every face by the pano direction from the
   player's eye (centre, 1.6 m) to that point — walls, floor and ceiling alike. Floor and
   ceiling are projected as 16:9 (plane extended sideways) so Orbis can take them; the room
   shows their centre 1:1.
3. `projection.yaw_deg` in `scenes/<scene>/scene.json` is turned until no wall boundary cuts
   a moving subject (read it off `seams.jpg`).
4. Each face's prompt is then written from its own image plus the scene-wide settings.

## Why not the alternatives

| Alternative | Its case | Why not |
|---|---|---|
| GPT Image concept art first, then Marble image-to-pano | Tighter control of style | User chose text-to-pano directly (2026-11-14); one fewer step |
| Generic `e2p` perspective crops | Off-the-shelf | Pitching the camera to centre the wall keystones vertical lines; the room needs an off-axis (lens-shift) projection because the eye (1.6 m) is above wall centre (1.35 m) |
| Generate floor/ceiling separately (GPT Image) | Pano poles are Marble's worst region | User chose projection (2026-11-14): keeps floor and ceiling continuous with the walls |
| Ask Marble to put a big tree on each diagonal so boundaries land on static objects | Seams would fall on static things by construction | **Rejected by the user** (2026-11-14). Turning `yaw_deg` after generation does the same job for free |
| Write the six prompts first, from a scene design | Faster to start | Text that the image does not support makes the opening jump |

## What this rests on

| Assumption | Status | Evidence, or the check that would settle it |
|---|---|---|
| Projected faces join without a visible seam | **verified** | `project_pano.py` edge check: across-edge change / in-face column change = 0.93–1.11 on `hillside` |
| Horizon at the same height on all walls | **verified by construction** | 59% from the bottom = eye 1.6 / wall 2.7 |
| Draft pano resolution is enough | **failed for sharpness** | `hillside` pano is 2304×1152 = 6.4 px/deg → ~576 px per wall vs Orbis's 832 input |
| Pole regions are usable for floor/ceiling | **doubtful** | `hillside`: floor is a radial smear, ceiling shows dark geometric artifacts from the sky |

## Accepted costs

Floor/ceiling quality is whatever the pano's poles give. Wall references are upsampled
~1.4× before Orbis sees them.

## What would reverse this

Floor/ceiling references stay unusable after 2–3 pano attempts → generate those two faces
separately. A higher-resolution pano option appears → raise `--width` and re-check.

## Superseded 2026-11-14

Steps 1 and 3 still hold (Marble text-to-pano; yaw picks the front). The per-face eye-point projection is gone: the whole pano, rotated and squashed to 1664×960, is the one reference (`tools/pano_reference.py`). The tool `project_pano.py` was removed; it is in git history.
