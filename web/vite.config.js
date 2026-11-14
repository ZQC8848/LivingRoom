import fs from 'node:fs';
import path from 'node:path';
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
          sessionId = k.session_id;
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
    server: { host: true, port: 5174, strictPort: true },
    build: { target: 'es2022' }, // main.js uses top-level await
  };
});
