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
const EDIT_INSTRUCTION = (change, fixed) =>
  `Edit this image so that it shows: ${change}. This is an equirectangular 360-degree panorama squeezed to 16:9. ` +
  `Keep these exactly where they are, at the same position and size: ${fixed.join(', ')}. Keep the horizon line ` +
  'and the overall composition, and the left and right edges must still join seamlessly. Paint what the request ' +
  'asks for into this scene; anything that should be moving must be caught mid-motion (streaks, trails, spray, ' +
  'falling or drifting particles), never hanging still. Output a single 16:9 image, no text, no border.';

// The "prompt director": one small text-model call that splits a viewer's request into what
// must stay still and what must move, and writes the Orbis prompt from that. Why it exists
// (2026-11-14): the first version described only weather and light and its template said
// "everything stays exactly where it is" -- "asteroids fall from the sky" came out as a still
// orange sky. What we know about Orbis prompts (CLAUDE.md): a prompt is scene content, not an
// instruction; motion must be written as what is seen and in which direction; naming a
// camera puts a camera into the scene. The output is checked by lintPrompt(), not trusted.
const PROMPT_VERSION = 2; // bump to rewrite cached prompts (cached pictures are kept)
const DIRECTOR_MODEL = 'anthropic/claude-haiku-5.5';
const DIRECTOR_INSTRUCTION = (change, pano, problems) =>
  `A live, endlessly generated 360-degree video shows this place: ${pano.layout} ` +
  `These things are FIXED and must never move, grow, or be described as changing position: ${pano.fixed.join(', ')}. ` +
  `A viewer asked for: "${change}".\n` +
  'Reply with JSON only, no markdown:\n' +
  '{"moving": [things that visibly move, 1-4 short nouns, none of the FIXED things],\n' +
  ' "motion": "1-2 sentences, present tense, at most 45 words: what is SEEN moving, where in the view, in which ' +
  'direction and how fast (e.g. \"streak down from upper right to lower left, one after another\"). ' +
  'If the request is a state rather than an action (\"winter\"), describe its ambient motion (snow drifting down, grass swaying).",\n' +
  ' "ambience": "1 sentence, at most 25 words: sky, light and weather as they look",\n' +
  ' "static_request": true only if nothing at all should move}\n' +
  'Rules: plain scene description, as if describing what is in front of you. Never mention a camera, lens, shot, ' +
  'pan, zoom, photo, video, viewer, or the request itself. Do not move or destroy the FIXED things; effects may ' +
  'happen on and around them (smoke rising from the hill, snow lying on the hut roof).' +
  (problems?.length ? `\nYour previous answer had these problems, fix them: ${problems.join('; ')}.` : '');

const BANNED = /\b(camera|lens|tripod|shot|pans?|panning|zoom\w*|photo\w*|footage|video|viewer|film\w*|frame)\b/i;

function composePrompt(pano, plan) {
  return [pano.frame, pano.layout, pano.fixed_sentence, plan.motion, plan.ambience].filter(Boolean).join(' ').replace(/\s+/g, ' ').trim();
}

// Hard checks on the director's answer; returns the list of problems (empty = fine).
function lintPrompt(pano, plan) {
  const problems = [];
  const text = `${plan.motion || ''} ${plan.ambience || ''}`;
  const hit = text.match(BANNED);
  if (hit) problems.push(`uses the word "${hit[0]}" (never name a camera, shot, photo or viewer)`);
  if (!plan.static_request && (plan.motion || '').trim().split(/\s+/).length < 6) problems.push('motion is missing or too short');
  if (!(plan.ambience || '').trim()) problems.push('ambience is missing');
  const fixedWords = pano.fixed.flatMap((f) => f.toLowerCase().split(/\s+/)).filter((w) => w.length > 2);
  const clash = (plan.moving || []).find((m) => fixedWords.some((w) => new RegExp(`\\b${w}s?\\b`).test(String(m).toLowerCase())));
  if (clash) problems.push(`"${clash}" is a FIXED thing and may not be in moving`);
  if (!Array.isArray(plan.moving) || (!plan.static_request && !plan.moving.length)) problems.push('moving is empty');
  if (composePrompt(pano, plan).split(/\s+/).length > 150) problems.push('too long');
  return problems;
}

