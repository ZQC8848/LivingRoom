# Current state

**Last updated: 2026-11-14 21:33 PST**

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
| VR panel + USB preview (12:05) | 3D panel (Go live/Stop + events, hover, grip re-centre) built and checked on desktop with `?panel=1`; `tools/quest.sh` written. **adb is not installed on this Mac yet** (`brew install android-platform-tools`); nothing tested in the headset |
| Not verified | Panel and everything else in the headset; Fallback → Dynamic switch-over; Rain / Night / Morning re-anchors live; seam after the edge-crop + 3% blend change (a thin light line showed at the seam in the Evening run); Quest headset; audio; steering on the sphere; whether re-anchoring every 15–20 s keeps the layout |

## Next step

One live run through Morning → Evening → Rain → Night in the page, looking behind after each
to check the seam fix. Then the Quest: `npm --prefix web run dev`, Go live, Enter VR.

## Orbis keeper (2026-11-14 11:40)

`tools/keeper.py` + skill `orbis-keeper`: holds the one Dynamic session for 1 h (extend =
reset to 1 h from now, user's call each time; 3 h hard session ceiling); the web page adopts
the held session via a bound token (`/api/token?attach=1`) and its Stop leaves the session
to the keeper. **Verified (12:52–12:55):** waiting/retrying while Dynamic is busy (it was busy 12:16–12:52), clean give-up after the wait limit, hold acquired at 12:52:46, the web page adopted the held session (live in 18 s, status "keeper, 59.1 min left") and its Stop left the keeper holding the same session. Expiry verified 13:52: warnings at 9/4/0 min in `.keeper/keeper.log`, released at the deadline after 60.0 min (~$75.26). **Not yet exercised:** `extend`, `release`.

## A2A with the teammate's agent (2026-11-14 14:15)

`tools/a2a/` (README there): `server.mjs` wraps Claude Code or Codex as an A2A agent,
`send.mjs` talks to the peer. This Mac is on Zoe's tailnet (`tailscale switch` to go back to
our own; `qc-pc` is unreachable meanwhile) and serves port 41241 tailnet-only; the server
runs with all permission checks off, requests are logged to `.a2a/log.jsonl`.
**Verified:** Mac -> Zoe's Codex (`immerse-the-bay-zoezi-codex`, ~9 s per reply); the Dynamic
findings and the current plan were sent to it at 14:18. **Not verified:** Zoe -> this Mac
(one 401 at 14:09, no successful request yet). Her Codex cannot run commands when called
over A2A ("windows sandbox failed"), so it only answers from what it already knows.
The server is a foreground process: it stops when the terminal/session that started it ends.

## Two-session relay (2026-11-14 19:07)

Dynamic has two servers now. `keeper.py start --sessions 2` holds both; with `orbis.pano.loop`
in scene.json the live page runs a **relay**: the run on the sphere plays on one session
while the other is anchored and started, then a 3 s live-to-live cross-fade and the roles
swap (`web/src/live.js` relay section, two video decks in `liveMain.js`). No frozen frame.
**Verified on desktop (19:01-19:07, both held Dynamic sessions):** timed loop, hand-overs at
27 s and 57 s, old run kept playing under the fade; Evening pressed mid-run: Morning kept
playing 7.5 s, then faded to Evening, and the loop continued on the Evening anchor.
**Not verified:** in the headset (two 2560x1440 decodes overlap for ~10 s per hand-over);
steers (Golden hour) are lost at the next hand-over; relay with a one-session hold falls
back to the frozen-frame re-anchor, and that path has no timed loop.
The page uses BOTH slots in relay mode, so a teammate attached to slot 2 gets reset by it.

## Custom prompts paint a new reference (2026-11-14 19:24)

Typing a change ("heavy snow covers everything") no longer steers: the dev server's
`POST /api/edit` has `google/gemini-3.1-flash-lite-image` (OpenRouter, `OPENROUTER_API_KEY`)
paint the request onto the scene's **original** reference.png (always the original, never the scene on the sphere: edits do not stack, since 20:58; the server ignores any base the client sends) (3-4 s, ~$0.034) while
`anthropic/claude-haiku-5.5` turns the words into the scene sentence of the Orbis prompt
(`orbis.pano.custom_prompt` in scene.json); the page then re-anchors on the result like any
event. Results are cached in `<assets>/custom/<hash>.{jpg,json}` by text.
Model choice: `tools/image_edit_test.py`, contact sheets in `tests/edit-20261114-19*/`.
**Verified live (relay, desktop):** submit -> painted in 3.5 s -> hand-over 10.5 s after
submit -> faded in by 13.8 s; the next timed hand-over kept the snow. **Not verified:** the
seam behind the viewer on painted references;
the model sometimes adds objects (extra sheep in a fog test). No text input in VR yet.

