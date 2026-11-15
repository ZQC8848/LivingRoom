import { Reactor } from '@reactor-team/js-sdk';
import { LIVE } from './config.js';

// The live picture for the sphere: one Reactor session at a time ("line").
//
// Primary line: Orbis Dynamic -- the keeper's held session if tools/keeper.py has one, else a
// session of our own. Fallback line (scene.fallback, LingBot World 2 on the personal account):
// used only while Dynamic is busy, retried every probe_primary_every_seconds; when Dynamic
// frees up the page switches over behind a frozen frame and closes the fallback.
//
// Constraints this code is shaped around (all measured 2026-11-14, see CLAUDE.md):
// - Dynamic serves ONE session at a time for everyone on Reactor ("no available capacity").
// - Billing runs per second from `ready` until disconnect, idle or not -> always disconnect
//   on stop and on page hide; the dev server caps sessions (Orbis 15 min, LingBot 10 min).
// - set_image only anchors the first chunk -> changing the anchor = reset + set_image + start
//   on the SAME session (re-anchor), never a new session.
// - A session-scoped JWT may only act on sessions it created: one token per line, reused.
// - Big scene-wide steers re-compose Orbis' panorama -> those events re-anchor instead.
// - LingBot holds its layout ~50 s then its bottom edge degrades -> re-anchor it periodically
//   (its warm-up is < 1 s).