// Ask the director, check, retry once with the problems, else fall back to the viewer's words.
async function direct(key, change, pano) {
  let problems = [];
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      // max_tokens covers the model's hidden reasoning too: at 120 unusual requests came back empty.
      const o = await openrouter(key, { model: DIRECTOR_MODEL, max_tokens: 1500, messages: [{ role: 'user', content: DIRECTOR_INSTRUCTION(change, pano, problems) }] }, 20000);
      const raw = String(o.choices?.[0]?.message?.content || '');
      const plan = JSON.parse(raw.slice(raw.indexOf('{'), raw.lastIndexOf('}') + 1));
      problems = lintPrompt(pano, plan);
      if (!problems.length) return { ...plan, prompt: composePrompt(pano, plan), lint: [], attempts: attempt + 1 };
    } catch (e) {
      problems = [`answer was not valid JSON (${String(e?.message ?? e).slice(0, 60)})`];
    }
  }
  const safe = change.replace(new RegExp(BANNED.source, 'gi'), '').replace(/\s+/g, ' ').trim();
  const plan = { moving: [], motion: `${safe.charAt(0).toUpperCase()}${safe.slice(1)}.`, ambience: '', static_request: false };
  return { ...plan, prompt: composePrompt(pano, plan), lint: problems, attempts: 2, fallback: true };
}

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

      // POST /api/edit {scene, text}: paint what `text` asks onto the scene's original
      // reference.png and return a new re-anchor event {label, reference, prompt}. Always the
      // original, whatever is on the sphere now: edits do not stack. Results are cached on disk
      // by text, so a repeated prompt is instant and costs nothing.
      server.middlewares.use('/api/edit', async (req, res) => {
        if (req.method !== 'POST') return send(res, 405, { error: 'POST only' });
        try {
          const { scene: name = 'hillside', text } = await readJson(req);
          const change = String(text || '').trim().slice(0, 300);
          if (!/^[a-z0-9_-]+$/.test(name) || !change) return send(res, 400, { error: 'scene and text are required' });
          const sceneFile = path.join(ROOT, 'scenes', name, 'scene.json');
          if (!fs.existsSync(sceneFile)) return send(res, 404, { error: `no scene ${name}` });
          const pano = JSON.parse(fs.readFileSync(sceneFile, 'utf8')).orbis?.pano ?? {};
          const assets = fs.realpathSync(path.join(__dirname, 'public', 'scenes', name));
          const prefix = `/scenes/${name}/`;
          const baseFile = path.join(assets, 'reference.png');
          if (!fs.existsSync(baseFile)) return send(res, 500, { error: 'the scene has no reference.png' });
          for (const k of ['frame', 'layout', 'fixed', 'fixed_sentence']) if (!pano[k]) return send(res, 500, { error: `scene.json orbis.pano.${k} is missing` });
          const id = crypto.createHash('sha1').update(change.toLowerCase()).digest('hex').slice(0, 12);
          const dir = path.join(assets, 'custom');
          const meta = path.join(dir, `${id}.json`);
          const key = env.OPENROUTER_API_KEY;
          if (!key) return send(res, 500, { error: 'no OPENROUTER_API_KEY in .env' });
          const t0 = Date.now();
          const seconds = () => Math.round((Date.now() - t0) / 100) / 10;
          const asEvent = (reference, plan, extra) => ({
            label: change.length > 28 ? `${change.slice(0, 27)}…` : change,
            mode: 'reanchor',
            reference,
            prompt: plan.prompt,
            text: change,
            moving: plan.moving,
            motion: plan.motion,
            ambience: plan.ambience,
            lint: plan.lint,
            fallback: plan.fallback || undefined,
            prompt_version: PROMPT_VERSION,
            ...extra,
          });

          if (fs.existsSync(meta)) {
            const old = JSON.parse(fs.readFileSync(meta, 'utf8'));
            if (old.prompt_version === PROMPT_VERSION) return send(res, 200, { ...old, cached: true });
            // The picture is still good; only its prompt was written by an older director.
            const event = asEvent(old.reference, await direct(key, change, pano), { seconds: seconds(), cost_usd: old.cost_usd });
            fs.writeFileSync(meta, JSON.stringify(event, null, 1));
            return send(res, 200, { ...event, cached: 'picture' });
          }

          const mime = baseFile.endsWith('.png') ? 'image/png' : 'image/jpeg';
          // In parallel: the picture (~4 s) and the director's prompt (~3 s).
          const [out, plan] = await Promise.all([
            openrouter(key, {
              model: EDIT_MODEL,
              modalities: ['image', 'text'],
              image_config: { aspect_ratio: '16:9' },
              messages: [{ role: 'user', content: [
                { type: 'text', text: EDIT_INSTRUCTION(change, pano.fixed) },
                { type: 'image_url', image_url: { url: `data:${mime};base64,${fs.readFileSync(baseFile).toString('base64')}` } },
              ] }],
            }, 90000),
            direct(key, change, pano),
          ]);
          const msg = out.choices?.[0]?.message;
          const url = msg?.images?.[0]?.image_url?.url;
          if (!url) return send(res, 502, { error: 'the image model returned no image', detail: String(msg?.content ?? '').slice(0, 200) });
          const [head, b64] = url.split(',', 2);
          const ext = head.includes('png') ? 'png' : 'jpg';
          fs.mkdirSync(dir, { recursive: true });
          fs.writeFileSync(path.join(dir, `${id}.${ext}`), Buffer.from(b64, 'base64'));
          const event = asEvent(`${prefix}custom/${id}.${ext}`, plan, { seconds: seconds(), cost_usd: out.usage?.cost ?? null });
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
    // VITE_DEPLOY=1 (tools/build_deploy.py, the deploy/vercel branch): the recorded hillside; its
    // stills and clips are in web/deploy-public.
    publicDir: process.env.LR_PUBLIC_DIR || (process.env.VITE_DEPLOY === '1' ? 'deploy-public' : 'public'),
    server: { host: true, port: 5174, strictPort: true },
    build: { target: 'es2022' }, // main.js uses top-level await
  };
});
