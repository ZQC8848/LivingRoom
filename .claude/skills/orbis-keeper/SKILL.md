---
name: orbis-keeper
description: Hold the single Orbis Dynamic session for Living Room for a limited time (1 h per hold, extendable on request) so the web page and tests can attach to it back to back without losing the server to someone else. Use when the user asks to hold, keep, reserve, extend, check or release the Orbis / Dynamic session or "the line", or before a demo or live testing round.
---

# Orbis keeper

Orbis Dynamic has **one server for everyone on Reactor**: whoever holds a session blocks
every other user and team, and it bills **$1.254/min while held, idle or not**. The keeper
(`tools/keeper.py`) owns one Dynamic session for a bounded time; the web page attaches to
it instead of creating its own, so consecutive runs never release the server in between.

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
tools/.venv/bin/python tools/keeper.py status     # minutes left, cost so far, session id
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
- The page never ends a keeper session on errors; only `keeper.py release` or the timer does.

## When reporting

Always give: phase, minutes left, the time it will release, held minutes and cost so far.
Before the hold expires, if the user is still working, ask once whether to extend —
do not decide for them.

## If something looks wrong

- `status` warns "keeper process is gone but the session may still be open": run `release`;
  it falls back to `DELETE /sessions/{id}` with the API key.
- `start` says a keeper is already running: use `status` / `extend` / `release` on it.
- Port 5199 is the keeper's control API (localhost only).
