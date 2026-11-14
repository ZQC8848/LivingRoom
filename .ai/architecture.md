# Architecture — what happens to one frame and one touch

**Last verified: 2026-11-14 (design; nothing built yet)**

```
Quest 3 (WebXR page)
  ↑ head + hand poses, touch events      (WebSocket, tiny)
  ↓ one composited video stream          (LAN WebRTC)
Mac (relay + compositor, holds the key)
  · mints JWT, opens 4–6 Orbis sessions, staggered ~6 s apart (rate limit)
  · receives each wall's main_video track
  · packs walls into one atlas frame (e.g. 2×2 at 4K for four walls)
  · sends the atlas to the headset
Reactor cloud
  · one Orbis session per live face
```

## One frame

1. Each Orbis session streams its wall at the chosen delivery tier.
2. The Mac draws every wall into its atlas slot (floor/ceiling: centre 1:1 crop of the
   16:9 frame; ceiling mirrored horizontally).
3. The headset decodes one stream and maps atlas regions to the six room faces. Head
   rotation never waits on the network — it is local rendering of textured quads.

## One touch

1. Hand-to-plane distance on the headset detects contact; touch UV goes to a ripple
   uniform **immediately** (local shader distortion of the current video texture).
2. The same event goes to the Mac, which maps it to a coarse region (3×3 grid) and sends
   a single state-change `set_prompt` to that wall's session.
3. 3–6 s later the generated video carries the semantic consequence.

## Scene transition (no extra sessions)

1. New first-frame images uploaded ahead of time (`upload_file`).
2. Capture each wall's current frame as a still texture.
3. Per session: `reset` → `set_image` → `set_prompt` → `start` (session reused).
4. Show the still with a local transition effect while the new run warms up (~2 chunks),
   then crossfade each wall independently as its first new frame arrives.

## Open questions that change this design

- Can the Mac relay add < ~200 ms and hold up on venue Wi-Fi? (bring a router)
- Does the Quest browser decode the atlas in hardware (`getStats` → `decoderImplementation`)?
- Do 4–6 sessions *generating* at once all get GPUs?