export function createLive({ scene, onStatus, onVideo, onAudio, onMessage, onFrames, onFreeze, onLine }) {
  let line = null; // the line whose picture is on the sphere
  let wanted = false;
  let retryTimer = null;
  let probeTimer = null;
  let refreshTimer = null;
  let busy = false; // a re-anchor or switch is in progress
  // What the picture is anchored to; a new line starts from the latest anchor, not the opening.
  let anchor = { reference: scene.reference, prompt: scene.opening, label: 'opening' };
  const fallback = scene.fallback;

  const status = (s, detail = '') => onStatus?.(s, detail);
  const isOrbis = (model) => model.includes('visko-orbis');
  const label = (l) => (l ? (isOrbis(l.model) ? 'Orbis Dynamic' : 'LingBot World 2 (fallback)') : '');

  async function token(model, attach) {
    const r = await fetch(`/api/token?model=${encodeURIComponent(model)}${attach ? '&attach=1' : ''}`, { method: 'POST' });
    const body = await r.json();
    if (!r.ok) throw new Error(body.error || `token ${r.status}`);
    return body;
  }

  // If tools/keeper.py is holding the Dynamic session, adopt it instead of creating one.
  async function keeper() {
    try {
      const k = await (await fetch('/api/keeper')).json();
      return k.phase === 'holding' && k.model === scene.model ? k : null;
    } catch {
      return null;
    }
  }

  // Open a line on `model`. Its tracks are held back until the line is promoted, so a probe
  // that connects never touches the picture until we decide to switch to it.
  async function open(model) {
    const l = { model, reactor: new Reactor({ modelName: model }), uploads: new Map(), awaitingFrames: false, tracks: {} };
    l.reactor.on('message', (m) => {
      if (l.awaitingFrames && m?.type === 'chunk_complete' && m.data?.frames_emitted > 0) {
        l.awaitingFrames = false;
        if (l === line) onFrames?.(anchor, label(l));
      }
      if (l === line) onMessage?.(m);
    });
    l.reactor.on('error', (e) => l === line && status('error', `${e.operation ?? ''} ${e.code ?? ''} ${e.message ?? e}`));
    l.reactor.on('trackReceived', (name, track, stream) => {
      l.tracks[name] = stream;
      if (l === line) (name === 'main_video' ? onVideo : onAudio)?.(stream);
    });
    const held = isOrbis(model) ? await keeper() : null;
    const { jwt, sessionId } = await token(model, Boolean(held));
    try {
      await l.reactor.connect(jwt, sessionId ? { sessionId } : undefined);
    } catch (e) {
      l.adopted = Boolean(sessionId);
      await cleanup(l);
      throw e;
    }
    l.adopted = Boolean(sessionId);
    l.sessionId = l.reactor.getSessionId();
    l.held = held;
    console.info('[live] line', model, l.sessionId, l.adopted ? `(keeper, ${held.minutes_left} min left)` : '(own)');
    return l;
  }

  // Disconnect a line. Never end the keeper's session from here; if one of our own sessions
  // exists but the disconnect failed, end it server-side so it stops billing.
  async function cleanup(l) {
    const own = l.adopted ? null : l.reactor.getSessionId?.();
    try {
      await l.reactor.disconnect();
    } catch {
      if (own) fetch(`/api/end-session/${own}?model=${encodeURIComponent(l.model)}`, { method: 'POST' });
    }
  }

  async function fileRef(l, url) {
    if (!l.uploads.has(url)) {
      const blob = await (await fetch(url)).blob();
      l.uploads.set(url, await l.reactor.uploadFile(blob, { name: url.split('/').pop() }));
    }
    return l.uploads.get(url);
  }

  // reset (harmless on a fresh session, required on an adopted one) -> anchor -> start.
  async function anchorAndStart(l) {
    await l.reactor.sendCommand('reset', {});
    if (isOrbis(l.model)) await l.reactor.sendCommand('set_resolution', { resolution: LIVE.resolution });
    await l.reactor.sendCommand('set_image', { image: await fileRef(l, anchor.reference) });
    await l.reactor.sendCommand('set_prompt', { prompt: anchor.prompt });
    l.awaitingFrames = true;
    await l.reactor.sendCommand('start', {});
  }

  // Make `l` the line on the sphere: freeze the old picture, attach the new tracks, start.
  async function promote(l) {
    const old = line;
    if (old) onFreeze?.(false);
    line = l;
    onLine?.(l.model);
    if (l.tracks.main_video) onVideo?.(l.tracks.main_video);
    if (l.tracks.main_audio) onAudio?.(l.tracks.main_audio);
    await anchorAndStart(l);
    status('generating', `${anchor.label} · ${label(l)}${l.adopted ? ` · keeper, ${l.held.minutes_left} min left` : ''}`);
    for (const e of scene.events) if (e.mode === 'reanchor' && e.reference) fileRef(l, e.reference).catch(() => {});
    if (old) await cleanup(old);
    clearInterval(refreshTimer);
    if (!isOrbis(l.model) && fallback?.reanchor_every_seconds) {
      refreshTimer = setInterval(() => reanchorTo(anchor, true), fallback.reanchor_every_seconds * 1000);
    }
  }

  const busyError = (e) => /capacity|RATE_LIMITED|429/i.test(String(e?.message ?? e));

  async function attempt() {
    clearTimeout(retryTimer);
    if (!wanted) return;
    status('connecting', 'Orbis Dynamic');
    try {
      await promote(await open(scene.model));
      clearInterval(probeTimer);
      return;
    } catch (e) {
      console.warn('[live] Orbis connect failed:', String(e?.message ?? e));
      if (!wanted) return;
      if (!busyError(e) || !fallback) {
        status(busyError(e) ? 'busy' : 'error', busyError(e) ? `Dynamic is in use elsewhere; retrying in ${LIVE.retrySeconds}s` : String(e?.message ?? e));
        retryTimer = setTimeout(attempt, LIVE.retrySeconds * 1000);
        return;
      }
    }
    // Dynamic is busy: run the fallback and keep probing Dynamic.
    try {
      status('connecting', 'Dynamic busy -> LingBot World 2 fallback');
      await promote(await open(fallback.model));
      clearInterval(probeTimer);
      probeTimer = setInterval(probePrimary, (fallback.probe_primary_every_seconds ?? 30) * 1000);
    } catch (e) {
      status('error', `fallback failed: ${String(e?.message ?? e)}; retrying in ${LIVE.retrySeconds}s`);
      retryTimer = setTimeout(attempt, LIVE.retrySeconds * 1000);
    }
  }

  async function probePrimary() {
    if (!wanted || busy || (line && isOrbis(line.model))) return;
    let l;
    try {
      l = await open(scene.model);
    } catch (e) {
      if (!busyError(e)) console.warn('[live] Orbis probe failed:', String(e?.message ?? e));
      return; // still busy; stay on the fallback
    }
    if (!wanted) return cleanup(l);
    busy = true;
    try {
      clearInterval(probeTimer);
      await promote(l);
    } finally {
      busy = false;
    }
  }

  async function reanchorTo(next, quiet = false) {
    anchor = next;
    if (!line || line.reactor.getStatus() !== 'ready' || busy) return false;
    busy = true;
    try {
      onFreeze?.(quiet);
      if (!quiet) status('reanchoring', next.label);
      await anchorAndStart(line);
      status('generating', `${next.label} · ${label(line)}`);
      return true;
    } finally {
      busy = false;
    }
  }

  async function stop() {
    wanted = false;
    clearTimeout(retryTimer);
    clearInterval(probeTimer);
    clearInterval(refreshTimer);
    const l = line;
    line = null;
    if (l) await cleanup(l);
    status('stopped');
  }

  // Never leave a billed session behind when the tab goes away.
  window.addEventListener('pagehide', () => { if (line) line.reactor.disconnect(); });

  const ready = () => line && line.reactor.getStatus() === 'ready';

  return {
    start() { wanted = true; attempt(); },
    stop,
    get active() { return wanted; },
    get ready() { return Boolean(ready()); },
    get model() { return line?.model ?? null; },
    async steer(prompt) {
      if (!ready()) return false;
      await line.reactor.sendCommand('set_prompt', { prompt });
      return true;
    },
    // Swap the anchor without giving up the session; onFrames fires when the new run has
    // picture again. Offline, it just records the anchor for the next connect.
    reanchor(event) {
      return reanchorTo({ reference: event.reference, prompt: event.prompt, label: event.label });
    },
  };
}
