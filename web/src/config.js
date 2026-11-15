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
  liveFadeSeconds: 2, liveFadeAfterFrames: 4, // still pano -> live stream crossfade once the first frame arrives
};

export const RIPPLE = {
  max: 8,
  lifetime: 3.0, // s
  speed: 0.35, // rad/s the ring front travels across the sky
  wavelength: 0.045, // rad
  amplitude: 0.012, // rad of lookup displacement at the crest
  glow: 0, // white ring on the wave crest; 0 = refraction (image bending) only
};

export const LIVE = {
  retrySeconds: 10, // Dynamic answers 429 "no available capacity" while anyone else holds it
  resolution: '2k',
};

// Paired-video reveal demo (scenes with media/manifest.json, e.g. bosch-demo). Every value can be
// overridden by the manifest's "reveal" / "projection" objects. See .ai/decisions/paired-video-reveal.md.
export const REVEAL = {
  radiusDeg: 38, // angular radius of the revealed cap at full size
  featherDeg: 14, // soft edge, measured inward from the radius
  growSeconds: 0.7, // time to open from nothing
  shrinkSeconds: 0.5, // time to close after release
  maxSlots: 2, // two controllers / hands at once
  rimGlow: 0.18, // faint light on the edge so the boundary reads in both layers
  desktopHoldSeconds: 0, // 0 = a desktop click toggles; >0 = a click opens it for that long
};
export const DEMO = {
  defaultScene: 'bosch-demo',
  driftToleranceFrames: 1.5, // hell is re-synced to heaven beyond this many frames of difference
  syncIntervalMs: 400,
};
