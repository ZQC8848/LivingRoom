import * as THREE from 'three';
import { ATLAS, FACES, atlasRect } from './config.js';

// The texture every face samples. Today: a canvas test pattern laid out exactly like the
// relay's atlas will be. Later: setVideo() with the relay's WebRTC stream.

const CELL_W = 640;
const CELL_H = 360;
const HUES = { front: 205, right: 160, back: 265, left: 25, floor: 190, ceiling: 45 };

export function createAtlas() {
  const canvas = document.createElement('canvas');
  canvas.width = CELL_W * ATLAS.cols;
  canvas.height = CELL_H * ATLAS.rows;
  const ctx = canvas.getContext('2d');

  const canvasTexture = new THREE.CanvasTexture(canvas);
  canvasTexture.colorSpace = THREE.SRGBColorSpace;

  const atlas = {
    texture: canvasTexture,
    mode: 'pattern',
    // Swap every face over to a <video> carrying the relay's atlas stream.
    setVideo(video) {
      const t = new THREE.VideoTexture(video);
      t.colorSpace = THREE.SRGBColorSpace;
      atlas.texture = t;
      atlas.mode = 'video';
      atlas.onChange?.(t);
    },
    // A still 3x2 atlas, e.g. the projected Marble reference images of a scene.
    setImage(url) {
      return new THREE.TextureLoader().loadAsync(url).then((t) => {
        t.colorSpace = THREE.SRGBColorSpace;
        t.anisotropy = 4;
        atlas.texture = t;
        atlas.mode = `image ${url}`;
        atlas.onChange?.(t);
      });
    },
    onChange: null,
    update(time) {
      if (atlas.mode === 'pattern') drawPattern(ctx, time, canvasTexture);
    },
  };
  return atlas;
}

let lastDraw = -1;
function drawPattern(ctx, time, texture) {
  if (time - lastDraw < 1 / 12) return; // ~12 fps: enough to see motion, cheap to upload
  lastDraw = time;

  for (const face of FACES) {
    const [col, row] = face.cell;
    const x0 = col * CELL_W;
    const y0 = row * CELL_H;
    const hue = HUES[face.id];

    ctx.fillStyle = `hsl(${hue} 45% 22%)`;
    ctx.fillRect(x0, y0, CELL_W, CELL_H);

    // 10 cm grid in face space would be too dense; draw a 12×(cell aspect) grid.
    ctx.strokeStyle = `hsl(${hue} 50% 40%)`;
    ctx.lineWidth = 1;
    for (let i = 1; i < 16; i++) line(ctx, x0 + (i * CELL_W) / 16, y0, x0 + (i * CELL_W) / 16, y0 + CELL_H);
    for (let i = 1; i < 9; i++) line(ctx, x0, y0 + (i * CELL_H) / 9, x0 + CELL_W, y0 + (i * CELL_H) / 9);

    // Part of the cell the face actually shows (floor/ceiling: centre square).
    const r = atlasRect(face);
    const kx = (r.x - col / ATLAS.cols) * ATLAS.cols * CELL_W;
    const kw = r.w * ATLAS.cols * CELL_W;
    if (face.crop < 1) {
      ctx.fillStyle = 'rgba(0,0,0,0.45)';
      ctx.fillRect(x0, y0, kx, CELL_H);
      ctx.fillRect(x0 + kx + kw, y0, CELL_W - kx - kw, CELL_H);
    }

    // Moving bar: shows the stream is live and which way "right" is on this face.
    const phase = (time * 0.25) % 1;
    ctx.fillStyle = `hsl(${hue} 80% 60%)`;
    ctx.fillRect(x0 + kx + phase * (kw - 24), y0 + CELL_H - 40, 24, 24);

    // Orientation marks: label reads upright, arrow points to image-top.
    const cx = x0 + kx + kw / 2;
    ctx.fillStyle = '#fff';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.font = 'bold 54px system-ui, sans-serif';
    ctx.fillText(face.label, cx, y0 + CELL_H / 2);
    ctx.font = '22px system-ui, sans-serif';
    ctx.fillText(face.crop < 1 ? '1:1 centre crop' : '16:9 native', cx, y0 + CELL_H / 2 + 46);
    ctx.fillText('▲ image top', cx, y0 + 26);
    ctx.textAlign = 'left';
    ctx.fillText('L', x0 + kx + 10, y0 + CELL_H / 2);
    ctx.textAlign = 'right';
    ctx.fillText('R', x0 + kx + kw - 10, y0 + CELL_H / 2);
  }
  texture.needsUpdate = true;
}

function line(ctx, x1, y1, x2, y2) {
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.stroke();
}
