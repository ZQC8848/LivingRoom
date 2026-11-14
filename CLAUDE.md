# Living Room — entry point

Read [README.md](README.md) for what this is, then [.ai/README.md](.ai/README.md) for
where project knowledge lives (the Fieldnotes skill in `.claude/skills/fieldnotes`
maintains it — use it when writing down a finding or a decision).

## Secrets

- `REACTOR_API_KEY` lives only in `.env` (git-ignored). Never put it in browser code:
  the Mac mints a JWT via `POST https://api.reactor.inc/tokens` with header
  `Reactor-API-Key` and hands the JWT to the client.

## Platform constraints (verified 2026-11-14 unless marked)

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
- Docs disagree on fps (18 in the track table, 24 in a `generation_started` example) —
  **unverified**, read it from a live run.
- Write motion as what the camera sees ("trunks slide from right to left"), not intent
  words. For lateral walls use tracking, never "pan" (pan = rotation, no parallax).

World Labs Marble API — `WORLDLABS_API_KEY` in `.env`, header `WLT-Api-Key`

- A finished `GET /operations/{id}` returns `response.assets.imagery.pano_url = null`;
  `GET /worlds/{world_id}` has the URL. `tools/marble_pano.py --world <id>` re-downloads
  without paying again. (2026-11-14)
- `marble-1.0-draft` text prompt costs 230 credits; its pano was 2304×1152 (6.4 px/deg).
  Pano generation is billed 80 credits on every model, so a pricier model may not give a
  better pano — unverified.

Quest 3 / WebXR

- WebXR exposes head + hands only; body is IK-inferred.
- Quest Link / Air Link do not run on macOS — there is no PC-tethered fallback on this
  team's hardware. Keep headset load to one decoded stream (see architecture).
