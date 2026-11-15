import * as THREE from 'three';
import { VRButton } from 'three/addons/webxr/VRButton.js';
import { SPHERE } from './config.js';
import { createPanoSphere, measurePoles } from './panoMaterial.js';
import { createPointerInput, directionToUv } from './pointer.js';
import { createLive } from './live.js';
import { createVrPanel } from './vrPanel.js';

const sceneName = new URLSearchParams(location.search).get('scene') || import.meta.env.VITE_DEFAULT_SCENE || 'hillside';

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.xr.enabled = true;
renderer.xr.setReferenceSpaceType('local');
renderer.xr.setFoveation(1);
document.body.appendChild(renderer.domElement);
document.body.appendChild(VRButton.createButton(renderer, { optionalFeatures: ['hand-tracking'] }));

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(80, window.innerWidth / window.innerHeight, 0.05, 100);
scene.add(camera);

const ui = {
  status: document.getElementById('status'),
  live: document.getElementById('live'),
  events: document.getElementById('events'),
  steer: document.getElementById('steer'),
  prompt: document.getElementById('prompt'),
};
const lines = { scene: '', live: 'still panorama', stream: '', last: '' };
let vrPanel = null; // the in-VR copy of the HUD, created once the scene's events are known
const render = () => {
  ui.status.textContent = [lines.scene, lines.live, lines.stream, lines.last].filter(Boolean).join('\n');
  vrPanel?.set({ status: lines.live.replace(/^live: /, '') || 'still panorama', detail: lines.last || lines.stream });
};

const config = await (await fetch(`/api/scene/${sceneName}`)).json();
// ?model=stable swaps in Orbis Stable (has spare capacity; its camera drifts) to test the pipeline.
if (new URLSearchParams(location.search).get('model') === 'stable') config.model = 'reactor/visko-orbis-stable';
lines.scene = `scene: ${config.name} · ${config.model}`;
render();

// Still panorama first: it is what the viewer sees until (and if) the live stream arrives.
const still = await new THREE.TextureLoader().loadAsync(config.still);
still.colorSpace = THREE.SRGBColorSpace;
still.minFilter = THREE.LinearFilter; // no mipmaps: the u = 0/1 seam would bleed through them
still.generateMipmaps = false;

// Two video "decks": normally only deck 0 plays. With the two-session relay (live.js) the
// next run warms up on the other deck and the sphere cross-fades live -> live between them.
const videos = [0, 1].map(() => Object.assign(document.createElement('video'), { muted: true, playsInline: true, autoplay: true }));
const liveTextures = videos.map((v) => {
  const t = new THREE.VideoTexture(v);
  t.colorSpace = THREE.SRGBColorSpace;
  t.minFilter = THREE.LinearFilter;
  t.generateMipmaps = false;
  return t;
});
let shown = 0; // the deck whose picture is (or is fading in as) the live picture
let video = videos[0];
let frozen = false; // uStill is a held frame of the outgoing picture (freezeLiveFrame)
let fadeSeconds = SPHERE.liveFadeSeconds;
const audio = Object.assign(document.createElement('audio'), { autoplay: true });

const pano = createPanoSphere(still, liveTextures[0]);
scene.add(pano.mesh);
measurePoles(still.image, pano.material.uniforms.uZenith.value, pano.material.uniforms.uNadir.value);

const clock = new THREE.Clock();
let liveTarget = 0;
let liveMix = 0; // linear 0..1; the shader gets it eased (see the animation loop)
let fadeWhenFrame = Infinity; // fade the new run in once `frames` reaches this (see onFrames)
let fadeDeadline = Infinity; // ...or at this clock time, if the video reports no frames
let stillFade = null; // offline still -> still crossfade in progress: the texture fading in
let frames = 0;
let fpsWindow = { t: 0, n: 0, fps: 0 };

