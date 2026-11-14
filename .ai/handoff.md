# Current state

**Last updated: 2026-11-14**

> This file **expires** — update it at the end of each working session.

## Where things stand

| Item | State |
|---|---|
| Design (room, topology, transitions) | Decided — see `decisions/` |
| Reactor key access | Verified: Orbis Stable + Dynamic only |
| Concurrency | Verified to 8 idle sessions; generating-at-once untested |
| Code | Nothing yet |

## Next step

One live Orbis wall, recorded on the Mac: 16:9 first frame, static-camera prompt, three
state-change prompts over 2–3 min. Read actual fps, `delivered` resolution,
`available_resolutions`, warm-up time. **This is cheap and can invalidate the room design,
so it goes first.**

Then: 4 sessions generating at once → floor (overhead) drift test → WebXR room shell →
Mac relay → ripple shader.

## In flight / undecided

- Floor and ceiling: live Orbis or static? Depends on the drift test and on decode budget.
- Wall content theme (e.g. boat on a misty river) not chosen.
- "Moving forward" via per-wall prompts (front dolly, back pull-back, sides tracking) is
  an experiment, not a commitment. Keep the floor static if it causes motion sickness.
- Video-to-video "shadow mirror" idea is parked: the key has no V2V model.

## Things that will bite you

- `.env` holds the real key and is not in git; a fresh clone needs it from a teammate.
- Opening sessions in a burst trips `sessions_per_minute` = 10 — stagger by ~6 s.
- The key also appears in the original chat transcript; rotate it after the event.
