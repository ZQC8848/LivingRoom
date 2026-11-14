import * as THREE from 'three';
import { REVEAL } from './config.js';

// Paired-video panorama sphere. Same skybox trick as panoMaterial.js (view translation dropped,
// lookup by direction), but with two 2:1 equirect layers: heaven everywhere, hell inside the
// spherical caps the viewer opens by pointing.
//
// The mask is a function of angular distance on the sphere, not of screen or UV distance:
//   ang  = acos(dot(dir, centre))            dir = this pixel's world direction, centre = the ray
//   mask = 1 - smoothstep(r - feather, r, ang)
// so a cap stays round at any latitude (a UV-space circle would pinch toward the poles) and
// both eyes see the identical mask. Up to REVEAL.maxSlots caps (one per controller/hand);
// the layers are blended with the max of the caps' masks.

const vertexShader = /* glsl */ `
  varying vec3 vDir;
  void main() {
    vDir = position;
    vec4 p = projectionMatrix * vec4(mat3(viewMatrix) * position, 1.0);
    gl_Position = p.xyww;
  }
`;

const fragmentShader = /* glsl */ `
  #define PI 3.14159265
  #define SLOTS ${REVEAL.maxSlots}
  uniform sampler2D uPoster;
  uniform sampler2D uHeaven;
  uniform sampler2D uHell;
  uniform float uVideoMix;      // 0 = poster on both layers, 1 = the two videos
  uniform float uYaw;           // radians added to the longitude (manifest front_yaw_deg)
  uniform float uEdgeCrop;
  uniform float uSeamBand;
  uniform vec4 uReveal[SLOTS];  // xyz = centre direction, w = current radius in radians (<= 0: closed)
  uniform float uFeather;       // radians
  uniform float uRim;
  varying vec3 vDir;

  vec3 layer(sampler2D vid, vec2 uv) {
    uv.x = uEdgeCrop + uv.x * (1.0 - 2.0 * uEdgeCrop);
    return mix(texture2D(uPoster, uv).rgb, texture2D(vid, uv).rgb, uVideoMix);
  }
  vec3 seamless(sampler2D vid, vec2 uv) {
    vec3 a = layer(vid, uv);
    if (uSeamBand <= 0.0) return a;
    float s = uv.x < 0.5 ? uv.x : uv.x - 1.0;
    if (abs(s) >= uSeamBand) return a;
    vec3 b = layer(vid, vec2(fract(-s + 1.0), uv.y));
    return mix(a, b, 0.5 * (1.0 - abs(s) / uSeamBand));
  }

  void main() {
    vec3 dir = normalize(vDir);
    float lon = atan(dir.x, -dir.z) + uYaw;
    float lat = asin(clamp(dir.y, -1.0, 1.0));
    vec2 uv = vec2(fract(0.5 + lon / (2.0 * PI)), 0.5 + lat / PI);

    float mask = 0.0;
    float rim = 0.0;
    for (int i = 0; i < SLOTS; i++) {
      vec4 r = uReveal[i];
      if (r.w <= 0.0) continue;
      float ang = acos(clamp(dot(dir, normalize(r.xyz)), -1.0, 1.0));
      float f = min(uFeather, r.w);
      mask = max(mask, 1.0 - smoothstep(r.w - f, r.w, ang));
      float d = (ang - r.w) / 0.035;
      rim = max(rim, exp(-d * d));
    }

    vec3 col = mix(seamless(uHeaven, uv), seamless(uHell, uv), mask);
    col += rim * uRim * uVideoMix;
    gl_FragColor = vec4(col, 1.0);
    #include <colorspace_fragment>
  }
`;

export function createRevealSphere({ poster, heaven, hell, yawDeg = 0, edgeCrop = 0, seamBand = 0, reveal = REVEAL }) {
  const slots = Array.from({ length: REVEAL.maxSlots }, () => new THREE.Vector4(0, 0, -1, 0));
  const material = new THREE.ShaderMaterial({
    vertexShader,
    fragmentShader,
    side: THREE.BackSide,
    depthWrite: false,
    uniforms: {
      uPoster: { value: poster },
      uHeaven: { value: heaven },
      uHell: { value: hell },
      uVideoMix: { value: 0 },
      uYaw: { value: THREE.MathUtils.degToRad(yawDeg) },
      uEdgeCrop: { value: edgeCrop },
      uSeamBand: { value: seamBand },
      uReveal: { value: slots },
      uFeather: { value: THREE.MathUtils.degToRad(reveal.featherDeg) },
      uRim: { value: reveal.rimGlow },
    },
  });
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(1, 96, 48), material);
  mesh.frustumCulled = false;
  mesh.renderOrder = -1;
  return { mesh, material, slots };
}

// Per-slot open/close animation. open(slot, dir) starts growing at dir; move() follows the
// pointer while held; close() shrinks it. update(dt) writes the radius into the uniform.
export function createRevealState(slots, reveal = REVEAL) {
  const rMax = THREE.MathUtils.degToRad(reveal.radiusDeg);
  const st = slots.map(() => ({ want: false, t: 0 })); // t: 0 closed .. 1 open
  const ease = (x) => x * x * (3 - 2 * x);
  return {
    open(i, dir) {
      st[i].want = true;
      slots[i].set(dir.x, dir.y, dir.z, slots[i].w);
    },
    move(i, dir) {
      if (st[i].want) slots[i].set(dir.x, dir.y, dir.z, slots[i].w);
    },
    close(i) {
      st[i].want = false;
    },
    toggle(i, dir) {
      if (st[i].want) st[i].want = false;
      else this.open(i, dir);
    },
    isOpen: (i) => st[i].want,
    anyOpen: () => st.some((s) => s.want || s.t > 0),
    update(dt) {
      st.forEach((s, i) => {
        const dur = s.want ? reveal.growSeconds : reveal.shrinkSeconds;
        s.t = THREE.MathUtils.clamp(s.t + (s.want ? dt : -dt) / dur, 0, 1);
        slots[i].w = ease(s.t) * rMax;
      });
    },
    radiiDeg: () => slots.map((s) => THREE.MathUtils.radToDeg(s.w)),
  };
}
