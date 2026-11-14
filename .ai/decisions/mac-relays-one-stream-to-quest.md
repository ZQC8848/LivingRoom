# The Mac holds the sessions and sends the headset one composited stream

**2026-11-14 ・ status: standing ・ scope: demo topology**

## What forced the choice

4–6 concurrent WebRTC streams on a Quest 3 browser may exceed its hardware decoder, and
the team has only a Mac, so Quest Link / Air Link (PC-only) is not available as a
fallback. The API key must also stay off the client.

## Decision

The Mac mints JWTs, holds every Orbis session, packs the walls into one atlas video and
relays it over LAN WebRTC. The headset decodes one stream and sends poses/touches back.

## Why not the alternatives

| Alternative | Its case | Why not |
|---|---|---|
| Quest opens every session directly | Lowest latency, no relay | 4–6 decodes + texture uploads in the browser; untested and the likeliest demo failure |
| PC + Quest Link | All work on a GPU | No Windows machine available |
| Native Unity app | More decode control | Reactor ships JS/Python SDKs only; re-implementing the session protocol is not a weekend task |

## What this rests on

| Assumption | Status | Evidence, or the check that would settle it |
|---|---|---|
| Relay adds only ~100–200 ms | unverified | Timestamp overlay on Mac vs headset |
| Venue Wi-Fi carries one 4K stream reliably | unverified | Bring a travel router; measure on site |

## Accepted costs

Extra hop of latency; dependence on LAN. Acceptable because world changes are already
seconds-scale and head rotation is rendered locally.

## What would reverse this

`getStats` on the Quest shows hardware decode of 4 streams with no dropped frames —
then connect directly and drop the relay.
