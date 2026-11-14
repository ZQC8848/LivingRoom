import * as THREE from 'three';

// A floating control panel for VR, where the HTML HUD cannot be seen.
// Drawn on a 2D canvas (status line + a grid of buttons) and shown on a plane in the world.
// Rays from controllers or hand pinches hit-test it by UV; a hit presses the button under it
// instead of making a ripple. Placed in front of the head when VR starts; grip re-centres it.

const W = 1024;
const H = 560;
const COLS = 3;
const PAD = 28;
const STATUS_H = 150;
const PANEL_W = 0.62; // metres
const PANEL_H = (PANEL_W * H) / W;
const COLORS = {
  bg: 'rgba(14, 14, 12, 0.82)',
  border: 'rgba(201, 185, 138, 0.55)',
  text: '#ece8dc',
  dim: '#a9a294',
  button: '#2a2924',
  hover: '#3d3b33',
  active: '#c9b98a',
  activeText: '#1a1812',
  disabled: '#1d1c19',
};

export function createVrPanel({ buttons, onPress }) {
  const canvas = Object.assign(document.createElement('canvas'), { width: W, height: H });
  const ctx = canvas.getContext('2d');
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const mesh = new THREE.Mesh(
    new THREE.PlaneGeometry(PANEL_W, PANEL_H),
    new THREE.MeshBasicMaterial({ map: texture, transparent: true, depthWrite: false }),
  );
  mesh.visible = false;
  mesh.renderOrder = 10;

  const rows = Math.ceil(buttons.length / COLS);
  const bw = (W - PAD * (COLS + 1)) / COLS;
  const bh = (H - STATUS_H - PAD * (rows + 1)) / rows;
  const rects = buttons.map((b, i) => ({
    ...b,
    x: PAD + (i % COLS) * (bw + PAD),
    y: STATUS_H + PAD + Math.floor(i / COLS) * (bh + PAD),
    w: bw,
    h: bh,
  }));

  const state = { status: '', detail: '', hover: -1, highlight: null, disabled: false, flash: -1 };

  function roundRect(x, y, w, h, r) {
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, r);
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    roundRect(2, 2, W - 4, H - 4, 28);
    ctx.fillStyle = COLORS.bg;
    ctx.fill();
    ctx.lineWidth = 3;
    ctx.strokeStyle = COLORS.border;
    ctx.stroke();

    ctx.textBaseline = 'middle';
    ctx.textAlign = 'left';
    ctx.fillStyle = COLORS.text;
    ctx.font = '600 40px system-ui, sans-serif';
    ctx.fillText(fit(state.status, W - 2 * PAD), PAD + 6, 58);
    ctx.fillStyle = COLORS.dim;
    ctx.font = '30px system-ui, sans-serif';
    ctx.fillText(fit(state.detail, W - 2 * PAD), PAD + 6, 112);

    rects.forEach((r, i) => {
      const on = state.highlight && (r.id === state.highlight || r.label === state.highlight);
      const off = state.disabled && r.id !== 'live';
      roundRect(r.x, r.y, r.w, r.h, 18);
      ctx.fillStyle = off ? COLORS.disabled : on || i === state.flash ? COLORS.active : i === state.hover ? COLORS.hover : COLORS.button;
      ctx.fill();
      ctx.lineWidth = 2;
      ctx.strokeStyle = i === state.hover ? COLORS.active : 'rgba(255,255,255,0.12)';
      ctx.stroke();
      ctx.textAlign = 'center';
      ctx.fillStyle = off ? '#5d5a52' : on || i === state.flash ? COLORS.activeText : COLORS.text;
      ctx.font = '600 38px system-ui, sans-serif';
      ctx.fillText(r.label, r.x + r.w / 2, r.y + r.h / 2);
    });
    texture.needsUpdate = true;
  }

  function fit(text, max) {
    let t = text || '';
    while (t.length > 3 && ctx.measureText(t).width > max) t = t.slice(0, -2);
    return t === (text || '') ? t : `${t.slice(0, -1)}…`;
  }

  // Ray -> index of the button under it, or -1 (hit but no button), or null (missed panel).
  const raycaster = new THREE.Raycaster();
  function hit(ray) {
    if (!mesh.visible) return null;
    raycaster.ray.copy(ray);
    const h = raycaster.intersectObject(mesh, false)[0];
    if (!h) return null;
    const px = h.uv.x * W;
    const py = (1 - h.uv.y) * H;
    return rects.findIndex((r) => px >= r.x && px <= r.x + r.w && py >= r.y && py <= r.y + r.h);
  }

  let flashTimer = null;
  return {
    mesh,
    set(update) {
      const changed = Object.entries(update).some(([k, v]) => state[k] !== v);
      Object.assign(state, update);
      if (changed) draw();
    },
    setButtonLabel(id, label) {
      const r = rects.find((x) => x.id === id);
      if (r && r.label !== label) {
        r.label = label;
        draw();
      }
    },
    // Returns true if the ray hit the panel (so the caller should not also ripple).
    select(ray) {
      const i = hit(ray);
      if (i === null) return false;
      if (i >= 0 && !(state.disabled && rects[i].id !== 'live')) {
        state.flash = i;
        draw();
        clearTimeout(flashTimer);
        flashTimer = setTimeout(() => { state.flash = -1; draw(); }, 180);
        onPress(rects[i].id);
      }
      return true;
    },
    hover(rays) {
      let idx = -1;
      for (const ray of rays) {
        const i = hit(ray);
        if (i !== null && i >= 0) idx = i;
      }
      if (idx !== state.hover) {
        state.hover = idx;
        draw();
      }
    },
    // Put the panel ~0.75 m in front of the head (yaw only), a little below eye level,
    // turned to face the viewer.
    placeInFront(head) {
      const pos = new THREE.Vector3().setFromMatrixPosition(head.matrixWorld);
      const fwd = new THREE.Vector3(0, 0, -1).transformDirection(head.matrixWorld);
      fwd.y = 0;
      if (fwd.lengthSq() < 1e-6) fwd.set(0, 0, -1);
      fwd.normalize();
      mesh.position.copy(pos).addScaledVector(fwd, 0.75).add(new THREE.Vector3(0, -0.28, 0));
      mesh.lookAt(pos.x, pos.y - 0.05, pos.z);
      mesh.visible = true;
    },
    draw,
  };
}