// Counts decoded frames for the HUD. Fading the live picture in is driven by the model's
// own "frames emitted" signal (onFrames), not by video frames, so a re-anchor's stale
// frames never fade in early.
function countFrames(deck) {
  const v = videos[deck];
  if (!('requestVideoFrameCallback' in v) || v.dataset.counting) return;
  v.dataset.counting = '1'; // one callback chain per element, however often its stream changes
  const tick = () => {
    if (deck === shown) {
      frames++;
      fpsWindow.n++;
      if (frames >= fadeWhenFrame) startFadeIn();
    }
    v.requestVideoFrameCallback(tick);
  };
  v.requestVideoFrameCallback(tick);
}

// The still the sphere falls back to: the scene pano, an event's reference while offline,
// or a frozen copy of the live picture while a re-anchor warms up.
const loader = new THREE.TextureLoader();
const stillCache = new Map();
function prepStill(t) {
  t.colorSpace = THREE.SRGBColorSpace;
  t.minFilter = THREE.LinearFilter;
  t.generateMipmaps = false;
  return t;
}
async function stillFor(url) {
  if (!stillCache.has(url)) stillCache.set(url, loader.loadAsync(url).then(prepStill));
  return stillCache.get(url);
}
// The new run's picture is really on the video element: cross-fade from the held frame to it.
function startFadeIn() {
  fadeWhenFrame = Infinity;
  fadeDeadline = Infinity;
  liveTarget = 1;
}
// Offline: cross-fade from the current still to another one, borrowing the live slot.
function crossfadeStill(texture) {
  const u = pano.material.uniforms;
  if (liveTarget || liveMix > 0 || u.uStill.value === texture) {
    u.uStill.value = texture; // live picture is (partly) up: just swap what is underneath
    return;
  }
  u.uLive.value = texture;
  stillFade = texture;
}
function endStillFade() {
  if (!stillFade) return;
  const u = pano.material.uniforms;
  u.uStill.value = stillFade;
  u.uLive.value = liveTextures[shown];
  stillFade = null;
  liveMix = 0;
  u.uLiveMix.value = 0;
}
// Stop: the page must end on a real still. After a relay hand-over the layer underneath the
// live picture is the other video deck, and a held (keeper) session keeps streaming whatever
// its next user starts -- so put the current scene's still underneath before the live
// picture fades out; the animation loop detaches both decks once it has.
function goOffline() {
  fadeWhenFrame = Infinity;
  fadeDeadline = Infinity;
  frozen = false;
  stillFor(currentReference).then((tex) => {
    if (live.active || stillFade) return;
    pano.material.uniforms.uStill.value = tex;
    measurePoles(tex.image, pano.material.uniforms.uZenith.value, pano.material.uniforms.uNadir.value);
  });
}
function detachDecks() {
  for (const v of videos) v.srcObject = null;
  shown = 0;
  video = videos[0];
  pano.material.uniforms.uLive.value = liveTextures[0];
}
const freezeCanvas = document.createElement('canvas');
const freezeTexture = prepStill(new THREE.CanvasTexture(freezeCanvas));
function freezeLiveFrame() {
  endStillFade();
  fadeWhenFrame = Infinity;
  fadeDeadline = Infinity;
  if (video.readyState < 2) return false;
  freezeCanvas.width = video.videoWidth;
  freezeCanvas.height = video.videoHeight;
  freezeCanvas.getContext('2d').drawImage(video, 0, 0);
  freezeTexture.needsUpdate = true;
  pano.material.uniforms.uStill.value = freezeTexture;
  pano.material.uniforms.uLiveMix.value = 0; // identical picture, so no visible jump
  liveMix = 0;
  liveTarget = 0;
  frozen = true;
  return true;
}
function burst() {
  // A ring of ripples around the horizon marks the change while the new run warms up.
  const t = clock.getElapsedTime();
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * Math.PI * 2;
    pano.addRipple(new THREE.Vector3(Math.sin(a), 0.05, -Math.cos(a)), t + i * 0.12);
  }
}

