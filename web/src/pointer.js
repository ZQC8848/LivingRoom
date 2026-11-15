import * as THREE from 'three';

// The sphere sits at infinity, so it cannot be touched. Interaction is by pointing:
//   - XR: controller trigger, or hand-tracking pinch (Quest reports it as select on the
//     hand's target-ray space), along wherever the ray points
//   - desktop: click (a drag turns the view instead; see main.js)
// Every gesture ends in onSelect(ray, source) with a world-space THREE.Ray; the caller decides
// whether it pressed the VR panel or points at the sky. Grip calls onSqueeze (re-centre panel).

export function createPointerInput({ renderer, camera, onSelect, onSqueeze }) {
  const controllers = [0, 1].map((i) => {
    const c = renderer.xr.getController(i);
    if (!c.userData.ray) { // one ray line per controller, however many experiences use it
      c.userData.ray = makeRay();
      c.add(c.userData.ray);
    }
    c.addEventListener('selectstart', () => onSelect(rayOf(c), 'xr'));
    c.addEventListener('squeezestart', () => onSqueeze?.());
    c.addEventListener('connected', (e) => (c.userData.inputSource = e.data));
    c.addEventListener('disconnected', () => (c.userData.inputSource = null));
    return c;
  });

  const raycaster = new THREE.Raycaster();
  renderer.domElement.addEventListener('click', (e) => {
    if (renderer.xr.isPresenting || renderer.domElement.dataset.dragged === '1') return;
    const r = renderer.domElement.getBoundingClientRect();
    const ndc = new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    raycaster.setFromCamera(ndc, camera);
    onSelect(raycaster.ray.clone(), 'mouse');
  });

  return {
    controllers,
    // Current rays of the connected controllers / hands, for hover highlighting.
    rays() {
      return controllers.filter((c) => c.userData.inputSource).map(rayOf);
    },
  };
}

function rayOf(obj) {
  const origin = new THREE.Vector3().setFromMatrixPosition(obj.matrixWorld);
  const dir = new THREE.Vector3(0, 0, -1).transformDirection(obj.matrixWorld);
  return new THREE.Ray(origin, dir);
}

// Direction -> panorama frame coordinates (same convention as panoMaterial.js).
export function directionToUv(dir) {
  const lon = Math.atan2(dir.x, -dir.z);
  const lat = Math.asin(THREE.MathUtils.clamp(dir.y, -1, 1));
  return { u: 0.5 + lon / (2 * Math.PI), v: 0.5 + lat / Math.PI, lonDeg: THREE.MathUtils.radToDeg(lon), latDeg: THREE.MathUtils.radToDeg(lat) };
}

function makeRay() {
  const geo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 0, -5)]);
  return new THREE.Line(geo, new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.35 }));
}
