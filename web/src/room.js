import * as THREE from 'three';
import { ROOM, FACES, SEAMS, atlasRect } from './config.js';
import { createWallMaterial, texelOf } from './wallMaterial.js';

// Six inward-facing planes around the origin. The player starts at the origin
// (local-floor reference space), facing -Z = the front wall.
//
// Each plane's local +X is the viewer's right and local +Y is image-top, so the atlas
// cell maps without per-face UV hacks (except the ceiling flip set in config.js).

const S = ROOM.size;
const H = ROOM.height;
const HALF = S / 2;

const PLACEMENT = {
  front: { size: [S, H], pos: [0, H / 2, -HALF], rot: [0, 0, 0] },
  back: { size: [S, H], pos: [0, H / 2, HALF], rot: [0, Math.PI, 0] },
  left: { size: [S, H], pos: [-HALF, H / 2, 0], rot: [0, Math.PI / 2, 0] },
  right: { size: [S, H], pos: [HALF, H / 2, 0], rot: [0, -Math.PI / 2, 0] },
  floor: { size: [S, S], pos: [0, 0, 0], rot: [-Math.PI / 2, 0, 0] },
  ceiling: { size: [S, S], pos: [0, H, 0], rot: [Math.PI / 2, 0, 0] },
};

export function createRoom(atlas) {
  const group = new THREE.Group();
  const faces = [];

  for (const face of FACES) {
    const p = PLACEMENT[face.id];
    // Faces meet edge to edge. A hair of overlap (behind the neighbouring face, so never
    // visible) stops the black background showing through rasterisation cracks.
    const geometry = new THREE.PlaneGeometry(p.size[0] + SEAMS.overlap, p.size[1] + SEAMS.overlap);
    const material = createWallMaterial(
      atlas.texture,
      atlasRect(face),
      face,
      new THREE.Vector2(p.size[0], p.size[1]),
    );
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(...p.pos);
    mesh.rotation.set(...p.rot);
    mesh.name = face.id;
    mesh.updateMatrixWorld(true);
    group.add(mesh);

    // Plane in world space, normal pointing into the room — used for fingertip contact.
    const normal = new THREE.Vector3(0, 0, 1).applyQuaternion(mesh.quaternion);
    faces.push({
      id: face.id,
      mesh,
      material,
      size: p.size,
      normal,
      plane: new THREE.Plane().setFromNormalAndCoplanarPoint(normal, mesh.position.clone()),
      armed: true,
    });
  }

  if (SEAMS.trim) group.add(createTrim());

  atlas.onChange = (texture) => {
    for (const f of faces) {
      f.material.uniforms.uAtlas.value = texture;
      f.material.uniforms.uTexel.value = texelOf(texture);
    }
  };

  return { group, faces };
}

// World point on a face → its UV (0..1), or null if outside the face.
export function worldToFaceUv(face, point) {
  const local = face.mesh.worldToLocal(point.clone());
  const u = local.x / face.size[0] + 0.5;
  const v = local.y / face.size[1] + 0.5;
  return u >= 0 && u <= 1 && v >= 0 && v <= 1 ? new THREE.Vector2(u, v) : null;
}

// Thin bars along all 12 edges: the seams between independently generated faces are
// made visible on purpose instead of pretending they line up.
function createTrim() {
  const t = 0.05;
  const mat = new THREE.MeshBasicMaterial({ color: 0x3a3328 });
  const g = new THREE.Group();
  const bar = (sx, sy, sz, x, y, z) => {
    const m = new THREE.Mesh(new THREE.BoxGeometry(sx, sy, sz), mat);
    m.position.set(x, y, z);
    g.add(m);
  };
  for (const y of [0, H]) {
    for (const z of [-HALF, HALF]) bar(S, t, t, 0, y, z);
    for (const x of [-HALF, HALF]) bar(t, t, S, x, y, 0);
  }
  for (const x of [-HALF, HALF]) for (const z of [-HALF, HALF]) bar(t, H, t, x, H / 2, z);
  return g;
}
