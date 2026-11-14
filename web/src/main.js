import * as THREE from 'three';
import { VRButton } from 'three/addons/webxr/VRButton.js';
import { SPHERE } from './config.js';
import { createPanoSphere, measurePoles } from './panoMaterial.js';
import { createPointerInput, directionToUv } from './pointer.js';
import { createLive } from './live.js';

const sceneName = new URLSearchParams(location.search).get('scene') || 'hillside';

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
const render = () => (ui.status.textContent = [lines.scene, lines.live, lines.stream, lines.last].filter(Boolean).join('\n'));

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

const video = Object.assign(document.createElement('video'), { muted: true, playsInline: true, autoplay: true });
const liveTexture = new THREE.VideoTexture(video);
liveTexture.colorSpace = THREE.SRGBColorSpace;
liveTexture.minFilter = THREE.LinearFilter;
liveTexture.generateMipmaps = false;
const audio = Object.assign(document.createElement('audio'), { autoplay: true });

const pano = createPanoSphere(still, liveTexture);
scene.add(pano.mesh);
measurePoles(still.image, pano.material.uniforms.uZenith.value, pano.material.uniforms.uNadir.value);

const clock = new THREE.Clock();
let liveTarget = 0;
let frames = 0;
let fpsWindow = { t: 0, n: 0, fps: 0 };

// Counts decoded frames for the HUD. Fading the live picture in is driven by the model's
// own "frames emitted" signal (onFrames), not by video frames, so a re-anchor's stale
// frames never fade in early.
function countFrames() {
  if (!('requestVideoFrameCallback' in video)) return;
  const tick = () => {
    frames++;
    fpsWindow.n++;
    video.requestVideoFrameCallback(tick);
  };
  video.requestVideoFrameCallback(tick);
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
const freezeCanvas = document.createElement('canvas');
const freezeTexture = prepStill(new THREE.CanvasTexture(freezeCanvas));
function freezeLiveFrame() {
  if (video.readyState < 2) return false;
  freezeCanvas.width = video.videoWidth;
  freezeCanvas.height = video.videoHeight;
  freezeCanvas.getContext('2d').drawImage(video, 0, 0);
  freezeTexture.needsUpdate = true;
  pano.material.uniforms.uStill.value = freezeTexture;
  pano.material.uniforms.uLiveMix.value = 0; // identical picture, so no visible jump
  liveTarget = 0;
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
    setButtonsBusy(s === 'reanchoring');
    ui.live.textContent = live?.active ? 'Stop' : 'Go live';
    render();
  },
  onVideo(stream) {
    video.srcObject = stream;
    video.play().catch(() => {});
    countFrames();
  },
  onFrames(anchor, model) {
    liveTarget = 1; // the new run (opening, re-anchor or line switch) has picture again: fade in
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

ui.live.addEventListener('click', () => {
  if (live.active) live.stop();
  else live.start();
  ui.live.textContent = live.active ? 'Stop' : 'Go live';
});
const eventButtons = [];
for (const ev of config.events) {
  const b = Object.assign(document.createElement('button'), {
    textContent: ev.label,
    type: 'button',
    title: ev.mode === 'reanchor' ? 're-anchor to a new reference (~6 s transition)' : 'steer the running picture',
  });
  b.addEventListener('click', () => (ev.mode === 'reanchor' ? reanchor(ev) : steer(ev.prompt)));
  ui.events.appendChild(b);
  eventButtons.push(b);
}
function setButtonsBusy(on) {
  for (const b of eventButtons) b.disabled = on;
}
async function reanchor(ev) {
  burst();
  if (live.ready) {
    lines.last = `re-anchoring to ${ev.label}…`;
    render();
    await live.reanchor(ev); // live.js freezes the frame (onFreeze) before resetting
  } else {
    // Offline or busy: show the event's own reference as the still; a later Go live starts there.
    live.reanchor(ev);
    pano.material.uniforms.uStill.value = await stillFor(ev.reference);
    measurePoles(pano.material.uniforms.uStill.value.image, pano.material.uniforms.uZenith.value, pano.material.uniforms.uNadir.value);
    lines.last = `still: ${ev.label} (not live)`;
    render();
  }
}
ui.steer.addEventListener('submit', (e) => {
  e.preventDefault();
  const text = ui.prompt.value.trim();
  if (text) steer(text).then((ok) => ok && (ui.prompt.value = ''));
});
async function steer(text) {
  const ok = await live.steer(text);
  lines.last = ok ? `sent: ${text}` : 'not live yet — prompt not sent';
  render();
  return ok;
}

const pointer = createPointerInput({
  renderer,
  camera,
  onPoint(dir, source) {
    pano.addRipple(dir, clock.getElapsedTime());
    const { lonDeg, latDeg } = directionToUv(dir);
    lines.last = `ripple at lon ${lonDeg.toFixed(0)}°, lat ${latDeg.toFixed(0)}° (${source})`;
    render();
    window.dispatchEvent(new CustomEvent('sky-point', { detail: { dir: dir.toArray(), lonDeg, latDeg, source } }));
  },
});
for (const c of pointer.controllers) scene.add(c);

installDesktopLook(camera, renderer);
if (import.meta.env.DEV) window.__lr = { THREE, scene, camera, renderer, pano, live, video };

let lastPoleProbe = 0;
renderer.setAnimationLoop(() => {
  const t = clock.getElapsedTime();
  const dt = clock.getDelta();
  const u = pano.material.uniforms;
  u.uTime.value = t;
  const step = 1 / (SPHERE.liveFadeSeconds * 60);
  u.uLiveMix.value = THREE.MathUtils.clamp(u.uLiveMix.value + Math.sign(liveTarget - u.uLiveMix.value) * step, 0, 1);
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
