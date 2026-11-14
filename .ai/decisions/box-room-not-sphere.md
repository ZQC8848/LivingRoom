# The world is shown on the walls of a box, not on a 360° sphere

**2026-11-14 ・ status: standing ・ scope: display geometry only; not how walls are generated**

## What forced the choice

Orbis outputs ordinary 16:9 perspective video from one reference image. Showing it
around the player needs some projection, and the obvious one (equirectangular sphere,
as in the earlier 4DGS World Lab pipeline) fights the model.

## Decision

A rectangular room 4.8 × 4.8 × 2.7 m. Each of the four walls is a native 16:9 Orbis
stream, uncropped. Floor and ceiling are square and take a centre 1:1 crop (or are
static). Seams at the room edges are covered by visible trim, not hidden.

## Why not the alternatives

| Alternative | Its case | Why not |
|---|---|---|
| Equirect sphere, squash 2:1 → 16:9 and back | One session, one seam, already proven with Seedance | Orbis anchors only the first frame and is autoregressive; perspective priors are likely to straighten the horizon within a few chunks. 832 px over 360° ≈ 2.3 px/deg |
| Cube with 1:1 faces, squash 1:1 → 16:9 | Standard cubemap | Model sees horizontally stretched content and may "correct" it over time |
| Cube, centre-crop 16:9 → 1:1 on every face | No distortion | Throws away 44% of width on the faces that matter most |

## What this rests on

| Assumption | Status | Evidence, or the check that would settle it |
|---|---|---|
| A 90°-HFOV perspective wall is something Orbis holds stably | unverified | Run one wall 2–3 min with a static-camera prompt; look for drift |
| Overhead floor shots hold (no horizon appearing) | unverified | Same test on the floor prompt; centre crop discards edges where intrusions start |
| Visible seams are acceptable as design | unverified | Show it to two people |

## Accepted costs

Up to 6 sessions instead of 1. Twelve seams between independently generated faces.
Floor/ceiling waste 44% of their frame.

## What would reverse this

The single-wall test shows Orbis keeps a squashed equirect frame stable for > 2 min —
then a sphere becomes the cheaper option again.
