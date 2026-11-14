# Living Room — entry point

Read [README.md](README.md) for what this is, then [.ai/README.md](.ai/README.md) for
where project knowledge lives (the Fieldnotes skill in `.claude/skills/fieldnotes`
maintains it — use it when writing down a finding or a decision).

## Secrets

- `REACTOR_API_KEY` lives only in `.env` (git-ignored). Never put it in browser code:
  the Vite dev server mints a JWT (`/api/token`, `web/vite.config.js`) via
  `POST https://api.reactor.inc/tokens` with header `Reactor-API-Key`.
- **A session-scoped JWT can only act on sessions it created.** Mint one per connection and
  pass the same string to `connect()`. A resolver that mints per request gets 403 on
  `get session` right after creating it — and that session keeps running, billed, with no
  handle to end it (happened 2026-11-14). The API key itself, as `Authorization: Bearer`,
  can `DELETE /sessions/{id}` for any session on the account (`/api/end-session/<id>`).

## Platform constraints (verified 2026-11-14 unless marked)

Reactor billing (docs.reactor.inc/resources/billing, read 2026-11-14)

- **Billed per second from `ready` until the session is terminated — even idle, even with no
  `start`.** "Connect-only" probes are not free. `connecting`/`waiting` are free.
- Per minute: Orbis **Stable $0.582**, Orbis **Dynamic $1.254**, Helios / LongLive 2 /
  SANA-Streaming $0.102, LingBot $0.300, LingBot World 2 $0.420, Vidu S2-Editing $0.420,
  FastH3 $2.100. Live rates: `GET https://api.reactor.inc/pricing` (no auth).
- Docs call Stable and Dynamic "two versions of the same model"; the only documented
  difference is that Dynamic accepts `set_resolution` at any time (Stable reads it at
  `start`). The better image anchoring we measured on Dynamic is not documented.

Reactor / Visko Orbis — docs: https://docs.reactor.inc/model-api-reference/visko-orbis-stable/overview

- **The hackathon key can only open `reactor/visko-orbis-stable` and
  `reactor/visko-orbis-dynamic`.** Every other Reactor model (SANA-Streaming, Vidu,
  LingBot, …) returns 403 `requested model is not available to this API key`.
- **Rate limit is on session creation, not concurrency:** `sessions_per_minute` = 10 per
  model (HTTP 429 `quota_exceeded`, `retry_after_seconds`). Opening 8 sessions ~10 s apart
  kept all 8 READY. Not yet tested: 8 sessions *generating* at once.
- Orbis has **no video input track** — outputs only `main_video` + `main_audio`
  (read from the session schema). Video-to-video is not possible with Orbis.
- Generation is 832×480; `1080p` / `2k` / `4k` are delivery tiers. Non-16:9 reference
  images are squashed, not cropped — crop before upload. (docs)
- `set_image` only anchors the first chunk; sending it mid-run does nothing. To change
  the image: `reset` → `set_image` → `set_prompt` → `start`. `reset` keeps the session,
  so it does not count against the creation rate limit. (docs)
- Prompt changes land at the next 33-frame chunk boundary (~1.83 s) and take 2–4 s to
  settle. Steering faster than that queues competing morphs. (docs)
- First chunk after `start` emits 0 frames; picture arrives around chunk 2. (docs)
- **Measured 2026-11-14 (front-wall run, Stable, image + prompt):** 18 fps; delivery
  defaults to `2k` = 2560×1440; `available_resolutions` = 1080p / 2k / 4k (no native 832
  tier); chunk 0 emits 0 frames at ~2.3 s, first frame at ~4.2 s; then a 33-frame chunk
  every ~1.84 s (real time). `image_accepted` reports the uploaded size (1664×936).
- **Use `visko-orbis-dynamic` for walls, not Stable** (2026-11-14, one 40–80 s run each,
  same front-wall image + prompt): Dynamic's first frame matched the reference (mean abs
  diff 5.7/255 vs 26–33 for Stable variants) and the camera stayed put for 40 s; Stable
  pushed in to grass level from the first frame and kept moving, with or without
  passthrough or an environment-first prompt. The names are misleading.
- Dynamic's first frame came later (~6.4 s vs ~4 s) and fps ramped 14 → 17 over the first
  15 s. A Dynamic session once failed with 429 `no available capacity` (server-side, not
  our rate limit) — retry after a few seconds.
- **Dynamic gives us only ONE concurrent session** (2026-11-14, 09:23 PST): with one
  Dynamic session open, a second got 429 `no available capacity` 4/4 tries over 25 s;
  closing it made the next open succeed. Stable opened fine at the same moment. Re-checked
  09:38–09:44: 11/11 attempts to hold two at once got exactly one. A second key
  (`REACTOR_API_KEY_2`) was refused too while key 1 held a session — **but both keys are on
  the same Reactor account and user** (`GET /me`), so that alone does not separate "pool"
  from "account". What does: account limits come back as `quota_exceeded` with a `limit`
  (as `sessions_per_minute` did), while this is `no available capacity: no available
  servers`, and Reactor docs say a model without `workers` serves **one session per
  instance**. **Settled 10:06 with a key from a separate Reactor account**
  (`REACTOR_API_KEY_ALT`, different `account_id`): while the hackathon account held one
  Dynamic session, the other account got the same `no available capacity`; alone, it opened
  at once. So it is the model's server pool — effectively **one Dynamic session for
  everyone on Reactor at a time**. Whoever holds it blocks all other users and teams. More
  keys or accounts do not help; only Visko adding instances does. At 09:06 we were refused
  with none of ours open — someone else held it.
