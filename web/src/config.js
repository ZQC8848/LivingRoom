// Tunables for the single-stream panorama sphere. See .ai/decisions/single-stream-panorama.md.

export const SPHERE = {
  // Fraction of the frame width, on each side of the left/right edge, cross-blended so the
  // two independently generated edges of the Orbis frame meet without a hard line.
  seamBand: 0.03,
  // Fraction of the frame width ignored at each left/right edge before mapping to 360 deg.
  edgeCrop: 0.004,
  edgeCropByModel: { 'reactor/lingbot-world-2': 0.01 },
  // Latitude (deg) where the poles start fading to a flat colour, and where they are fully flat.
  // Equirect poles are the least reliable pixels in both Marble's pano and Orbis' output.
  poleFadeStart: 68,
  poleFadeEnd: 84,
  liveFadeSeconds: 1.5, // still pano -> live stream crossfade once the first frame arrives
};

export const RIPPLE = {
  max: 8,
  lifetime: 3.0, // s
  speed: 0.35, // rad/s the ring front travels across the sky
  wavelength: 0.045, // rad
  amplitude: 0.012, // rad of lookup displacement at the crest
  glow: 0.3,
};

export const LIVE = {
  retrySeconds: 10, // Dynamic answers 429 "no available capacity" while anyone else holds it
  resolution: '2k',
};
