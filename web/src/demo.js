import * as THREE from 'three';
import { VRButton } from 'three/addons/webxr/VRButton.js';
import { DEMO, REVEAL } from './config.js';
import { createRevealSphere, createRevealState } from './revealMaterial.js';
import { directionToUv } from './pointer.js';

// Paired-video reveal demo: heaven and hell are two same-length 2:1 equirect videos on one
// head-locked sphere; pointing opens a spherical cap (angular radius, see revealMaterial.js) in
// which hell replaces heaven. No network calls besides the static files in
// scenes/<name>/media/, so a plain static host is enough.

export const assetUrl = (p) => new URL(import.meta.env.BASE_URL + p, location.href).href;

export async function startDemo(sceneName, manifest) {
  const params = new URLSearchParams(location.search);
  const base = `scenes/${sceneName}/media/`;
  // Paths live in manifest.media (strings); manifest.files carries sha256 etc. and is not read here.
  const strings = (o) => Object.fromEntries(Object.entries(o ?? {}).filter(([, v]) => typeof v === 'string'));
  const media = strings(manifest.media);
  const packedFile = media.packed || null; // single-decoder mode: paired.mp4, heaven on top, hell below
  if (packedFile && (media.packedLayout || 'heaven-top-hell-bottom') !== 'heaven-top-hell-bottom') throw new Error(`unsupported packedLayout ${media.packedLayout}`);
  const files = { heaven: 'heaven.mp4', hell: 'hell.mp4', poster: 'poster.jpg', hell_poster: 'hell-poster.jpg', ...media };
  if (media.hellPoster) files.hell_poster = media.hellPoster; // both spellings are accepted
  const reveal = { ...REVEAL, ...manifest.reveal };
  const proj = manifest.projection ?? {};
  const video = manifest.video ?? {};
  const fps = video.fps ?? manifest.media?.fps ?? manifest.fps ?? 30;
  const frameCount = video.frame_count ?? manifest.frames;
  const loop = manifest.media?.loop ?? true;
  const yawDeg = proj.front_yaw_deg ?? manifest.orientation?.front_longitude_degrees ?? 0;

  const ui = { hud: document.getElementById('hud'), status: document.getElementById('status') };
  for (const id of ['live', 'events', 'steer']) document.getElementById(id)?.closest('.row')?.remove();
  document.getElementById('live')?.remove();
  const log = { lines: [`${manifest.title ?? sceneName}`, 'loading…'], hint: 'drag to look · click to open hell · click again to close' };
  const draw = () => (ui.status.textContent = [...log.lines, params.has('debug') ? log.debug ?? '' : log.hint].filter(Boolean).join('\n'));
  draw();

  const renderer = new THREE.WebGLRenderer({ antialias: false });
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

  // Poster first: it is the whole picture until both videos have frames (and the fallback when
  // a video cannot play).
  const prep = (t) => {
    t.colorSpace = THREE.SRGBColorSpace;
    t.minFilter = THREE.LinearFilter;
    t.generateMipmaps = false; // no mipmaps: the u = 0/1 seam would bleed through them
    t.wrapS = THREE.RepeatWrapping; // the 2:1 panoramas already match at the back seam
    return t;
  };
  const loadPoster = (f) => new THREE.TextureLoader().loadAsync(assetUrl(base + f)).then(prep);
  const poster = await loadPoster(files.poster);
  const hellPoster = await loadPoster(files.hell_poster).catch(() => poster); // optional
  const makeVideo = (file) =>
    Object.assign(document.createElement('video'), {
      src: assetUrl(base + file),
      muted: true,
      loop,
      playsInline: true,
      preload: 'auto',
      crossOrigin: 'anonymous',
    });
  // Packed: ONE <video> and ONE VideoTexture; heaven and hell are aliases of the same objects,
  // so they share a clock and can never drift. Dual: two videos, kept in lockstep by resync().
  const heaven = makeVideo(packedFile || files.heaven);
  const hell = packedFile ? heaven : makeVideo(files.hell);
  for (const v of new Set([heaven, hell])) v.setAttribute('webkit-playsinline', '');
  const heavenTex = prep(new THREE.VideoTexture(heaven));
  const hellTex = packedFile ? heavenTex : prep(new THREE.VideoTexture(hell));
  const sphere = createRevealSphere({
    poster,
    hellPoster,
    heaven: heavenTex,
    hell: hellTex,
    packed: !!packedFile,
    videoHeight: video.height ? (packedFile ? video.height * 2 : video.height) : 1024,
    yawDeg,
    edgeCrop: proj.edge_crop ?? 0,
    seamBand: proj.seam_band ?? 0,
    reveal,
  });
  scene.add(sphere.mesh);
  const state = createRevealState(sphere.slots, reveal);

  // ---- video: start, validate, keep the pair in lockstep -------------------------------------
  const info = { problems: [], playing: false, driftFrames: 0, resyncs: 0, videoMode: packedFile ? 'packed' : 'dual', everPlayed: false, loadError: false };
  let startOverlay = null;
  // Pane = one 2:1 panorama: the whole frame (dual) or half of it (packed, 2048x2048 -> 2 x 2048x1024).
  const pane = () => ({ w: heaven.videoWidth, h: packedFile ? heaven.videoHeight / 2 : heaven.videoHeight });
  const check = () => {
    const p = [];
    if (heaven.videoWidth) {
      const { w, h } = pane();
      if (Math.abs(w / h - 2) > 0.01) p.push(`${packedFile ? 'pane' : 'video'} is ${w}x${h}, not 2:1 (file ${heaven.videoWidth}x${heaven.videoHeight})`);
      sphere.material.uniforms.uPadV.value = 0.5 / heaven.videoHeight;
      if (!packedFile && hell.videoWidth && (heaven.videoWidth !== hell.videoWidth || heaven.videoHeight !== hell.videoHeight)) p.push(`size mismatch ${heaven.videoWidth}x${heaven.videoHeight} vs ${hell.videoWidth}x${hell.videoHeight}`);
      // manifest.video.width/height may describe the file or one pane; either is accepted
      if (video.width && !((video.width === heaven.videoWidth && video.height === heaven.videoHeight) || (video.width === w && video.height === h))) p.push(`manifest says ${video.width}x${video.height}, video is ${heaven.videoWidth}x${heaven.videoHeight}`);
    }
    if (!packedFile && heaven.duration && hell.duration && Math.abs(heaven.duration - hell.duration) > 1.5 / fps) p.push(`duration mismatch ${heaven.duration.toFixed(3)}s vs ${hell.duration.toFixed(3)}s`);
    if (frameCount && heaven.duration && Math.abs(heaven.duration * fps - frameCount) > 1.5) p.push(`manifest says ${frameCount} frames, video has ~${Math.round(heaven.duration * fps)}`);
    info.problems = p;
    if (p.length) console.warn('[demo] media problems:', p);
  };
  heaven.addEventListener('loadedmetadata', check);
  if (!packedFile) hell.addEventListener('loadedmetadata', check);
  for (const v of new Set([heaven, hell])) v.addEventListener('error', () => {
    info.loadError = true;
    info.problems = [...info.problems, `cannot load ${packedFile ? 'packed' : v === heaven ? 'heaven' : 'hell'} video (${v.error?.message || v.error?.code})`];
  });

  async function startVideos() {
    try {
      await Promise.all([...new Set([heaven, hell])].map((v) => v.play()));
      startOverlay?.remove();
      startOverlay = null;
    } catch {
      if (!info.problems.some((q) => q.startsWith('cannot'))) showStartOverlay(); // autoplay blocked: needs one tap (not for a load error)
    }
  }
  function showStartOverlay() {
    if (startOverlay) return;
    startOverlay = Object.assign(document.createElement('button'), { textContent: 'Tap to start', type: 'button' });
    Object.assign(startOverlay.style, { position: 'fixed', inset: '0', margin: 'auto', width: '200px', height: '56px', zIndex: 5, fontSize: '18px' });
    startOverlay.addEventListener('click', startVideos);
    document.body.appendChild(startOverlay);
  }
  startVideos();
  // Dual mode only: a packed video has one clock, nothing to resync.
  if (!packedFile) setInterval(() => {
    if (heaven.paused || hell.paused || heaven.readyState < 2 || hell.readyState < 2) return;
    let d = hell.currentTime - heaven.currentTime;
    const dur = heaven.duration || 0;
    if (dur && Math.abs(d) > dur / 2) d += d > 0 ? -dur : dur; // one of them just wrapped
    info.driftFrames = d * fps;
    if (Math.abs(info.driftFrames) > DEMO.driftToleranceFrames) {
      hell.currentTime = heaven.currentTime;
      info.resyncs++;
    }
  }, DEMO.syncIntervalMs);
  document.addEventListener('visibilitychange', () => document.visibilityState === 'visible' && startVideos());
  renderer.xr.addEventListener('sessionstart', startVideos);

  // ---- pointing: one cap per controller / hand, plus the mouse --------------------------------
  const rayDir = (obj) => {
    obj.updateMatrixWorld(true);
    return new THREE.Vector3(0, 0, -1).transformDirection(obj.matrixWorld);
  };
  const controllers = [0, 1].map((i) => {
    const c = renderer.xr.getController(i);
    c.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3(0, 0, -5)]), new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.3 })));
    // select = trigger or a hand pinch. Held: the cap follows the ray. Released: it closes.
    c.addEventListener('selectstart', () => state.open(i, rayDir(c)));
    c.addEventListener('selectend', () => state.close(i));
    scene.add(c);
    return c;
  });
  const raycaster = new THREE.Raycaster();
  let lastPoint = null;
  renderer.domElement.addEventListener('click', (e) => {
    if (renderer.xr.isPresenting || renderer.domElement.dataset.dragged === '1') return;
    const r = renderer.domElement.getBoundingClientRect();
    raycaster.setFromCamera(new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1), camera);
    const dir = raycaster.ray.direction.clone();
    state.toggle(0, dir);
    lastPoint = directionToUv(dir);
    if (reveal.desktopHoldSeconds > 0 && state.isOpen(0)) setTimeout(() => state.close(0), reveal.desktopHoldSeconds * 1000);
  });
  installDesktopLook(camera, renderer);

  // Test / debug hook: open a cap by longitude/latitude (degrees; lon 0 = front, +90 = right).
  window.__reveal = {
    videoMode: info.videoMode,
    packedVideo: packedFile ? heaven : null,
    state, sphere, heaven, hell, info, renderer, camera,
    openAt(lonDeg, latDeg, slot = 0) {
      const lon = THREE.MathUtils.degToRad(lonDeg), lat = THREE.MathUtils.degToRad(latDeg);
      state.open(slot, new THREE.Vector3(Math.sin(lon) * Math.cos(lat), Math.sin(lat), -Math.cos(lon) * Math.cos(lat)));
    },
    close: (slot = 0) => state.close(slot),
    focus(name, slot = 0) {
      const f = manifest.focus?.[name];
      if (!f) return false;
      this.lookAt(f.longitude_degrees, f.latitude_degrees);
      this.openAt(f.longitude_degrees, f.latitude_degrees, slot);
      return true;
    },
    lookAt(lonDeg, latDeg) { camera.rotation.set(THREE.MathUtils.degToRad(latDeg), -THREE.MathUtils.degToRad(lonDeg), 0, 'YXZ'); },
  };

  // ---- loop -----------------------------------------------------------------------------------
  const clock = new THREE.Clock();
  let hintAt = performance.now();
  renderer.setAnimationLoop(() => {
    const dt = clock.getDelta();
    controllers.forEach((c, i) => state.isOpen(i) && renderer.xr.isPresenting && state.move(i, rayDir(c)));
    state.update(dt);
    const u = sphere.material.uniforms;
    // Latch: once both layers have shown real frames, a short seeking/buffering dip (readyState
    // < 2) keeps the last video texture; only a real load error drops back to the poster.
    const nowOk = !heaven.paused && !hell.paused && heaven.readyState >= 2 && hell.readyState >= 2;
    if (nowOk && !info.loadError) info.everPlayed = true;
    const ready = !info.loadError && (nowOk || info.everPlayed);
    info.playing = nowOk;
    u.uVideoMix.value = THREE.MathUtils.clamp(u.uVideoMix.value + (ready ? dt : -dt) / 0.8, 0, 1);
    const open = state.radiiDeg().map((r) => r.toFixed(0)).join('/');
    log.lines = [
      manifest.title ?? sceneName,
      info.problems.length ? `⚠ ${info.problems.join('; ')}` : ready ? `${info.videoMode} · ${heaven.videoWidth}x${heaven.videoHeight} · t=${heaven.currentTime.toFixed(2)}s` : 'loading video… (showing poster)',
    ];
    log.debug = `caps ${open}° · drift ${info.driftFrames.toFixed(2)} fr · resyncs ${info.resyncs}${lastPoint ? ` · last lon ${lastPoint.lonDeg.toFixed(0)}° lat ${lastPoint.latDeg.toFixed(0)}°` : ''}`;
    if (performance.now() - hintAt > 9000 && !params.has('debug') && !info.problems.length) ui.hud.style.display = 'none';
    draw();
    renderer.render(scene, camera);
  });
  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });
}

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
