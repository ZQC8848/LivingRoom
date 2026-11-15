# A2A between teammates' coding agents, over Tailscale

Each teammate runs `server.mjs` next to their own coding agent (Claude Code or Codex) and
publishes it on their tailnet. The other side talks to it with `send.mjs` (or any A2A client).
Both files have zero dependencies (Node >= 18) and can be copied anywhere.

```
your agent --send.mjs--> http://<their-machine>.<tailnet>.ts.net:41241/ --> server.mjs --> codex exec / claude -p
```

Traffic is encrypted by Tailscale (WireGuard); the port is never on the public internet.

## Warning: full permissions

The server runs the agent with every permission check off. Whoever has the token and can
reach the port can edit files, run commands, read `.env` and spend API credit on that
machine. So: share the token privately (not in a group chat or the repo), never use
`tailscale funnel`, and stop the server when you are not collaborating. Every request is
logged to `.a2a/log.jsonl`.

## Setup (each side)

1. Install Tailscale and sign in with your own account: https://tailscale.com/download
2. In the repo's `.env` (git-ignored):
   ```
   A2A_TOKEN=<openssl rand -hex 24>      # others use this to call YOU
   A2A_PEER_URL=http://<their-machine>.<their-tailnet>.ts.net:41241/
   A2A_PEER_TOKEN=<the token THEY generated>
   ```
3. Start the server (Codex side: `A2A_AGENT=codex`; set `A2A_WORKDIR` if the agent should
   work somewhere other than this repo):
   ```bash
   A2A_AGENT=codex node tools/a2a/server.mjs
   ```
   Windows (PowerShell): `$env:A2A_AGENT="codex"; node tools/a2a/server.mjs`. The files can
   live in any folder: put `.env` two levels above `server.mjs` (the "repo root") and set
   `A2A_WORKDIR` to the project Codex should work in. Allow Node through Windows Firewall
   if it asks.
4. Publish the port to the tailnet:
   ```bash
   tailscale serve --bg --tcp 41241 tcp://127.0.0.1:41241
   ```
5. Share the machine with the teammate: Tailscale admin console -> Machines -> `...` on
   this machine -> Share -> send them the invite link. They only see this one machine.
6. Send each other, privately: the machine's `*.ts.net` name (`tailscale status`) and `A2A_TOKEN`.

## Use

```bash
node tools/a2a/send.mjs --card                      # peer's agent card (no token needed)
node tools/a2a/send.mjs "Summarise what you changed in the web/ folder today"
node tools/a2a/send.mjs --context <id> "follow-up"  # same thread on their side
node tools/a2a/send.mjs --self "ping"               # test your own server
```

Tell your own agent it may use it, e.g. "ask the teammate's agent via tools/a2a/send.mjs".

## Joining the held Orbis Dynamic session (attach-only)

Dynamic has one server for all of Reactor. When Qin's keeper (`tools/keeper.py`) holds it,
a teammate's app can join that session instead of queueing. Same host, same bearer token:

```
GET  /keeper                -> { phase: "holding" | "none" | ..., model, session_ids, sessions, minutes_left, hold_until }
POST /keeper/token[?slot=N] -> { jwt, sessionId, slot, sessions, model, minutes_left, hold_until }   (409 if no hold / no such slot)
```

Dynamic now has two servers. When the keeper holds both (`sessions: 2`), the default slot
for you is **2**: a session of your own, separate from the picture on Qin's page (slot 1).
With a one-session hold there is only slot 1 and it is shared -- see the rules below.

```js
const HOST = 'http://qinchuans-macbook-pro.tail5a410a.ts.net:41241';
const r = await fetch(`${HOST}/keeper/token`, { method: 'POST', headers: { authorization: `Bearer ${A2A_PEER_TOKEN}` } });
if (r.ok) {
  const { jwt, sessionId, model } = await r.json();
  const reactor = new Reactor({ modelName: model });
  await reactor.connect(jwt, { sessionId });          // joins the held session
  await reactor.sendCommand('reset', {});             // then anchor your own scene:
  // set_resolution -> set_image -> set_prompt -> start
} else {
  // 409: nobody is holding -> open your own session as usual (may be "no available capacity")
}
```

Call this from your server or a Node script, not from browser code (the bearer token must
not ship to a browser; from an https page the http request is blocked anyway).

Rules:
- **One session = one picture.** Everyone attached sees the same stream, and anyone's
  `reset` / `set_image` / `set_prompt` changes it for all. Agree who is using it.
- **Only disconnect; never end the session** (no `DELETE /sessions`, no stop-session call).
  Disconnecting leaves the hold with the keeper.
- The JWT works only for this session and expires with the hold; it cannot create sessions.
- Starting, extending and releasing a hold is not exposed. Ask Qin.

## Stop

```bash
tailscale serve --tcp 41241 off     # unpublish
# Ctrl-C the server (or kill the node process)
```

## Protocol notes

A2A 0.3, JSON-RPC over HTTP POST `/`, `Authorization: Bearer <token>`:
`message/send` (honours `configuration.blocking: false`), `tasks/get`, `tasks/cancel`.
No streaming or push. One `contextId` = one agent session; runs are serialised, 30 min cap
(`A2A_RUN_TIMEOUT_MIN`). Agent card: `/.well-known/agent-card.json`.
