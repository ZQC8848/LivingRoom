import * as THREE from 'three';
import { VRButton } from 'three/addons/webxr/VRButton.js';
import { ROOM } from './config.js';
import { createAtlas } from './atlas.js';
import { createRoom } from './room.js';
import { createTouchInput } from './touch.js';

const EYE_HEIGHT = 1.6; // desktop preview only; in XR the headset supplies it

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.xr.enabled = true;
renderer.xr.setReferenceSpaceType('local-floor');
renderer.xr.setFoveation(1);
document.body.appendChild(renderer.domElement);
document.body.appendChild(
  VRButton.createButton(renderer, { optionalFeatures: ['local-floor', 'hand-tracking'] }),
);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x000000);

const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.05, 50);
camera.position.set(0, EYE_HEIGHT, 0);
scene.add(camera);

const atlas = createAtlas();
const room = createRoom(atlas);
scene.add(room.group);

const clock = new THREE.Clock();
const hud = document.getElementById('hud');
const touchLog = [];

const touch = createTouchInput({
  renderer,
  camera,
  room,
  onTouch(faceId, uv, source) {
    const face = room.faces.find((f) => f.id === faceId);
    face.material.userData.addRipple(uv.x, uv.y, clock.getElapsedTime());
    // Later: send to the Mac, which maps uv → 3×3 region → set_prompt on that wall.
    const entry = `${faceId} u=${uv.x.toFixed(2)} v=${uv.y.toFixed(2)} (${source})`;
    touchLog.unshift(entry);
    touchLog.length = Math.min(touchLog.length, 4);
    window.dispatchEvent(new CustomEvent('wall-touch', { detail: { faceId, u: uv.x, v: uv.y, source } }));
  },
});
for (const c of touch.controllers) scene.add(c);
for (const h of touch.hands) scene.add(h);

// Optional: ?video=<url> plays a 3×2 atlas video on the walls (stand-in for the relay).
const videoUrl = new URLSearchParams(location.search).get('video');
if (videoUrl) {
  const video = Object.assign(document.createElement('video'), {
    src: videoUrl, loop: true, muted: true, playsInline: true, crossOrigin: 'anonymous',
  });
  video.play().then(() => atlas.setVideo(video)).catch((e) => console.warn('video failed', e));
}

installDesktopLook(camera, renderer);
if (import.meta.env.DEV) window.__lr = { THREE, scene, camera, renderer, room, atlas }; // console debugging

renderer.setAnimationLoop(() => {
  const t = clock.getElapsedTime();
  atlas.update(t);
  for (const f of room.faces) f.material.uniforms.uTime.value = t;
  touch.update();
  hud.textContent =
    `Living Room — ${ROOM.size}×${ROOM.size}×${ROOM.height} m, walls 16:9\n` +
    `drag to look · click a wall to ripple · atlas: ${atlas.mode}\n` +
    touchLog.join('\n');
  renderer.render(scene, camera);
});

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

// Desktop preview: stand at the centre, drag to turn the head. A click without a drag
// is passed through to the touch handler.
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
    if (Math.hypot(dx, dy) > 5) r.domElement.dataset.dragged = '1'; // touch.js ignores this click
    yaw = down.yaw + dx * 0.004;
    pitch = THREE.MathUtils.clamp(down.pitch + dy * 0.004, -1.5, 1.5);
    cam.rotation.set(pitch, yaw, 0);
  });
}
