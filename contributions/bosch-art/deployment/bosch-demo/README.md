# Living Room · The Garden of Consequences

Static deployment of the existing LivingRoom prototype, using the paired-video
reveal feature branch and the Bosch-inspired media release. See
`SOURCE_PROVENANCE.json` for the exact upstream source and media checksums.

Run `npm install`, then `npm run build`. The public output is `dist/`.
There are no model API calls or secrets in this deployment. Model-based live
sessions remain in the original repository and are not part of the public demo.

Drag to turn the view. Click to reveal or hide the other state. In WebXR, hold a
controller trigger or hand pinch to reveal, release to close. This release's
headset interaction still needs physical Quest verification; browser simulation
is recorded separately.

The two H.264 master videos are 2048×1024, 30 fps, 240 frames, 8 seconds.
For deployment they are vertically packed in one 2048×2048 H.264 High 5.1 file,
with one video element, one VideoTexture and one clock. Each sampled state remains
a complete 2:1 equirectangular frame. The angular reveal mask selects the second
state; there is no second clock to drift. Sky / floor transitions are already
composed, and the viewer does not move the generated camera.

The packed file (about 4.3 MB) downloads completely and is checked against its
manifest before playback starts from a local Blob URL. The poster remains visible
during loading. This makes exact seek and loop independent of the host's handling
of open-ended video Range requests. A new checksum uses a new cache key.

The custom shader decodes sRGB video samples into linear color exactly once.
Poster textures use their normal hardware color decode. Half-texel padding keeps
the two packed states from bleeding at the poles.

## Published experience r5

Reveal remains the default narrative. The persistent Mode menu adds Garden Day/Night, Aftermath Day/Night, Garden Seasons and Aftermath Seasons. Day/night changes take six seconds, in twelve-second loops; seasons take eight seconds. All modes retain the fixed source viewpoint and share one active video element and VideoTexture.

In VR the floating menu opens on entry. Point and pinch/trigger to choose; the lower-view MODES badge or controller grip reopens it. Menu selection consumes the gesture before Reveal. English captions and sound controls are available in-world.

Eight Lily stock-voice narration cues cover the introduction, reveal/return, four optional modes and research. The story attributes Margaret D. Carroll's time/transformation reading and distinguishes the contemporary recovery interpretation from Bosch's original. See public/guide/index.html and public/audio/transcript.en.html.

This public static deployment plays prepared hybrid loops. No model keys or realtime generation connection ship to the browser. Hardware Quest targeting and comfort still need the wearer's acceptance.

Live Lab r6: open /?experience=live. Stable Reveal and four time studies remain the default, with no broker/model requests. Live Lab requires a private operator code and a running loopback broker/temporary HTTPS tunnel. The broker lives outside the published checkout at tools/live/broker.mjs; keys and operator state remain in ignored local files. One owned Dynamic session per connection, max_sessions=1, max duration 180 seconds, heartbeat cleanup and explicit server-side Stop. Generated environmental video is masked over the approved static plate; weather quality is experimental. No automatic camera transforms. See public/guide/live.html. The realistic sheep study is a separate teammate application. Scenario changes use a mode switch; no religious bridge or authored transition is planned. About 80 percent of the narrative focus remains on the painted world.
