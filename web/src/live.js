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
//
// Relay (scene.loop, needs the keeper to hold BOTH Dynamic sessions): Orbis loses the
// reference after ~25-30 s, and re-anchoring one session costs ~9 s of frozen picture. With
// two sessions the second one ("standby", keeper slot 2) is anchored and started while the
// first is still on the sphere; when it has frames the page cross-fades live -> live and the
// first becomes the standby. No frozen frame, for the timed loop and for events alike. Each
// line plays on its own video "deck" (0 or 1) so both can be decoded during the hand-over.

export function createLive({ scene, onStatus, onVideo, onAudio, onMessage, onFrames, onFreeze, onLine, onIdle }) {
  let line = null; // the line whose picture is on the sphere
  let wanted = false;
  let retryTimer = null;
  let probeTimer = null;
  let refreshTimer = null;
  let busy = false; // a re-anchor or switch is in progress
  let standby = null; // relay: the idle Orbis line on the keeper's second session
  let incoming = null; // relay: the standby while it warms up for a hand-over
  let relayTimer = null;
  let idleTimer = null;
  let relayAgain = false; // an event arrived during a hand-over: relay once more when it is done
  const loop = scene.loop;
  // What the picture is anchored to; a new line starts from the latest anchor, not the opening.
  let anchor = { reference: scene.reference, prompt: scene.opening, label: 'opening' };
  const fallback = scene.fallback;

  const status = (s, detail = '') => onStatus?.(s, detail);
  const isOrbis = (model) => model.includes('visko-orbis');
  const label = (l) => (l ? (isOrbis(l.model) ? 'Orbis Dynamic' : 'LingBot World 2 (fallback)') : '');

  async function token(model, attach, slot) {
    const r = await fetch(`/api/token?model=${encodeURIComponent(model)}${attach ? `&attach=1&slot=${slot}` : ''}`, { method: 'POST' });
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
  async function open(model, slot = 1) {
    const l = { model, deck: slot - 1, reactor: new Reactor({ modelName: model }), uploads: new Map(), awaitingFrames: false, tracks: {} };
    l.reactor.on('message', (m) => {
      if (l.awaitingFrames && m?.type === 'chunk_complete' && m.data?.frames_emitted > 0) {
        l.awaitingFrames = false;
        if (l === line) onFrames?.(anchor, label(l), l.deck);
        else if (l === incoming) handOver(l);
      }
      if (l === line) onMessage?.(m);
    });
    l.reactor.on('error', (e) => l === line && status('error', `${e.operation ?? ''} ${e.code ?? ''} ${e.message ?? e}`));
    l.reactor.on('trackReceived', (name, track, stream) => {
      l.tracks[name] = stream;
      if (l === line) (name === 'main_video' ? onVideo : onAudio)?.(stream, l.deck);
    });
    const held = isOrbis(model) ? await keeper() : null;
    if (slot > 1 && (held?.session_ids?.length ?? 0) < slot) throw new Error(`keeper holds no slot ${slot}`);
    const { jwt, sessionId } = await token(model, Boolean(held), slot);
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
    dropRelay();
    if (l.tracks.main_video) onVideo?.(l.tracks.main_video, l.deck);
    if (l.tracks.main_audio) onAudio?.(l.tracks.main_audio, l.deck);
    await anchorAndStart(l);
    status('generating', `${anchor.label} · ${label(l)}${l.adopted ? ` · keeper, ${l.held.minutes_left} min left` : ''}`);
    for (const e of scene.events) if (e.mode === 'reanchor' && e.reference) fileRef(l, e.reference).catch(() => {});
    if (old) await cleanup(old);
    clearInterval(refreshTimer);
    if (!isOrbis(l.model) && fallback?.reanchor_every_seconds) {
      refreshTimer = setInterval(() => reanchorTo(anchor, true), fallback.reanchor_every_seconds * 1000);
    }
    if (isOrbis(l.model) && l.adopted && loop) armRelay(l);
  }

  // ---- relay between the keeper's two sessions ----

  async function armRelay(first) {
    if ((first.held?.session_ids?.length ?? 0) < 2) return; // one-session hold: no relay
    try {
      const l = await open(scene.model, first.deck === 0 ? 2 : 1);
      if (line !== first || !wanted) return cleanup(l);
      standby = l;
      for (const e of scene.events) if (e.mode === 'reanchor' && e.reference) fileRef(l, e.reference).catch(() => {});
      fileRef(l, anchor.reference).catch(() => {});
      console.info('[live] relay armed: standby on keeper slot', l.deck + 1);
      scheduleRelay();
    } catch (e) {
      console.warn('[live] relay not available:', String(e?.message ?? e));
    }
  }

  function dropRelay() {
    clearTimeout(relayTimer);
    clearTimeout(idleTimer);
    for (const l of [standby, incoming]) if (l && l !== line) cleanup(l);
    standby = incoming = null;
    relayAgain = false;
  }

  // The next timed hand-over: start warming the standby early enough that the line on the
  // sphere has been visible for about loop.live_seconds when the new one takes over.
  function scheduleRelay(sinceHandOver = 0) {
    clearTimeout(relayTimer);
    if (!standby || !loop?.live_seconds) return;
    const lead = Math.max(1, loop.live_seconds - (loop.warmup_seconds ?? 9) - sinceHandOver);
    relayTimer = setTimeout(() => relayTo(anchor, true), lead * 1000);
  }

  // Anchor and start the standby; handOver() runs when it has frames.
  async function relayTo(next, quiet = false) {
    anchor = next;
    if (!standby || !line || !wanted) return false;
    if (incoming || idleTimer) {
      relayAgain = true; // one hand-over at a time; pick up the latest anchor afterwards
      return true;
    }
    clearTimeout(relayTimer);
    const to = standby;
    incoming = to;
    if (!quiet) status('reanchoring', `${next.label} · warming the second session`);
    try {
      if (to.tracks.main_video) onVideo?.(to.tracks.main_video, to.deck);
      await anchorAndStart(to);
    } catch (e) {
      console.warn('[live] relay failed, falling back to a plain re-anchor:', String(e?.message ?? e));
      incoming = null;
      dropRelay();
      return reanchorTo(next, quiet);
    }
    return true;
  }

  // The standby has picture: it becomes the line on the sphere (the page cross-fades from the
  // old deck, which keeps playing), and the old line is reset once the fade is over.
  function handOver(l) {
    const old = line;
    const settle = (loop?.fade_seconds ?? 3) + 4; // the page may wait ~2.5 s for decoded frames before fading
    incoming = null;
    line = l;
    standby = old;
    onLine?.(l.model);
    if (l.tracks.main_audio) onAudio?.(l.tracks.main_audio, l.deck);
    onFrames?.(anchor, label(l), l.deck);
    status('generating', `${anchor.label} · ${label(l)} · relay, slot ${l.deck + 1}`);
    idleTimer = setTimeout(async () => {
      idleTimer = null;
      try {
        await old.reactor.sendCommand('reset', {}); // stop generating; the session stays held
      } catch {}
      onIdle?.(old.deck);
      if (relayAgain) {
        relayAgain = false;
        relayTo(anchor, true);
      } else scheduleRelay(settle);
    }, settle * 1000);
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
    if (standby && line && isOrbis(line.model)) return relayTo(next, quiet);
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
    for (const x of [standby, incoming]) {
      if (!x || x === l) continue;
      try {
        await x.reactor.sendCommand('reset', {});
      } catch {}
    }
    dropRelay();
    if (l) {
      if (l.adopted) {
        try {
          await l.reactor.sendCommand('reset', {}); // held session: stop generating, keep it
        } catch {}
      }
      await cleanup(l);
    }
    status('stopped');
  }

  // Never leave a billed session behind when the tab goes away.
  window.addEventListener('pagehide', () => {
    for (const l of [line, standby, incoming]) if (l) l.reactor.disconnect();
  });

  const ready = () => line && line.reactor.getStatus() === 'ready';

  return {
    start() { wanted = true; attempt(); },
    stop,
    get active() { return wanted; },
    get ready() { return Boolean(ready()); },
    get model() { return line?.model ?? null; },
    get relay() { return Boolean(standby || incoming); },
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
