# Current state

**Last updated: 2026-11-14**

> This file **expires** — update it at the end of each working session.

## Where things stand

| Item | State |
|---|---|
| Design (room, topology, transitions) | Decided — see `decisions/` |
| Scene `hillside` reference images | Marble draft pano (world `e60f6310…`) projected to 6 faces, yaw 12°; walls join cleanly. Floor smeared, ceiling has sky artifacts, pano only 2304 px wide. View: `?scene=hillside` |
| Reactor key access | Verified: Orbis Stable + Dynamic only |
| Concurrency | Verified to 8 idle sessions; generating-at-once untested |
| WebXR room shell (`web/`) | Done on branch `feat/webxr-room`: 6 faces from one 3×2 atlas, trim, ripple shader, fingertip / controller / mouse touch. Verified on desktop only — **not yet on a Quest** |

## Next step

One live Orbis wall, recorded on the Mac: 16:9 first frame, static-camera prompt, three
state-change prompts over 2–3 min. Read actual fps, `delivered` resolution,
`available_resolutions`, warm-up time. **This is cheap and can invalidate the room design,
so it goes first.**

Then: run the room on the Quest (`npm --prefix web run dev`) and check fingertip contact
distance and ripple strength in-headset → 4 sessions generating at once → floor
(overhead) drift test → Mac relay feeding the atlas.

## In flight / undecided

- Floor and ceiling: live Orbis or static? Depends on the drift test and on decode budget.
- Wall content theme (e.g. boat on a misty river) not chosen.
- "Moving forward" via per-wall prompts (front dolly, back pull-back, sides tracking) is
  an experiment, not a commitment. Keep the floor static if it causes motion sickness.
- Video-to-video "shadow mirror" idea is parked: the key has no V2V model.

## Things that will bite you

- `.env` holds the real key and is not in git; a fresh clone needs it from a teammate.
- Opening sessions in a burst trips `sessions_per_minute` = 10 — stagger by ~6 s.
- Port 5173 on this Mac is often held by another project's Vite server; the room uses
  5174 with `strictPort`.
- Ripple tuning (`RIPPLE` in `web/src/config.js`) was judged on a desktop screen; 5 cm
  amplitude may be too strong or weak at 2.4 m in a headset.
- The key also appears in the original chat transcript; rotate it after the event.
