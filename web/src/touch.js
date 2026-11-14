import * as THREE from 'three';
import { TOUCH } from './config.js';
import { worldToFaceUv } from './room.js';

// Three ways to touch a face, all ending in onTouch(faceId, uv, source):
//   - hand tracking: index fingertip crosses into a face plane
//   - controllers:   trigger while the ray points at a face
//   - desktop:       mouse click (dev only)

const FINGERTIP = 'index-finger-tip';

export function createTouchInput({ renderer, camera, room, onTouch }) {
  const raycaster = new THREE.Raycaster();
  const meshes = room.faces.map((f) => f.mesh);
  const byMesh = new Map(room.faces.map((f) => [f.mesh, f]));
  const tip = new THREE.Vector3();

  const hands = [0, 1].map((i) => renderer.xr.getHand(i));
  const controllers = [0, 1].map((i) => {
    const c = renderer.xr.getController(i);
    c.add(makeRay());
    c.addEventListener('selectstart', () => {
      const hit = rayFromObject(c);
      if (hit) onTouch(hit.face.id, hit.uv, 'controller');
    });
    return c;
  });

  function rayFromObject(obj) {
    const origin = new THREE.Vector3().setFromMatrixPosition(obj.matrixWorld);
    const dir = new THREE.Vector3(0, 0, -1).transformDirection(obj.matrixWorld);
    raycaster.set(origin, dir);
    return firstHit();
  }

  function firstHit() {
    const hit = raycaster.intersectObjects(meshes, false)[0];
    if (!hit) return null;
    const face = byMesh.get(hit.object);
    const uv = worldToFaceUv(face, hit.point);
    return uv ? { face, uv } : null;
  }

  // Desktop click → ray from camera.
  renderer.domElement.addEventListener('click', (e) => {
    if (renderer.xr.isPresenting || renderer.domElement.dataset.dragged === '1') return;
    const r = renderer.domElement.getBoundingClientRect();
    const ndc = new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    raycaster.setFromCamera(ndc, camera);
    const hit = firstHit();
    if (hit) onTouch(hit.face.id, hit.uv, 'mouse');
  });

  // Per frame: fingertip contact with hysteresis so one press = one ripple.
  function update() {
    for (const hand of hands) {
      const joint = hand.joints?.[FINGERTIP];
      if (!joint || !joint.visible) continue;
      joint.getWorldPosition(tip);
      for (const face of room.faces) {
        const d = face.plane.distanceToPoint(tip); // >0 inside the room
        if (face.armed && d < TOUCH.contact) {
          const uv = worldToFaceUv(face, face.plane.projectPoint(tip, new THREE.Vector3()));
          if (uv) {
            face.armed = false;
            onTouch(face.id, uv, 'hand');
          }
        } else if (!face.armed && d > TOUCH.release) {
          face.armed = true;
        }
      }
    }
  }

  return { hands, controllers, update };
}

function makeRay() {
  const geo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 0, -5)]);
  return new THREE.Line(geo, new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.35 }));
}
