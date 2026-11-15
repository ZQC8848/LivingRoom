// Recorded playback for the public deployment (VITE_DEPLOY=1): the same interface as
// createLive() in live.js, but nothing is generated and nothing is billed. Every preset has a
// clip recorded from Orbis Dynamic (tools/orbis_test.py --mp4, ~28 s from the reference on),
// and the page plays it the way the live relay plays two sessions:
//
//   deck A  ████████ clip ████████▓▒░          the clip again, from the start
//   deck B            (idle)      ░▒▓████████ ...
//
// Near the end of a clip the same file starts on the other <video> deck and liveMain.js
// cross-fades to it -- the recorded equivalent of returning to the reference before the
// layout drifts. Pressing another preset starts that preset's clip on the other deck.
// No session, no token, no API route: a static host is enough.

export function createRecorded({ scene, videos, countFrames, onStatus, onFrames }) {
  const fade = scene.loop?.fade_seconds ?? 3;
  let wanted = false;
  let deck = -1; // the deck whose clip is on the sphere
  let token = 0; // the latest play() wins
  let loopTimer = null;
  let fadingUntil = 0;
  let current = null; // the preset that is (or should be) playing

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  async function play(ev, isLoop = false) {
    const mine = ++token;
    clearTimeout(loopTimer);
    if (!ev?.clip) return false;
    current = ev;
    if (!isLoop) onStatus?.('loading', ev.label);
    // The outgoing deck is still visible under a running cross-fade: let that finish first.
    const wait = fadingUntil - performance.now();
    if (wait > 0) await sleep(wait);
    if (mine !== token || !wanted) return false;

    const d = deck < 0 ? 0 : 1 - deck;
    const v = videos[d];
    v.srcObject = null;
    v.loop = false;
    v.src = ev.clip;
    countFrames(d);
    try {
      await v.play();
    } catch (e) {
      if (mine === token) onStatus?.('error', `cannot play ${ev.label} (${e?.name ?? e}); click the page once and press it again`);
      return false;
    }
    if (mine !== token || !wanted) {
      v.pause();
      return false;
    }
    const old = deck;
    deck = d;
    fadingUntil = performance.now() + (fade + 2.5) * 1000;
    onFrames?.({ label: ev.label }, 'recorded', d); // liveMain fades this deck in over the other one
    onStatus?.('playing', `${ev.label} · recorded with Orbis Dynamic`);
    if (old >= 0) {
      setTimeout(() => {
        if (deck !== old) {
          // Free the decoder. (Not onIdle(): liveMain clears srcObject there, which makes a
          // <video> with a src reload and, with autoplay, start its clip again.)
          videos[old].pause();
          videos[old].removeAttribute('src');
          videos[old].load();
        }
      }, (fade + 3) * 1000);
    }
    // Loop: start the same clip on the other deck shortly before this one runs out.
    const arm = () => {
      if (mine !== token) return;
      const lead = v.duration - v.currentTime - fade - 1;
      loopTimer = setTimeout(() => mine === token && wanted && play(ev, true), Math.max(2, lead) * 1000);
    };
    if (Number.isFinite(v.duration) && v.duration > 0) arm();
    else v.addEventListener('loadedmetadata', arm, { once: true });
    return true;
  }

  // A browser may refuse or abort play(): a tab opened in the background, or an autoplay
  // policy that wants a gesture first. Try again when the page becomes visible or is touched.
  const retry = () => wanted && deck < 0 && play(current ?? opening());
  document.addEventListener('visibilitychange', () => document.visibilityState === 'visible' && retry());
  window.addEventListener('pointerdown', retry);

  const opening = () => scene.events.find((e) => e.reference === scene.reference && e.clip) ?? scene.events.find((e) => e.clip);

  return {
    start() {
      wanted = true;
      play(opening());
    },
    async stop() {
      wanted = false;
      token++;
      clearTimeout(loopTimer);
      for (const v of videos) v.pause();
      deck = -1;
      onStatus?.('stopped');
    },
    get active() { return wanted; },
    get ready() { return wanted && deck >= 0; },
    get model() { return 'recorded'; },
    get relay() { return false; },
    get relayMode() { return 'recorded'; },
    async steer() { return false; },
    reanchor(event) {
      const ev = scene.events.find((e) => e.label === event.label) ?? event;
      return play(ev);
    },
  };
}
