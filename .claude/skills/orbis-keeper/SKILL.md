---
name: orbis-keeper
description: Hold one or both Orbis Dynamic sessions for Living Room for a limited time (1 h per hold, extendable on request; --sessions 2 for both) so the web page and tests can attach to it back to back without losing the server to someone else. Use when the user asks to hold, keep, reserve, extend, check or release the Orbis / Dynamic session or "the line", or before a demo or live testing round.
---

# Orbis keeper

Orbis Dynamic has **two servers for everyone on Reactor** (since the evening of 2026-11-14,
as the user reported; it was one before, and our own measurements in CLAUDE.md are from the
one-server time). Each held session takes one of them away from every other user and team
and bills **$1.254/min while held, idle or not**. The keeper (`tools/keeper.py`) owns one or
both sessions for a bounded time; the web page attaches to a held session instead of
creating its own, so consecutive runs never release the server in between.

## One session or two

- **Default: one** (`start`). Leaves the other server to other teams. Use this unless the
  user asks for two.
- **Two** (`start --sessions 2`): slot 1 and slot 2 -- e.g. the headset page on slot 1 and a
  teammate on slot 2, or one live while the other pre-warms for a seamless switch. This takes
  **all** of Dynamic from everyone else and bills **$2.508/min (~$150 per hour)**. Only on the
  user's explicit request, and say both facts when you start it.
- Slot 1 is usable as soon as it is held; slot 2 joins when it frees up. If it does not
  within the wait (`--wait-minutes`, default 15), the keeper keeps slot 1 and stops trying
  (`detail: holding 1 of 2: no more capacity ...`). It never goes back to one session on its
  own, and a running one-session hold cannot be grown to two: `release`, then
  `start --sessions 2` (which gives the server up for a moment -- tell the user).
- Both slots share one deadline (set when slot 1 is ready). `extend` and `release` act on both.

## Rules (agreed with the user, 2026-11-14)

- A hold lasts **at most 1 hour** and is released **when the time runs out** (not when idle).
- **Extending is the user's explicit decision.** `extend` resets the deadline to 1 h from
  now; it never stacks further. Do not extend on your own initiative, on a schedule, or
  because a task is still running — ask, and say the minutes left and the cost so far.
- The session has a hard ceiling of 3 h from when it was created (a crashed keeper cannot
  hold longer). Past it, a new hold means a new session.
- Never set up anything that re-starts or extends holds automatically.

## Commands (from the repo root)

```bash
tools/.venv/bin/python tools/keeper.py start      # waits for capacity (default 15 min), then holds 1 h
tools/.venv/bin/python tools/keeper.py start --sessions 2   # hold both Dynamic sessions
tools/.venv/bin/python tools/keeper.py status     # minutes left, cost so far, session ids, sessions held / wanted
tools/.venv/bin/python tools/keeper.py extend     # deadline -> 1 h from now (user asked)
tools/.venv/bin/python tools/keeper.py release    # end the session now
```

`start` blocks while it waits for Dynamic (other users may hold it); run it in the
background if the wait could be long, and report when it reaches `holding`.
State and log: `.keeper/state.json`, `.keeper/keeper.log` (git-ignored).

## How clients use the hold

- **Web page** (`npm --prefix web run dev:local` or `dev`): **Go live** checks
  `/api/keeper`; if a hold is active it mints a token bound to that session
  (`/api/token?attach=1`) and adopts it — `reset`, the current anchor image and prompt,
  `start`. **Stop** closes only the page's connection; the keeper's session stays.
- Slots: `/api/token?attach=1&slot=2` binds to the second session (default slot 1). The page
  itself only uses slot 1 today.
- **Teammates** (attach-only, over the tailnet, `tools/a2a/README.md`): `POST /keeper/token`
  on the A2A server. With two sessions held they get slot 2 by default, a picture of their
  own; with one, they share slot 1 with the page. No start / extend / release is exposed.
- The page never ends a keeper session on errors; only `keeper.py release` or the timer does.

## When reporting

Always give: phase, how many sessions are held of how many wanted, minutes left, the time it
will release, held minutes, cost so far and the current rate per minute.
Before the hold expires, if the user is still working, ask once whether to extend —
do not decide for them.

## If something looks wrong

- `status` warns "keeper process is gone but the session may still be open": run `release`;
  it falls back to `DELETE /sessions/{id}` with the API key.
- `start` says a keeper is already running: use `status` / `extend` / `release` on it.
- Port 5199 is the keeper's control API (localhost only).
