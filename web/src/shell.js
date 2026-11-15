import * as THREE from 'three';
import { VRButton } from 'three/addons/webxr/VRButton.js';

// One page, two experiences: the live hillside (liveMain.js) and the painted Garden of
// Consequences (garden/garden.js, the art-side work from contributions/bosch-art).
//
// They share ONE WebGLRenderer, ONE canvas and ONE WebXR session, so switching never leaves
// VR: a page navigation would end the immersive session and need "Enter VR" again. Each
// experience keeps its own THREE.Scene, camera, HUD and VR panel and registers here with
//   { scene, camera, frame(), activate(), deactivate(), ui }
// Only the active one gets frame() and is rendered; the other is fully idle (its
// deactivate() must stop streams, video decoding and sound). A switch fades to black, swaps,
// and fades back in -- the black sphere rides on the active camera, so it works in the headset.
//
// The XR controllers are singletons of the renderer: both experiences listen to them, so each
// handler must check shell.is('<id>') first, and activate() must put them into its own scene.

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.xr.enabled = true;
renderer.xr.setReferenceSpaceType('local');
renderer.xr.setFoveation(1);
renderer.domElement.style.touchAction = 'none';
document.body.appendChild(renderer.domElement);
document.body.appendChild(VRButton.createButton(renderer, { optionalFeatures: ['hand-tracking'] }));

const FADE_SECONDS = 0.6;
const experiences = new Map(); // id -> experience
const loaders = new Map(); // id -> () => Promise (registers the experience when it resolves)
let active = null;
let activeId = null;
let switching = false;

// Black sphere around the head: opacity 0 = invisible, 1 = everything hidden.
const fade = new THREE.Mesh(
  new THREE.SphereGeometry(0.3, 24, 16),
  new THREE.MeshBasicMaterial({ color: 0x000000, side: THREE.BackSide, transparent: true, opacity: 0, depthTest: false, depthWrite: false }),
);
fade.renderOrder = 1000;
fade.visible = false;
let fadeTarget = 0;
let fadeDone = null;
let lastTime = performance.now();

renderer.setAnimationLoop(() => {
  const now = performance.now();
  const dt = Math.min((now - lastTime) / 1000, 0.1);
  lastTime = now;
  const m = fade.material;
  if (m.opacity !== fadeTarget) {
    m.opacity = THREE.MathUtils.clamp(m.opacity + Math.sign(fadeTarget - m.opacity) * (dt / FADE_SECONDS), 0, 1);
    if (Math.abs(m.opacity - fadeTarget) < 1e-3) m.opacity = fadeTarget;
  }
  fade.visible = m.opacity > 0;
  if (m.opacity === fadeTarget && fadeDone) {
    const done = fadeDone;
    fadeDone = null;
    done();
  }
  if (!active) return;
  active.frame();
  renderer.render(active.scene, active.camera);
});
// Resolves when the fade has reached v. The loop does not run while the tab is hidden, so a
// timer lands the fade if it has not finished by itself (a switch must never hang).
const fadeTo = (v) => new Promise((resolve) => {
  fadeTarget = v;
  const timer = setTimeout(() => {
    fade.material.opacity = v;
    fade.visible = v > 0;
    fadeDone = null;
    resolve();
  }, FADE_SECONDS * 1000 + 400);
  fadeDone = () => {
    clearTimeout(timer);
    resolve();
  };
});

window.addEventListener('resize', () => {
  for (const e of experiences.values()) {
    e.camera.aspect = window.innerWidth / window.innerHeight;
    e.camera.updateProjectionMatrix();
  }
  renderer.setSize(window.innerWidth, window.innerHeight);
});

function show(id) {
  for (const [k, e] of experiences) if (e.ui) e.ui.hidden = k !== id;
  document.title = experiences.get(id)?.title ?? document.title;
}

export const shell = {
  renderer,
  get activeId() { return activeId; },
  is: (id) => activeId === id && !switching,
  // An experience is ready. The first one registered becomes the active one.
  register(id, experience) {
    experiences.set(id, experience);
    if (experience.ui) experience.ui.hidden = true;
    if (!active) {
      active = experience;
      activeId = id;
      experience.camera.add(fade);
      show(id);
      experience.activate?.();
    }
  },
  // An experience that is only loaded the first time it is switched to.
  lazy(id, load) {
    let pending = null;
    loaders.set(id, () => (pending ??= load().catch((e) => {
      pending = null; // let a later switch try again
      throw e;
    })));
  },
  // Load a lazy experience in the background (it registers but stays idle), so that the
  // first switch to it is as quick as the later ones.
  preload(id) {
    if (!experiences.has(id) && loaders.has(id)) loaders.get(id)().catch((e) => console.warn(`[shell] preload ${id}:`, e));
  },
  has: (id) => experiences.has(id) || loaders.has(id),
  async switchTo(id) {
    if (switching || id === activeId || !shell.has(id)) return false;
    switching = true;
    try {
      await fadeTo(1);
      const from = active;
      try {
        await from?.deactivate?.();
      } catch (e) {
        console.warn('[shell] deactivate failed:', e);
      }
      if (!experiences.has(id)) {
        try {
          await loaders.get(id)(); // registers itself; the screen stays black meanwhile
        } catch (e) {
          console.error(`[shell] could not load ${id}:`, e);
          from?.activate?.();
          await fadeTo(0);
          return false;
        }
      }
      const to = experiences.get(id);
      active = to;
      activeId = id;
      to.camera.add(fade);
      show(id);
      await to.activate?.();
      await fadeTo(0);
      return true;
    } finally {
      switching = false;
    }
  },
  // A button in an experience's HTML controls that switches to another one.
  switchButton(label, id) {
    const b = Object.assign(document.createElement('button'), { type: 'button', textContent: label, title: 'Switch experience without leaving VR' });
    b.addEventListener('click', () => shell.switchTo(id));
    return b;
  },
};

if (import.meta.env.DEV) window.__shell = shell;
