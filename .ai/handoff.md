# Current state

**Last updated: 2026-11-14 10:45 PST**

> This file **expires** — update it at the end of each working session. Earlier test logs
> (per-wall Stable/Dynamic runs, four-wall capacity failure) are in git history; their
> conclusions are in CLAUDE.md and `decisions/`.

## Where things stand

| Item | State |
|---|---|
| Design | **One Orbis Dynamic stream on a 360° head-locked sphere** — `decisions/single-stream-panorama.md`. The box-room / per-wall design is superseded (git history before this change) |
| Scene `hillside` | Marble draft pano (world `e60f6310…`), front = pano lon 12°, `reference.png` 1664×960 from `tools/pano_reference.py` |
| Web app (`web/`) | Sphere shader (seam blend, pole fade, still→live crossfade, ripples), pointing input, Reactor live connection with busy-retry, event buttons + prompt box, `/api/token` and `/api/end-session` |
| Verified | Still pano orientation and the seam behind the viewer on desktop; **live pipeline end to end on Orbis Stable** (2560×1440, 15–18 fps on the sphere) |
| Dynamic on the panorama | **First run 10:47 (~40 s, then stopped):** opening matched the reference, then the frame pushed in like a perspective shot (sheep and oak growing) and by ~27 s the seam behind the viewer showed unrelated content on each side |
| Panorama prompt test (11:00, Dynamic, 40 s each) | **Time-lapse wording keeps the layout for 30 s** and is now the opening prompt; see `scenes/hillside/scene.json` variants_notes |
| 90 s run (11:05, time-lapse prompt, steers at 35 s and 67 s) | Layout held to 70 s; Golden hour = gentle warming, layout kept; **Evening re-composed the scene** (flat horizon, oak gone by 88 s). Frames: `~/Assets/LivingRoom/scenes/hillside/tests/pano-20261114-110529-long90/contact.jpg` |
| Event re-anchoring (11:15) | **Built and verified live on Dynamic**: Evening = reset + `set_image(events/evening.png)` on the same session; 8.8 s from click to the new picture fully faded in, frozen frame shown throughout, layout intact front and back. Offline, an event swaps the still instantly. References `events/{evening,rain,night}.png` made by editing `reference.png` with Codex image gen (layout kept), normalised with `pano_reference.py --event` |
| LingBot World 2 fallback (11:55, personal account) | **Works**: Dynamic busy → LingBot live in 7.5 s; Evening re-anchor 2.4 s; quiet re-anchor every 40 s fired; ~50 fps. Switching back to Dynamic when it frees up is built but **not yet seen** (Dynamic stayed busy) |
| Not verified | Fallback → Dynamic switch-over; Rain / Night / Morning re-anchors live; seam after the edge-crop + 3% blend change (a thin light line showed at the seam in the Evening run); Quest headset; audio; steering on the sphere; whether re-anchoring every 15–20 s keeps the layout |

## Next step

One live run through Morning → Evening → Rain → Night in the page, looking behind after each
to check the seam fix. Then the Quest: `npm --prefix web run dev`, Go live, Enter VR.

## Orbis keeper (2026-11-14 11:40)

`tools/keeper.py` + skill `orbis-keeper`: holds the one Dynamic session for 1 h (extend =
reset to 1 h from now, user's call each time; 3 h hard session ceiling); the web page adopts
the held session via a bound token (`/api/token?attach=1`) and its Stop leaves the session
to the keeper. **Verified:** waiting/retrying while Dynamic is busy, clean give-up with no
session after the wait limit. **Not verified:** holding, extend, page attach, release — Dynamic
was busy for every attempt 11:33–11:40. A second keeper started from another shell at
11:38 (`start --wait-minutes 30`, pid 32025) was still waiting at 11:40; it was left alone.

## In flight / undecided

- **Dynamic is one server for all of Reactor.** It was taken by someone else on every
  attempt this morning. Ask Visko to add capacity or reserve it for demos.
- Layout holds ~70 s unsteered; pressing the current event again (e.g. Morning) re-anchors and
  pulls it back. An automatic re-anchor every ~60 s is not built.
- In VR the HUD is invisible: Go live / prompts must be pressed before Enter VR, or driven
  from the Mac by attaching a second connection to the same session (Reactor supports it).
- Sky artifacts from the draft pano (dark shapes above the horizon) are in the reference.

## Things that will bite you

- **Billing runs from `ready`, idle or not.** Always Stop. Up to four orphaned Stable
  sessions from the 403 bug (10:33) ran until their 15-min cap (~10:48).
- A session-scoped JWT only acts on sessions it created — mint one per connection and reuse
  it (fixed in `web/src/live.js`).
- `.env` is not in git; a fresh clone needs the keys from a teammate.
- Port 5173 is often held by another project's Vite; this app uses 5174 (`strictPort`).
- Rotate the hackathon keys after the event; they appear in the chat transcript.