- **Balances and quotas are readable:** `GET /me` → `account_id`, then
  `GET /accounts/{id}/credits` (`balance_usd`) and `GET /accounts/{id}/quotas`, with
  `Reactor-API-Key`. Hackathon account 11:40: **$84,913**, `concurrent_sessions` 125, no
  per-model quota — a shared event account. Personal account: $5.00, concurrent 5.
- **Who holds Dynamic is visible by elimination** (11:40–11:43, 15 s samples): every drop in
  the hackathon balance was an exact multiple of $0.0097 = one Stable-second (30–100 Stable-
  seconds per 15 s, i.e. other teams running ~2–6 Stable sessions). A Dynamic-second is
  $0.0209 and 209 is coprime with 97, so no Dynamic usage posted to this account while
  Dynamic was busy -> the holder was on another account. Assumes billing posts in near real
  time (the steady drops suggest it does); the personal account stayed at $5.0000 after its
  ~15 s Dynamic test at 10:06, so small/odd sessions may post late or not at all.
- `REACTOR_API_KEY_ALT` (a personal account, $5 starter credit) can also open SANA-Streaming
  and LingBot World 2, which the hackathon key cannot.
- The hackathon key's account looks shared beyond our team: `sessions_per_minute` showed
  `current=10` after 3 of our own creates. Treat the 10/min and concurrent quotas as shared.
- **An unclosed session keeps its server until its max duration.** A crashed script's
  session blocked all Dynamic opens for ~5 min. Always disconnect in `finally`, and keep
  `max_session_duration_seconds` tight in tests.
- **Stable cannot be prompt-locked** (2026-11-14, four 40 s runs, cinemagraph / fixed-tripod
  prompt): with or without passthrough and with another seed, the *first frame* already
  re-composes the reference (low wide shot, big sky, horizon dropped; diff vs reference
  21–38, Dynamic 5.7), then the camera keeps moving. So re-anchoring Stable with `reset` does
  not help either — it never starts on the reference.
- **A steering prompt is scene content, not an instruction.** "The camera stays fixed on its
  tripod." sent mid-run (passthrough) put a camera on a tripod into the shot and the scene
  collapsed within 10 s. Never name the camera, lens or rig in a prompt.
- `download_recording` right after `pause` timed out (playlist not ready after 60 s).
- `prompt_accepted` echoes the prompt as sent; the server-side rewrite (passthrough
  false) is not visible to the client.
- Write motion as what the camera sees ("trunks slide from right to left"), not intent
  words. For lateral walls use tracking, never "pan" (pan = rotation, no parallax).

World Labs Marble API — `WORLDLABS_API_KEY` in `.env`, header `WLT-Api-Key`

- A finished `GET /operations/{id}` returns `response.assets.imagery.pano_url = null`;
  `GET /worlds/{world_id}` has the URL. `tools/marble_pano.py --world <id>` re-downloads
  without paying again. (2026-11-14)
- `marble-1.0-draft` text prompt costs 230 credits; its pano was 2304×1152 (6.4 px/deg).
  Pano generation is billed 80 credits on every model, so a pricier model may not give a
  better pano — unverified.

Other Reactor models on the panorama (2026-11-14, personal account `REACTOR_API_KEY_ALT`,
60 s each, `tools/alt_model_test.py`; frames in ~/Assets/.../tests/{helios,lingbot-world-2}-*)

- **LingBot World 2** ($0.42/min, 1664×960 native, 48 fps, first frame 0.7 s): camera axes idle =
  a truly locked camera; every landmark stayed put for 60 s (diff vs reference ≤ 20, seam ≤ 9 —
  best of all models). But it keeps the reference's flaws (sky artifacts), adds wandering
  animals (a black cow, walking sheep), the bottom edge degrades after ~50 s, dark lines at the
  frame edges, and "Golden hour" barely registered.
- **Helios** ($0.102/min, 640×384 native, 1280×768 at default 2× SR, first frame 3.1 s; it
  centre-crops to 5:3, so feed it a 5:3 *squashed* reference): drifts within 8 s — blown-out sun,
  changing hill shape, seam up to 93 by 34 s. But `set_conditioning` (new image + prompt) mid-run
  switched to the Evening reference on the next chunk with the layout intact (diff 4.6, seam 4.2)
  — no `reset`, no warm-up.

Quest 3 / WebXR

- WebXR exposes head + hands only; body is IK-inferred.
- Quest Link / Air Link do not run on macOS — there is no PC-tethered fallback on this
  team's hardware. The single-stream design keeps the headset at one decoded stream.
- The panorama is a head-locked sphere (skybox trick), so it cannot be touched; input is
  pointing (`selectstart` from controllers or hand pinch).
