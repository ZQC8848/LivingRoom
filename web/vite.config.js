import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { defineConfig, loadEnv } from 'vite';
import basicSsl from '@vitejs/plugin-basic-ssl';

// WebXR needs a secure context. The Quest reaches this over LAN, so `npm run dev` serves
// HTTPS (self-signed) on all interfaces. `npm run dev:local` serves plain HTTP for desktop
// checks — localhost counts as a secure context without a certificate.
const plainHttp = process.env.LR_HTTP === '1';
const ROOT = path.resolve(__dirname, '..');
const MODEL = 'reactor/visko-orbis-dynamic';
const ALLOWED = new Set(['reactor/visko-orbis-dynamic', 'reactor/visko-orbis-stable', 'reactor/lingbot-world-2']);
// Which .env key pays for which model. The hackathon key only opens Orbis; the LingBot World 2
// fallback runs on the personal account (REACTOR_API_KEY_ALT, $0.42/min) -- capped shorter.
const keyFor = (env, model) => (model === 'reactor/lingbot-world-2' ? env.REACTOR_API_KEY_ALT : env.REACTOR_API_KEY);
const capFor = (model) => (model === 'reactor/lingbot-world-2' ? 600 : 900);

// The Reactor API key never reaches the browser: the dev server mints a short-lived,
// single-model JWT and hands that out. Sessions it allows are capped at 15 minutes so a
// forgotten tab cannot keep the (billed, and globally single) Dynamic server.
// Custom prompts ("snow begins to fall"): an image model edits the current reference into
// the new scene, and the page re-anchors Orbis on the result. Picked 2026-11-14 with
// tools/image_edit_test.py: 3-4 s and ~$0.034 per image, kept the panorama's layout best.
const EDIT_MODEL = 'google/gemini-3.1-flash-lite-image';
const EDIT_INSTRUCTION = (change) =>
  `Edit this image: ${change}. This is an equirectangular 360-degree panorama squeezed to 16:9. ` +
  'Keep the composition exactly: the horizon line, every hill, tree, animal and object stays at the same ' +
  'position and size, add no new objects or animals, and the left and right edges must still join seamlessly. ' +
  'Change only the weather, light, sky and surface appearance. Output a single 16:9 image, no text, no border.';
// In parallel a small text model turns the viewer's words into the scene sentence of the Orbis
// prompt. A prompt is scene content, not an instruction (CLAUDE.md): "snow begin to fall" has
// to become what is seen, and must never name a camera.
const REWRITE_MODEL = 'anthropic/claude-haiku-5.5';
const REWRITE_INSTRUCTION = (change) =>
  'A viewer of a live 360-degree landscape (a grassy hilltop above a lake and snowy mountains, with sheep, a hut ' +
  `and an oak tree) asked for this change: "${change}". Write ONE sentence, at most 30 words, present tense, ` +
  'that describes the weather, sky, light and ground as they now look, as plain scene description. Do not ' +
  'mention a camera, lens, photo, viewer or any change; do not add objects. Reply with the sentence only.';

async function openrouter(key, body, timeoutMs) {
  const r = await fetch('https://openrouter.ai/api/v1/chat/completions', {
    method: 'POST',
    headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
    signal: AbortSignal.timeout(timeoutMs),
    body: JSON.stringify(body),
  });
  const out = await r.json();
  if (!r.ok) throw new Error(out.error?.message || `openrouter ${r.status}`);
  return out;
}

function readJson(req) {
  return new Promise((resolve, reject) => {
    let s = '';
    req.on('data', (d) => (s += d));
    req.on('end', () => {
      try {
        resolve(JSON.parse(s || '{}'));
      } catch (e) {
        reject(e);
      }
    });
    req.on('error', reject);
  });
}

async function keeperStatus() {
  try {
    const r = await fetch('http://127.0.0.1:5199/status', { signal: AbortSignal.timeout(1500) });
    return await r.json();
  } catch {
    return null;
  }
}

