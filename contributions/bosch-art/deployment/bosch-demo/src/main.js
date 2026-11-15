// Entry point. A scene with media/manifest.json is the paired-video reveal demo (pure static:
// no /api, no Reactor, nothing loaded from the live code). Any other scene is the original
// live Orbis page (liveMain.js), which needs the dev server's /api routes.
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

const manifest = params.get('experience')==='live' ? null : await loadManifest(sceneName);
if (params.get('experience')==='live') {
  const {startLiveGarden}=await import('./liveGarden.js');
  await startLiveGarden();
} else if (manifest) {
  const { startDemo } = await import('./demo.js');
  await startDemo(sceneName, manifest);
} else if (import.meta.env.VITE_STATIC === '1') {
  document.getElementById('status').textContent = `scene "${sceneName}" has no media/manifest.json (live scenes need the dev server)`;
} else {
  await import('./liveMain.js');
}