const live = createLive({
  scene: config,
  onStatus(s, detail) {
    lines.live = `live: ${s}${detail ? ` — ${detail}` : ''}`;
    if (s === 'stopped' || s === 'busy' || s === 'error' || s === 'disconnected') liveTarget = 0;
    if (s === 'stopped') {
      goOffline();
      lines.stream = ''; // no stale "18 fps · mix 1.00" under "live: stopped"
    }
    setButtonsBusy(s === 'reanchoring');
    vrPanel?.set({ disabled: s === 'reanchoring' });
    vrPanel?.setButtonLabel('live', live?.active ? 'Stop' : 'Go live');
    ui.live.textContent = live?.active ? 'Stop' : 'Go live';
    render();
  },
  onVideo(stream, deck = 0) {
    videos[deck].srcObject = stream;
    videos[deck].play().catch(() => {});
    countFrames(deck);
  },
  // Relay: the line on this deck was handed over and reset; stop decoding its (black) stream.
  onIdle(deck) {
    if (deck !== shown) videos[deck].srcObject = null;
  },
  onFrames(anchor, model, deck = 0) {
    vrPanel?.set({ highlight: anchor.label === 'opening' ? 'Morning' : anchor.label });
    // The model has emitted frames of the new run (opening, re-anchor or line switch), but
    // they still have to travel and decode: until then the video element shows the old run's
    // last frame. Keep the held picture until a few new frames have really arrived, then
    // cross-fade -- never fade into the stale frame and pop.
    endStillFade();
    const u = pano.material.uniforms;
    fadeSeconds = SPHERE.liveFadeSeconds;
    if (deck !== shown) {
      // The new run is on the other deck. Unless a frozen frame is already underneath, put the
      // deck that is still playing underneath (same picture, so no jump) and fade the new one
      // in over it: live -> live, nothing ever stands still.
      if (!frozen && liveMix >= 1) {
        u.uStill.value = liveTextures[shown];
        fadeSeconds = config.loop?.fade_seconds ?? SPHERE.liveFadeSeconds;
      } else if (!frozen) freezeLiveFrame();
      u.uLive.value = liveTextures[deck];
      u.uLiveMix.value = 0;
      liveMix = 0;
      liveTarget = 0;
      shown = deck;
      video = videos[deck];
      frames = 0;
    }
    frozen = false;
    fadeWhenFrame = frames + SPHERE.liveFadeAfterFrames;
    fadeDeadline = clock.getElapsedTime() + 2.5;
    lines.last = `live picture: ${anchor.label} · ${model}`;
    render();
  },
  onFreeze() {
    freezeLiveFrame(); // hold the current picture while a re-anchor or line switch warms up
  },
  onLine(model) {
    // LingBot frames carry dark columns at their left/right edges; crop a little more there.
    pano.material.uniforms.uEdgeCrop.value = SPHERE.edgeCropByModel?.[model] ?? SPHERE.edgeCrop;
  },
  onAudio(stream) {
    audio.srcObject = stream;
    audio.play().catch(() => {});
  },
  onMessage(m) {
    if (m?.type === 'chunk_complete' && m.data?.delivered) lines.stream = `stream: ${m.data.delivered}, chunk ${m.data.chunk_index}`;
  },
});