function livingRoomApi(env) {
  const send = (res, code, body) => {
    res.statusCode = code;
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify(body));
  };
  return {
    name: 'living-room-api',
    configureServer(server) {
      server.middlewares.use('/api/token', async (req, res) => {
        if (req.method !== 'POST') return send(res, 405, { error: 'POST only' });
        const q = new URL(req.url, 'http://x').searchParams;
        const model = q.get('model') || MODEL;
        if (!ALLOWED.has(model)) return send(res, 400, { error: `model not allowed: ${model}` });
        const key = keyFor(env, model);
        if (!key) return send(res, 500, { error: `no API key in .env for ${model}` });
        // ?attach=1: a token bound to the session tools/keeper.py is holding. It can adopt that
        // session but create none, and the client's disconnect leaves the session running.
        let sessionId;
        if (q.get('attach')) {
          const k = await keeperStatus();
          if (k?.phase !== 'holding') return send(res, 409, { error: 'no keeper hold', keeper: k });
          // ?slot=2 picks the keeper's second session (two-session hold); default slot 1.
          const ids = k.session_ids ?? [k.session_id];
          sessionId = ids[Number(q.get('slot') || 1) - 1];
          if (!sessionId) return send(res, 409, { error: `keeper holds ${ids.length} session(s)`, keeper: k });
        }
        try {
          const resources = { models: { match: [model] } };
          const detail = { type: 'session', resources };
          if (sessionId) resources.sessions = { bind: [sessionId] };
          else detail.constraints = { max_sessions: 20, max_session_duration_seconds: capFor(model) };
          const r = await fetch('https://api.reactor.inc/tokens', {
            method: 'POST',
            headers: { 'Reactor-API-Key': key, 'Content-Type': 'application/json' },
            body: JSON.stringify({ expires_after: 3600, authorization_details: [detail] }),
          });
          const body = await r.json();
          if (!r.ok) return send(res, r.status, body);
          send(res, 200, { jwt: body.jwt, model, expires_at: body.expires_at, sessionId });
        } catch (e) {
          send(res, 502, { error: String(e) });
        }
      });

      // Status of tools/keeper.py (localhost:5199), or {phase: 'none'} if it is not running.
      server.middlewares.use('/api/keeper', async (req, res) => send(res, 200, (await keeperStatus()) ?? { phase: 'none' }));

      // End a session by id with the API key -- the cleanup path when a client lost its
      // own handle (a failed connect after the session was already created). Billed sessions
      // must never be left running.
      server.middlewares.use('/api/end-session', async (req, res) => {
        if (req.method !== 'POST') return send(res, 405, { error: 'POST only' });
        const id = (req.url || '/').replace(/^\//, '').split('?')[0];
        const key = keyFor(env, new URL(req.url, 'http://x').searchParams.get('model') || MODEL);
        if (!/^[0-9a-f-]{36}$/.test(id)) return send(res, 400, { error: 'bad session id' });
        try {
          const r = await fetch(`https://api.reactor.inc/sessions/${id}`, {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ reason: 'living-room client cleanup' }),
          });
          send(res, r.status, { status: r.status, body: (await r.text()).slice(0, 300) });
        } catch (e) {
          send(res, 502, { error: String(e) });
        }
      });

      // POST /api/edit {scene, base, text}: edit the reference at `base` (a /scenes/<scene>/ URL)
      // as `text` asks and return a new re-anchor event {label, reference, prompt}. Results are
      // cached on disk by (base, text), so a repeated prompt is instant and costs nothing.
      server.middlewares.use('/api/edit', async (req, res) => {
        if (req.method !== 'POST') return send(res, 405, { error: 'POST only' });
        try {
          const { scene: name = 'hillside', base, text } = await readJson(req);
          const change = String(text || '').trim().slice(0, 300);
          if (!/^[a-z0-9_-]+$/.test(name) || !change) return send(res, 400, { error: 'scene and text are required' });
          const sceneFile = path.join(ROOT, 'scenes', name, 'scene.json');
          if (!fs.existsSync(sceneFile)) return send(res, 404, { error: `no scene ${name}` });
          const pano = JSON.parse(fs.readFileSync(sceneFile, 'utf8')).orbis?.pano ?? {};
          const assets = fs.realpathSync(path.join(__dirname, 'public', 'scenes', name));
          const prefix = `/scenes/${name}/`;
          const rel = String(base || `${prefix}reference.png`);
          const baseFile = path.resolve(assets, rel.startsWith(prefix) ? rel.slice(prefix.length) : '\0');
          if (!baseFile.startsWith(assets + path.sep) || !fs.existsSync(baseFile)) return send(res, 400, { error: 'bad base image' });

          const id = crypto.createHash('sha1').update(`${path.relative(assets, baseFile)}\n${change.toLowerCase()}`).digest('hex').slice(0, 12);
          const dir = path.join(assets, 'custom');
          const meta = path.join(dir, `${id}.json`);
          if (fs.existsSync(meta)) return send(res, 200, { ...JSON.parse(fs.readFileSync(meta, 'utf8')), cached: true });

          const key = env.OPENROUTER_API_KEY;
          if (!key) return send(res, 500, { error: 'no OPENROUTER_API_KEY in .env' });
          const mime = baseFile.endsWith('.png') ? 'image/png' : 'image/jpeg';
          const t0 = Date.now();
          const [out, seen] = await Promise.all([
            openrouter(key, {
              model: EDIT_MODEL,
              modalities: ['image', 'text'],
              image_config: { aspect_ratio: '16:9' },
              messages: [{ role: 'user', content: [
                { type: 'text', text: EDIT_INSTRUCTION(change) },
                { type: 'image_url', image_url: { url: `data:${mime};base64,${fs.readFileSync(baseFile).toString('base64')}` } },
              ] }],
            }, 90000),
            openrouter(key, { model: REWRITE_MODEL, max_tokens: 120, messages: [{ role: 'user', content: REWRITE_INSTRUCTION(change) }] }, 15000)
              .then((o) => String(o.choices?.[0]?.message?.content || '').replace(/\s+/g, ' ').trim().slice(0, 300))
              .catch(() => ''), // the viewer's own words are the fallback
          ]);
          const msg = out.choices?.[0]?.message;
          const url = msg?.images?.[0]?.image_url?.url;
          if (!url) return send(res, 502, { error: 'the image model returned no image', detail: String(msg?.content ?? '').slice(0, 200) });
          const [head, b64] = url.split(',', 2);
          const ext = head.includes('png') ? 'png' : 'jpg';
          fs.mkdirSync(dir, { recursive: true });
          fs.writeFileSync(path.join(dir, `${id}.${ext}`), Buffer.from(b64, 'base64'));
          const template = pano.custom_prompt ?? `${pano.opening ?? ''} {change}`;
          const event = {
            label: change.length > 28 ? `${change.slice(0, 27)}…` : change,
            mode: 'reanchor',
            reference: `${prefix}custom/${id}.${ext}`,
            prompt: template.replace('{change}', seen || change),
            text: change,
            seen,
            seconds: Math.round((Date.now() - t0) / 100) / 10,
            cost_usd: out.usage?.cost ?? null,
          };
          fs.writeFileSync(meta, JSON.stringify(event, null, 1));
          send(res, 200, event);
        } catch (e) {
          send(res, 502, { error: String(e?.message ?? e) });
        }
      });

      // Scene config for the client: opening prompt, steering events, asset URLs.
      server.middlewares.use('/api/scene', (req, res) => {
        const name = (req.url || '/').replace(/^\//, '').split('?')[0] || 'hillside';
        if (!/^[a-z0-9_-]+$/.test(name)) return send(res, 400, { error: 'bad scene name' });
        const file = path.join(ROOT, 'scenes', name, 'scene.json');
        if (!fs.existsSync(file)) return send(res, 404, { error: `no scene ${name}` });
        const pano = JSON.parse(fs.readFileSync(file, 'utf8')).orbis?.pano;
        send(res, 200, {
          name,
          model: pano?.model ?? MODEL,
          fallback: pano?.fallback ?? null,
          loop: pano?.loop ?? null,
          opening: pano?.opening,
          events: (pano?.events ?? []).map((e) => ({
            ...e,
            reference: e.reference ? `/scenes/${name}/${e.reference}` : undefined,
          })),
          reference: `/scenes/${name}/reference.png`,
          still: `/scenes/${name}/pano_front.jpg`,
        });
      });
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ROOT, '');
  return {
    plugins: [...(plainHttp ? [] : [basicSsl()]), livingRoomApi(env)],
    // Static deploy build (tools/build_static.sh): publicDir is a staging folder holding only the
    // demo scene, so the symlinked ~/Assets scenes (test captures, GBs) never reach dist.
    base: process.env.VITE_STATIC === '1' ? './' : '/',
    publicDir: process.env.LR_PUBLIC_DIR || 'public',
    server: { host: true, port: 5174, strictPort: true },
    build: { target: 'es2022' }, // main.js uses top-level await
  };
});
