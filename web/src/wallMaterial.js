import * as THREE from 'three';
import { RIPPLE } from './config.js';

// One material per face. Samples its rectangle of the shared atlas and distorts it with
// up to RIPPLE.max expanding rings. The ripple is local and instant; the generated video
// carries the slower semantic consequence (see .ai/architecture.md, "One touch").

const vertexShader = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const fragmentShader = /* glsl */ `
  #define MAX_RIPPLES ${RIPPLE.max}
  uniform sampler2D uAtlas;
  uniform vec4 uRect;        // atlas offset.xy, scale.zw
  uniform vec2 uFlip;        // 1 = flip that axis
  uniform vec2 uSize;        // face size in metres (for round ripples)
  uniform float uTime;
  uniform vec4 uRipples[MAX_RIPPLES]; // u, v, startTime, strength (strength 0 = unused)
  uniform float uLifetime;
  uniform float uSpeed;
  uniform float uWavelength;
  uniform float uAmplitude;  // metres of image displacement at the crest
  uniform float uGlow;
  varying vec2 vUv;

  void main() {
    vec2 uv = vUv;
    vec2 offset = vec2(0.0);
    float glow = 0.0;

    for (int i = 0; i < MAX_RIPPLES; i++) {
      vec4 r = uRipples[i];
      float age = uTime - r.z;
      if (r.w <= 0.0 || age < 0.0 || age > uLifetime) continue;
      vec2 d = (uv - r.xy) * uSize;          // metres from the touch point
      float dist = length(d);
      float front = age * uSpeed;            // radius of the leading ring
      float behind = front - dist;           // >0 inside the expanding disc
      if (behind < 0.0) continue;
      float fade = (1.0 - age / uLifetime);
      float damp = exp(-behind * 3.0) * fade * fade * r.w;
      float wave = sin(behind / uWavelength * 6.2831853);
      vec2 dir = dist > 1e-4 ? d / dist : vec2(0.0);
      offset += dir * wave * damp * uAmplitude / uSize;
      glow += max(wave, 0.0) * damp;
    }

    vec2 local = clamp(uv + offset, 0.0, 1.0);
    local = mix(local, 1.0 - local, uFlip);
    vec3 col = texture2D(uAtlas, uRect.xy + local * uRect.zw).rgb;
    col += glow * uGlow;

    // Soft darkening toward the edges, where independently generated faces meet.
    vec2 e = min(vUv, 1.0 - vUv) * uSize;
    float edge = smoothstep(0.0, 0.12, min(e.x, e.y));
    col *= mix(0.55, 1.0, edge);

    gl_FragColor = vec4(col, 1.0);
    #include <colorspace_fragment>
  }
`;

export function createWallMaterial(atlasTexture, rect, face, sizeMetres) {
  const ripples = Array.from({ length: RIPPLE.max }, () => new THREE.Vector4(0, 0, 0, 0));
  const material = new THREE.ShaderMaterial({
    vertexShader,
    fragmentShader,
    uniforms: {
      uAtlas: { value: atlasTexture },
      uRect: { value: new THREE.Vector4(rect.x, rect.y, rect.w, rect.h) },
      uFlip: { value: new THREE.Vector2(face.flipU ? 1 : 0, face.flipV ? 1 : 0) },
      uSize: { value: new THREE.Vector2(sizeMetres.x, sizeMetres.y) },
      uTime: { value: 0 },
      uRipples: { value: ripples },
      uLifetime: { value: RIPPLE.lifetime },
      uSpeed: { value: RIPPLE.speed },
      uWavelength: { value: RIPPLE.wavelength },
      uAmplitude: { value: RIPPLE.amplitude },
      uGlow: { value: RIPPLE.glow },
    },
  });

  let next = 0;
  material.userData.addRipple = (u, v, time, strength = 1) => {
    ripples[next].set(u, v, time, strength);
    next = (next + 1) % RIPPLE.max;
  };
  return material;
}