function toggleLive() {
  if (live.active) live.stop();
  else live.start();
  ui.live.textContent = live.active ? 'Stop' : 'Go live';
  vrPanel?.setButtonLabel('live', live.active ? 'Stop' : 'Go live');
}
ui.live.addEventListener('click', toggleLive);
const eventButtons = [];
for (const ev of config.events) {
  const b = Object.assign(document.createElement('button'), {
    textContent: ev.label,
    type: 'button',
    title: ev.mode === 'reanchor' ? 're-anchor to a new reference (~6 s transition)' : 'steer the running picture',
  });
  b.addEventListener('click', () => runEvent(ev));
  ui.events.appendChild(b);
  eventButtons.push(b);
}
function runEvent(ev) {
  if (ev.mode === 'reanchor') vrPanel?.set({ highlight: ev.label });
  return ev.mode === 'reanchor' ? reanchor(ev) : steer(ev.prompt);
}
function setButtonsBusy(on) {
  for (const b of eventButtons) b.disabled = on;
}
let currentReference = config.reference; // what the picture is anchored to; custom prompts edit this
async function reanchor(ev) {
  if (ev.reference) currentReference = ev.reference;
  burst();
  if (live.ready) {
    lines.last = `re-anchoring to ${ev.label}…`;
    render();
    await live.reanchor(ev); // live.js freezes the frame (onFreeze) before resetting
  } else {
    // Offline or busy: show the event's own reference as the still; a later Go live starts there.
    live.reanchor(ev);
    const next = await stillFor(ev.reference);
    crossfadeStill(next);
    measurePoles(next.image, pano.material.uniforms.uZenith.value, pano.material.uniforms.uNadir.value);
    lines.last = `still: ${ev.label} (not live)`;
    render();
  }
}
ui.steer.addEventListener('submit', (e) => {
  e.preventDefault();
  const text = ui.prompt.value.trim();
  if (text) custom(text).then((ok) => ok && (ui.prompt.value = ''));
});
// A custom prompt is a scene change, and Orbis follows its reference image far more than its
// prompt: so an image model first edits the current reference into the new scene (~4 s, the
// dev server's /api/edit), then the page re-anchors on that picture like any event. The
// current scene keeps playing meanwhile; with the two-session relay there is no frozen frame.
let customBusy = false;
async function custom(text) {
  if (customBusy) return false;
  customBusy = true;
  ui.prompt.disabled = true;
  lines.last = `painting "${text}"…`;
  render();
  vrPanel?.set({ detail: `painting "${text}"…` });
  try {
    const r = await fetch('/api/edit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scene: config.name, base: currentReference, text }),
    });
    const ev = await r.json();
    if (!r.ok) throw new Error(ev.error || `edit ${r.status}`);
    console.info('[custom]', ev.cached ? `cached (${ev.cached})` : `${ev.seconds}s`, ev.reference, '| moving:', ev.moving, '|', ev.motion, ev.lint?.length ? `| lint: ${ev.lint.join('; ')}` : '');
    lines.last = `moving: ${ev.moving?.length ? ev.moving.join(', ') : 'nothing'}${ev.fallback ? ' (director failed, using your words)' : ''}`;
    render();
    await stillFor(ev.reference); // have the picture decoded before anything fades to it
    await reanchor(ev);
    return true;
  } catch (e) {
    lines.last = `could not paint "${text}": ${String(e?.message ?? e)}`;
    render();
    return false;
  } finally {
    customBusy = false;
    ui.prompt.disabled = false;
  }
}
async function steer(text) {
  const ok = await live.steer(text);
  lines.last = ok ? `sent: ${text}` : 'not live yet — prompt not sent';
  render();
  return ok;
}

// In VR the HTML HUD is invisible: the same controls float on a panel in front of the viewer.
vrPanel = createVrPanel({
  buttons: [{ id: 'live', label: 'Go live' }, ...config.events.map((e) => ({ id: e.label, label: e.label }))],
  onPress(id) {
    if (id === 'live') return toggleLive();
    const ev = config.events.find((e) => e.label === id);
    if (ev) runEvent(ev);
  },
});
scene.add(vrPanel.mesh);
vrPanel.draw();
render();
const panelOnDesktop = new URLSearchParams(location.search).has('panel'); // check the panel without a headset
let panelPlaced = false;
let xrFrames = 0;
renderer.xr.addEventListener('sessionstart', () => {
  panelPlaced = false;
  xrFrames = 0;
});
renderer.xr.addEventListener('sessionend', () => {
  vrPanel.mesh.visible = panelOnDesktop;
  if (panelOnDesktop) vrPanel.placeInFront(camera);
});
if (panelOnDesktop) {
  camera.updateMatrixWorld();
  vrPanel.placeInFront(camera);
}