## Relay without the keeper + prompt director (2026-11-14 20:51)

- **Loop needs two sessions; the page now opens its own second one** (`web/src/live.js`
  `armRelay`): keeper holds two -> its slot 2; otherwise an own session ("relay · own sessions
  ($2.5/min)" in the status line; takes all of Dynamic while live, Stop ends both). Second
  server taken -> "no loop: second session busy, retrying" every 30 s. A line that ends from
  outside (15-min cap, keeper hold over) is reopened (`statusChanged` -> `lineLost`).
  **Verified live (desktop, no keeper):** busy at first, armed on the 30 s retry, timed
  hand-over 22 s later. **Not verified:** that Stop really ends both own sessions (the user was
  watching the page, so it was not stopped); recovery after the 15-min cap.
- **Custom prompts go through a "director"** (`web/vite.config.js`: `DIRECTOR_INSTRUCTION`,
  `lintPrompt`, `composePrompt`; scene.json `frame` / `layout` / `fixed` / `fixed_sentence`):
  one claude-haiku-5.5 call returns `{moving, motion, ambience, static_request}`; hard checks
  (no camera words, fixed things not in `moving`, motion present, length); one retry, then the
  viewer's words. Runs in parallel with the picture (~4 s total). Cached prompts carry
  `prompt_version`; an old one is rewritten without repainting. Why: the first version dropped
  the asteroids from "asteroids fall from the sky" and the template froze everything (CLAUDE.md).
  **Verified:** asteroids, snow, waterfall (with "the camera pans left" in the request, dropped
  by the director), chalkboard -> lint clean; asteroids live end to end.
  **Not verified:** the lint retry and fallback paths (no request has failed lint yet).

## Presets (2026-11-14 21:20)

Buttons are **Morning, Snow, Asteroids, Saturn, Rain** (`scenes/hillside/scene.json` `events`;
Golden hour / Evening / Night / Nebula are in `retired_events`, which the test tools still
read). Each preset has a fixed picture and a prompt written from it; presets never go through
the prompt director, only typed prompts do. The page opens on the Morning still with the
Morning button highlighted. Snow / Asteroids / Saturn share a snowy night because they were
stacked custom edits. **Verified:** buttons and stills offline. **Not verified:** Snow,
Asteroids and Saturn live on Orbis (prompts untested); the seam behind the viewer on them.

## Two experiences in one page (2026-11-14 21:33)

The teammate's art-side app (**The Garden of Consequences**, `contributions/bosch-art/`,
merged from `feat/bosch-art-handoff-20261114`, 1.4 GB via Git LFS) now runs **inside the same
page** as the live hillside, so switching never leaves VR:
- `web/src/shell.js` owns the one renderer, canvas, VR button and XR session; experiences
  register `{scene, camera, frame, activate, deactivate, ui}`; `switchTo(id)` fades to black
  (a sphere on the active camera), deactivates one, activates the other, fades in (~1.2-2 s).
- `liveMain.js` registers `hillside` (deactivate = `live.stop()`, so its sessions end).
- `web/src/garden/` is a port of her r6 `demo.js` / `demoModes.js` / `vrPanel.js` (changes
  marked `shell:`); media comes from `/garden/` = symlink `web/public/garden` -> her `public/`.
  It is preloaded 2.5 s after the hillside is up and stays paused until activated.
- Switch controls: "Garden ▸" in the hillside HUD and VR panel, "◂ Hillside" in the Garden's
  mode row and VR menu. `?exp=garden` opens on the Garden.
- XR controllers and the canvas are shared: every input handler checks `shell.is(id)`.
**Verified on desktop:** both experiences, reveal, a mode change, switching both ways,
presets after switching back, live being stopped when leaving the hillside, both VR panels
(`?panel=1`). **Not verified:** anything in the headset (the fade, panel placement after a
switch, two sets of controller listeners, memory with both loaded); her sound after a switch;
her Live Lab is not ported (needs her broker and tunnel). The standalone app in
`contributions/.../bosch-demo` is untouched and still runs on its own (port 5182).

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
