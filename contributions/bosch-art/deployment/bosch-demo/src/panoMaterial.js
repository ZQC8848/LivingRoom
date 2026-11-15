import * as THREE from 'three';
import { RIPPLE, SPHERE } from './config.js';

// Head-locked panorama sphere. The vertex shader drops the view translation (skybox trick),
// so the picture sits at infinity: walking or leaning never distorts it, and each eye sees the
// same direction -> same pixel. The fragment shader looks the frame up by direction, so the
// 16:9 Orbis frame is stretched back to 360 x 180 degrees here and nowhere else.
//
// Direction -> frame: lon = atan(x, -z) (0 = front = -Z, +90 = right), lat = asin(y).
// u = 0.5 + lon / 2pi, v = 0.5 + lat / pi. Matches tools/pano_reference.py (front at centre).

const vertexShader = /* glsl */ `
  varying vec3 vDir;
  void main() {
    vDir = position;
    vec4 p = projectionMatrix * vec4(mat3(viewMatrix) * position, 1.0);
    gl_Position = p.xyww; // depth at the far plane: always behind anything else in the scene
  }
`;

const fragmentShader = /* glsl */ `
  #define PI 3.14159265
  #define MAX_RIPPLES ${RIPPLE.max}
  uniform sampler2D uStill;
  uniform sampler2D uLive;
  uniform float uLiveMix;          // 0 = still pano, 1 = live stream
  uniform vec3 uZenith;            // pole colours, measured from the current picture in JS
  uniform vec3 uNadir;
  uniform float uSeamBand;
  uniform float uEdgeCrop;
  uniform vec2 uPoleFade;          // radians
  uniform float uTime;
  uniform vec4 uRipples[MAX_RIPPLES]; // centre direction xyz, start time (w < 0 = unused)
  uniform float uRippleLife;
  uniform float uRippleSpeed;
  uniform float uRippleWave;
  uniform float uRippleAmp;
  uniform float uRippleGlow;
  varying vec3 vDir;

  vec3 frame(vec2 uv) {
    uv.x = uEdgeCrop + uv.x * (1.0 - 2.0 * uEdgeCrop); // skip the outermost columns of the frame
    return mix(texture2D(uStill, uv).rgb, texture2D(uLive, uv).rgb, uLiveMix);
  }

  // Cross-blend the two edges of the frame: at the seam both sides weigh 50/50, so the
  // colour is continuous across it; the blend fades out over uSeamBand on either side.
  vec3 seamless(vec2 uv) {
    float s = uv.x < 0.5 ? uv.x : uv.x - 1.0;      // signed distance to the seam (u = 0 / 1)
    vec3 a = frame(uv);
    if (abs(s) >= uSeamBand) return a;
    vec3 b = frame(vec2(fract(-s + 1.0), uv.y));   // mirror point on the other side
    float w = 0.5 * (1.0 - abs(s) / uSeamBand);
    return mix(a, b, w);
  }

  void main() {
    vec3 dir = normalize(vDir);
    float glow = 0.0;

    for (int i = 0; i < MAX_RIPPLES; i++) {
      vec4 r = uRipples[i];
      float age = uTime - r.w;
      if (r.w < 0.0 || age < 0.0 || age > uRippleLife) continue;
      vec3 c = normalize(r.xyz);
      float ang = acos(clamp(dot(dir, c), -1.0, 1.0));
      float behind = age * uRippleSpeed - ang;       // > 0 inside the expanding ring
      if (behind < 0.0) continue;
      float fade = 1.0 - age / uRippleLife;
      float damp = exp(-behind * 18.0) * fade * fade;
      float wave = sin(behind / uRippleWave * 2.0 * PI);
      vec3 toward = c - dir * dot(dir, c);           // tangent toward the ripple centre
      float tl = length(toward);
      if (tl > 1e-5) dir = normalize(dir + toward / tl * wave * damp * uRippleAmp);
      glow += max(wave, 0.0) * damp;
    }

    float lon = atan(dir.x, -dir.z);
    float lat = asin(clamp(dir.y, -1.0, 1.0));
    vec2 uv = vec2(0.5 + lon / (2.0 * PI), 0.5 + lat / PI);
    vec3 col = seamless(uv);

    float pole = smoothstep(uPoleFade.x, uPoleFade.y, abs(lat));
    col = mix(col, lat > 0.0 ? uZenith : uNadir, pole);
    col += glow * uRippleGlow;

    gl_FragColor = vec4(col, 1.0);
    #include <colorspace_fragment>
  }
`;

export function createPanoSphere(stillTexture, liveTexture) {
  const ripples = Array.from({ length: RIPPLE.max }, () => new THREE.Vector4(0, 0, -1, -1));
  const material = new THREE.ShaderMaterial({
    vertexShader,
    fragmentShader,
    side: THREE.BackSide,
    depthWrite: false,
    uniforms: {
      uStill: { value: stillTexture },
      uLive: { value: liveTexture ?? stillTexture },
      uLiveMix: { value: 0 },
      uZenith: { value: new THREE.Color(0.75, 0.75, 0.7) },
      uNadir: { value: new THREE.Color(0.35, 0.38, 0.25) },
      uSeamBand: { value: SPHERE.seamBand },
      uEdgeCrop: { value: SPHERE.edgeCrop },
      uPoleFade: { value: new THREE.Vector2(THREE.MathUtils.degToRad(SPHERE.poleFadeStart), THREE.MathUtils.degToRad(SPHERE.poleFadeEnd)) },
      uTime: { value: 0 },
      uRipples: { value: ripples },
      uRippleLife: { value: RIPPLE.lifetime },
      uRippleSpeed: { value: RIPPLE.speed },
      uRippleWave: { value: RIPPLE.wavelength },
      uRippleAmp: { value: RIPPLE.amplitude },
      uRippleGlow: { value: RIPPLE.glow },
    },
  });
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(1, 96, 48), material);
  mesh.frustumCulled = false;
  mesh.renderOrder = -1;

  let next = 0;
  return {
    mesh,
    material,
    addRipple(direction, time) {
      const d = direction.clone().normalize();
      ripples[next].set(d.x, d.y, d.z, time);
      next = (next + 1) % RIPPLE.max;
    },
  };
}

// Average colour of the top and bottom strips of an image/video, for the pole fade.
const probe = document.createElement('canvas');
probe.width = 32;
probe.height = 16;
const probeCtx = probe.getContext('2d', { willReadFrequently: true });
export function measurePoles(source, zenith, nadir) {
  try {
    probeCtx.drawImage(source, 0, 0, probe.width, probe.height);
    const px = probeCtx.getImageData(0, 0, probe.width, probe.height).data;
    const avg = (rows) => {
      let r = 0, g = 0, b = 0, n = 0;
      for (const y of rows) for (let x = 0; x < probe.width; x++) {
        const i = (y * probe.width + x) * 4;
        r += px[i]; g += px[i + 1]; b += px[i + 2]; n++;
      }
      return [r / n / 255, g / n / 255, b / n / 255];
    };
    zenith.setRGB(...avg([1, 2]), THREE.SRGBColorSpace);
    nadir.setRGB(...avg([13, 14]), THREE.SRGBColorSpace);
  } catch {
    // A cross-origin or not-yet-decoded source cannot be read; keep the previous colours.
  }
}
