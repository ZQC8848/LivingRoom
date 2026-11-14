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

## Latest result (2026-11-14): front wall on Orbis

`tools/orbis_wall_test.py hillside front` — 80 s, Stable, reference image + 98-word prompt.

| Check | Result |
|---|---|
| Opening matches reference | **No.** First frame (4.2 s) keeps the layout cues (sun upper left, hut right, slope) but the camera is near the grass and the sheep are big in the foreground |
| Static camera | **No.** Viewpoint keeps moving among the sheep |
| Long-run quality | Degrades from ~45 s: ground turns into green tufts on grey, lens looks wider |
| "Golden light" steer at 35 s | Not visible by 50 s |
| fps / size / warm-up | 18 fps, 2560×1440, first frame 4.2 s |

### Follow-up: three variables, 40–45 s each, no steering

| Run | Opening vs reference | Camera | Ground at 40 s |
|---|---|---|---|
| Stable + `passthrough` | Close (sheep small on crest, hut right) — diff 33 | Cuts between framings every ~10 s | OK |
| Stable + `env_first` prompt | Sheep pulled into foreground — diff 26 | Low, moving | Tufts-on-grey again |
| **Dynamic**, default prompt | **≈ identical — diff 5.7** | **Static: horizon, sun, crest, hut fixed** | OK, colours drift greener |

Dynamic added one large sheep grazing in the foreground (not in the reference). Contact
sheets: `~/Assets/LivingRoom/scenes/hillside/tests/*/contact.jpg` (`tools/contact_sheet.py`).

### Dynamic, 120 s with three steers (35 s golden light, 60 s one sheep bleats, 90 s evening)

- **Camera holds** for the whole run; by 70–80 s the crest line sits a little lower and the
  framing has crept, but no cuts and no ground breakdown.
- **Steering works.** Golden light builds gradually from ~40 s and is strong by 70 s;
  "evening" sent at 90 s gives a violet sky and dark hillside by 100 s. The bleat cannot be
  judged from stills.
- **Drift:** colour saturates steadily (grey-green → vivid green → yellow) even before the
  golden steer; a faint vertical light stripe appears near the left edge at 70–80 s; the
  extra foreground sheep from ~10 s stays all run.
- Diff vs reference climbs 5.8 → 25 (10 s) → 39 (40 s) → 44 (80 s) → 53 (100 s, evening).
- 18 fps steady after the first 5 s; first frame 5.9 s.

### Four walls at once: blocked by Dynamic capacity

`tools/orbis_room_test.py hillside` opened `left`, then `front` got 429 `no available
capacity` six times in a minute. Probe afterwards: one Dynamic session opens, a second is
refused every time while the first is open (see CLAUDE.md). **The four-wall design does
not run on Dynamic with our current access.**

## Next step

One live Orbis wall, recorded on the Mac: 16:9 first frame, static-camera prompt, three
state-change prompts over 2–3 min. Read actual fps, `delivered` resolution,
`available_resolutions`, warm-up time. **This is cheap and can invalidate the room design,
so it goes first.**

Then: run the room on the Quest (`npm --prefix web run dev`) and check fingertip contact
distance and ripple strength in-headset → 4 sessions generating at once → floor
(overhead) drift test → Mac relay feeding the atlas.

## In flight / undecided

- **Dynamic concurrency = 1 for all of Reactor** — confirmed with a key from a second,
  unrelated account (refused while ours held one, fine alone). Only Visko can add servers.
  Our long tests block every other user of Dynamic while they run. If not, pick a fallback: front wall live on Dynamic and the
  other faces as projected stills animated in the shader and colour-graded to follow the
  front wall's tone; or Stable (+ passthrough) on the side walls, which drifts.

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
