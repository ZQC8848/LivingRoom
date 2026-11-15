// Entry point.
//
// Default: one page with two experiences that share a renderer and a WebXR session
// (shell.js): the live hillside (liveMain.js, needs the dev server's /api routes) and the
// painted Garden of Consequences (garden/, static media under /garden/). Switching between
// them never leaves VR. ?exp=garden opens on the Garden.
//
// Legacy: ?scene=<name> for a scene that has media/manifest.json runs the original
// paired-video reveal demo on its own (demo.js: pure static, no /api, nothing from the shell).
const params = new URLSearchParams(location.search);
const sceneName = params.get('scene') || import.meta.env.VITE_DEFAULT_SCENE || 'hillside';

async function loadManifest(name) {
  try {
    const r = await fetch(`/scenes/${name}/media/manifest.json`, { cache: 'no-cache' });
    if (!r.ok || !(r.headers.get('content-type') || '').includes('json')) return null; // SPA fallback returns html
    return await r.json();
  } catch {
    return null;
  }
}

const manifest = import.meta.env.VITE_DEPLOY === '1' ? null : await loadManifest(sceneName);
if (manifest) {
  const { startDemo } = await import('./demo.js');
  await startDemo(sceneName, manifest);
} else if (import.meta.env.VITE_STATIC === '1') {
  document.getElementById('status').textContent = `scene "${sceneName}" has no media/manifest.json (live scenes need the dev server)`;
} else {
  const { shell } = await import('./shell.js');
  const deploy = import.meta.env.VITE_DEPLOY === '1'; // public build: the recorded hillside only
  // Declared before the hillside loads, so that it can offer the switch; loaded on first use.
  if (!deploy) shell.lazy('garden', () => import('./garden/garden.js').then((m) => m.startGarden()));
  await import('./liveMain.js'); // registers 'hillside', which becomes the active experience
  if (deploy) {
    // nothing else to load
  } else if (params.get('exp') === 'garden') shell.switchTo('garden');
  else setTimeout(() => shell.preload('garden'), 2500); // fetch it while the viewer looks at the hillside
}
