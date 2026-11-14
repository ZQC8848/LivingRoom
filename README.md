# Living Room

A VR room where every wall is alive. The player stands inside a box whose walls are
real-time AI video streams, touches a wall to make it ripple, and speaks or gestures to
change the world outside.

Built for the **Visko · Living Worlds** track (Orbis real-time video, Reactor platform).
Demo: Sunday, 2026-11-15.

## The room

| Face | Size | Aspect | Content | Source |
|---|---|---|---|---|
| Front / back / left / right walls | 4.8 m × 2.7 m | 16:9, native, no crop | The world seen from that side | 1 Orbis session each, first frame cut from one Marble panorama at yaw 0 / 180 / 270 / 90 |
| Floor | 4.8 m × 4.8 m | 1:1 | Overhead water / ground, slow in-place motion only | Orbis, 16:9 centre-cropped to 1:1 — or static |
| Ceiling | 4.8 m × 4.8 m | 1:1 | Sky looking up, mirrored horizontally | Orbis, centre-cropped — or static |

The player stands at the centre of the floor, eye height 1.6 m, 2.4 m from every wall.
From the centre each wall spans 90° horizontally and about 59° vertically, which is the
view of an ordinary perspective camera — the format Orbis was trained on.

## How it works (short)

- **Mac** mints Reactor JWTs (the API key never reaches the browser), holds the Orbis
  sessions, composites the walls and relays one video stream to the headset.
- **Quest 3** (WebXR) renders the room, runs the ripple shader locally, and sends head
  and hand poses back to the Mac.
- Interaction has three time scales: shader ripple (ms), `set_prompt` world change
  (3–6 s), and freeze-frame re-anchor / scene transition (~5 s).

Details: [.ai/architecture.md](.ai/architecture.md). Why it is built this way:
[.ai/decisions/](.ai/decisions/). Current state: [.ai/handoff.md](.ai/handoff.md).

## Setup

```bash
cp .env.example .env   # then put the Reactor key in it — never commit it
```