const pointer = createPointerInput({
  renderer,
  camera,
  onSqueeze() {
    vrPanel.placeInFront(renderer.xr.isPresenting ? renderer.xr.getCamera() : camera); // grip: bring the panel back in front
  },
  onSelect(ray, source) {
    if (vrPanel.select(ray)) return; // pressed a panel button
    const dir = ray.direction.clone();
    pano.addRipple(dir, clock.getElapsedTime());
    const { lonDeg, latDeg } = directionToUv(dir);
    lines.last = `ripple at lon ${lonDeg.toFixed(0)}°, lat ${latDeg.toFixed(0)}° (${source})`;
    render();
    window.dispatchEvent(new CustomEvent('sky-point', { detail: { dir: dir.toArray(), lonDeg, latDeg, source } }));
  },
});
for (const c of pointer.controllers) scene.add(c);

installDesktopLook(camera, renderer);
if (import.meta.env.DEV) window.__lr = { THREE, scene, camera, renderer, pano, live, videos, get video() { return video; }, vrPanel };

let lastPoleProbe = 0;
let lastT = 0;
renderer.setAnimationLoop(() => {
  const t = clock.getElapsedTime();
  const dt = Math.min(t - lastT, 0.1); // (Clock.getDelta() after getElapsedTime() is always ~0)
  lastT = t;
  const u = pano.material.uniforms;
  u.uTime.value = t;
  if (t >= fadeDeadline) startFadeIn();
  // Time-based (the headset runs at 72-90 Hz, the desktop at 60) and eased at both ends.
  const target = stillFade ? 1 : liveTarget;
  liveMix = THREE.MathUtils.clamp(liveMix + Math.sign(target - liveMix) * (dt / (stillFade ? SPHERE.liveFadeSeconds : fadeSeconds)), 0, 1);
  u.uLiveMix.value = THREE.MathUtils.smoothstep(liveMix, 0, 1);
  if (stillFade && liveMix >= 1) endStillFade();
  if (!live.active && !stillFade && liveMix <= 0 && videos.some((v) => v.srcObject)) detachDecks();
  if (liveTarget && t - lastPoleProbe > 0.5 && video.readyState >= 2) {
    lastPoleProbe = t;
    measurePoles(video, u.uZenith.value, u.uNadir.value);
  }
  if (t - fpsWindow.t >= 2) {
    fpsWindow.fps = fpsWindow.n / (t - fpsWindow.t);
    fpsWindow = { t, n: 0, fps: fpsWindow.fps };
    if (liveTarget) {
      lines.stream = `${lines.stream.split(' · ')[0] || 'stream'} · ${fpsWindow.fps.toFixed(1)} fps · mix ${u.uLiveMix.value.toFixed(2)}`;
      render();
    }
  }
  void dt;
  if (renderer.xr.isPresenting) {
    // Place the panel once the headset pose has settled (a few frames into the session).
    if (!panelPlaced && ++xrFrames > 10) {
      vrPanel.placeInFront(renderer.xr.getCamera());
      panelPlaced = true;
    }
    vrPanel.hover(pointer.rays());
  }
  renderer.render(scene, camera);
});

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

// Desktop preview: drag to turn the head; a click without a drag points (ripple).
function installDesktopLook(cam, r) {
  let yaw = 0;
  let pitch = 0;
  let down = null;
  cam.rotation.order = 'YXZ';
  r.domElement.addEventListener('pointerdown', (e) => {
    down = { x: e.clientX, y: e.clientY, yaw, pitch };
    r.domElement.dataset.dragged = '';
  });
  window.addEventListener('pointerup', () => (down = null));
  window.addEventListener('pointermove', (e) => {
    if (!down || r.xr.isPresenting) return;
    const dx = e.clientX - down.x;
    const dy = e.clientY - down.y;
    if (Math.hypot(dx, dy) > 5) r.domElement.dataset.dragged = '1';
    yaw = down.yaw + dx * 0.004;
    pitch = THREE.MathUtils.clamp(down.pitch + dy * 0.004, -1.5, 1.5);
    cam.rotation.set(pitch, yaw, 0);
  });
}
