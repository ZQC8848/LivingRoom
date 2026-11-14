// Room geometry and how each face samples the shared atlas texture.
// Numbers here are the ones in README.md and .ai/decisions/box-room-not-sphere.md.

export const ROOM = {
  size: 4.8, // floor is size × size metres
  height: 2.7, // = size × 9/16, so every wall is exactly 16:9
};

// The Mac relay will send ONE video: a 3×2 grid of 16:9 cells, one cell per Orbis
// session. Until the relay exists, a canvas test pattern stands in with the same layout.
export const ATLAS = { cols: 3, rows: 2 };

const CROP_1x1 = 9 / 16; // fraction of a 16:9 cell's width kept for a square face

// cell: [col, row] with row 0 at the TOP of the atlas image.
// crop: fraction of the cell width kept, centred (floor/ceiling are square faces).
// flipU/flipV: orientation fixes so content reads as a real camera would have shot it.
//   Floor  = camera looking straight down, image top toward the front wall → no flip.
//   Ceiling = camera looking straight up, image top toward the front wall → both flips.
export const FACES = [
  { id: 'front', label: 'FRONT', cell: [0, 0], crop: 1, flipU: false, flipV: false },
  { id: 'right', label: 'RIGHT', cell: [1, 0], crop: 1, flipU: false, flipV: false },
  { id: 'back', label: 'BACK', cell: [2, 0], crop: 1, flipU: false, flipV: false },
  { id: 'left', label: 'LEFT', cell: [0, 1], crop: 1, flipU: false, flipV: false },
  { id: 'floor', label: 'FLOOR', cell: [1, 1], crop: CROP_1x1, flipU: false, flipV: false },
  { id: 'ceiling', label: 'CEILING', cell: [2, 1], crop: CROP_1x1, flipU: true, flipV: true },
];

// UV rectangle (offset.xy, scale.xy) of a face inside the atlas, in texture space
// (v = 0 at the bottom of the image).
export function atlasRect(face) {
  const [col, row] = face.cell;
  const cw = 1 / ATLAS.cols;
  const ch = 1 / ATLAS.rows;
  const w = cw * face.crop;
  const x = col * cw + (cw - w) / 2;
  const y = 1 - (row + 1) * ch;
  return { x, y, w, h: ch };
}

export const RIPPLE = {
  max: 8, // shader array size
  lifetime: 3.0, // seconds
  speed: 1.2, // m/s, ring expansion
  wavelength: 0.18, // metres
  amplitude: 0.05, // metres of image displacement at the crest
  glow: 0.35, // brightness added on crests
};

export const TOUCH = {
  contact: 0.015, // fingertip within this many metres of a face = touch
  release: 0.05, // must move this far away before the next touch on that face
};
