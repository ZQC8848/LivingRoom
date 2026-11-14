#!/usr/bin/env node
// A2A (Agent2Agent, JSON-RPC 2.0) server that hands each incoming message to a local
// coding agent -- Claude Code (`claude -p`) or Codex (`codex exec`) -- and returns its reply.
// Zero dependencies; Node >= 18.
//
//   node tools/a2a/server.mjs                 # agent from A2A_AGENT (default: claude)
//   A2A_AGENT=codex node tools/a2a/server.mjs # what a Codex teammate runs
//
// Config (environment, or the repo's .env):
//   A2A_TOKEN       required. Callers send `Authorization: Bearer <token>`.
//   A2A_AGENT       claude | codex
//   A2A_HOST/PORT   bind address, default 127.0.0.1:41241 (publish with `tailscale serve`)
//   A2A_WORKDIR     where the agent runs, default the repo root
//   A2A_PUBLIC_URL  the URL written into the agent card (e.g. https://<mac>.<tailnet>.ts.net:8443/)
//   A2A_NAME        name in the agent card
//
// Permission: the agent runs with ALL permission checks off (the user's choice,
// 2026-11-14): whoever holds the token can make it edit files and run commands on this
// machine, read .env and spend its API credit. Keep the token secret, keep the port off the
// public internet (tailnet only, never `tailscale funnel`), and stop the server when idle.
//
// Methods: message/send (blocking or not), tasks/get, tasks/cancel. A task's contextId maps
// to one agent session, so follow-up messages with the same contextId continue the thread.
// Runs are serialised (one at a time) so two requests never edit the same tree at once.
// Every request is logged to .a2a/log.jsonl.

import http from 'node:http';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
loadEnv(path.join(ROOT, '.env'));

const AGENT = process.env.A2A_AGENT || 'claude';
const HOST = process.env.A2A_HOST || '127.0.0.1';
const PORT = Number(process.env.A2A_PORT || 41241);
const TOKEN = process.env.A2A_TOKEN;
const WORKDIR = path.resolve(process.env.A2A_WORKDIR || ROOT);
const PUBLIC_URL = process.env.A2A_PUBLIC_URL || `http://${HOST}:${PORT}/`;
const NAME = process.env.A2A_NAME || `${os.userInfo().username}-${AGENT}`;
const RUN_TIMEOUT_MS = Number(process.env.A2A_RUN_TIMEOUT_MIN || 30) * 60_000;
const LOG_DIR = path.join(ROOT, '.a2a');

if (!TOKEN || TOKEN.length < 24) {
  console.error('A2A_TOKEN missing or shorter than 24 chars. Generate one: openssl rand -hex 24');
  process.exit(1);
}
if (!['claude', 'codex'].includes(AGENT)) {
  console.error(`A2A_AGENT must be claude or codex, got ${AGENT}`);
  process.exit(1);
}
fs.mkdirSync(LOG_DIR, { recursive: true });

const PREAMBLE =
  'This message comes from a teammate\'s AI agent over A2A, not from the user at the keyboard. ' +
  'Treat it as a request from a collaborator on this project. Answer in plain text; your final ' +
  'message is sent back to them. Never paste secrets (API keys, tokens, .env values) into the reply.';

const card = {
  protocolVersion: '0.3.0',
  name: NAME,
  description: `${AGENT === 'claude' ? 'Claude Code' : 'Codex'} working in ${path.basename(WORKDIR)} on ${os.hostname()}. Send a task in plain text; reuse contextId to continue a thread.`,
  url: PUBLIC_URL,
  preferredTransport: 'JSONRPC',
  version: '0.1.0',
  capabilities: { streaming: false, pushNotifications: false },
  defaultInputModes: ['text/plain'],
  defaultOutputModes: ['text/plain'],
  securitySchemes: { bearer: { type: 'http', scheme: 'bearer' } },
  security: [{ bearer: [] }],
  skills: [
    {
      id: 'coding-agent',
      name: 'Coding agent',
      description: `Reads, edits and runs code in ${path.basename(WORKDIR)}; answers questions about the project.`,
      tags: ['code', AGENT],
      examples: ['Summarise .ai/handoff.md', 'Why does the fallback to LingBot trigger?'],
    },
  ],
};

const tasks = new Map(); // taskId -> task
const sessions = new Map(); // contextId -> agent session id
const children = new Map(); // taskId -> child process
let queue = Promise.resolve();

const server = http.createServer(async (req, res) => {
  try {
    if (req.method === 'GET' && (req.url === '/.well-known/agent-card.json' || req.url === '/.well-known/agent.json')) {
      return json(res, 200, card);
    }
    if (req.method === 'GET' && req.url === '/health') return json(res, 200, { ok: true, agent: AGENT, queued: [...tasks.values()].filter((t) => !done(t)).length });
    if (req.method !== 'POST') return json(res, 404, { error: 'not found' });
    if (!authorised(req)) {
      log({ event: 'unauthorised', from: req.socket.remoteAddress });
      return json(res, 401, { error: 'unauthorised' });
    }
    const body = JSON.parse(await read(req));
    const { id, method, params } = body;
    const reply = (result) => json(res, 200, { jsonrpc: '2.0', id, result });
    const fail = (code, message) => json(res, 200, { jsonrpc: '2.0', id, error: { code, message } });

    if (method === 'message/send') {
      const msg = params?.message;
      const text = (msg?.parts || []).filter((p) => (p.kind ?? p.type) === 'text').map((p) => p.text).join('\n').trim();
      if (!text) return fail(-32602, 'message has no text part');
      const task = newTask(msg.contextId, msg);
      log({ event: 'message', task: task.id, context: task.contextId, from: req.socket.remoteAddress, text });
      const run = enqueue(task, text);
      if (params?.configuration?.blocking === false) return reply(task);
      await run;
      return reply(task);
    }
    if (method === 'tasks/get') {
      const t = tasks.get(params?.id);
      return t ? reply(t) : fail(-32001, 'task not found');
    }
    if (method === 'tasks/cancel') {
      const t = tasks.get(params?.id);
      if (!t) return fail(-32001, 'task not found');
      if (done(t)) return fail(-32002, 'task is not cancelable');
      children.get(t.id)?.kill('SIGTERM');
      setState(t, 'canceled', 'Canceled by caller.');
      return reply(t);
    }
    return fail(-32601, `method not supported: ${method}`);
  } catch (e) {
    json(res, 200, { jsonrpc: '2.0', id: null, error: { code: -32700, message: String(e?.message ?? e) } });
  }
});

server.listen(PORT, HOST, () => {
  console.log(`A2A ${AGENT} agent "${NAME}" on http://${HOST}:${PORT}/  (workdir ${WORKDIR})`);
  console.log(`Agent card: ${PUBLIC_URL.replace(/\/$/, '')}/.well-known/agent-card.json`);
  console.log('ALL permission checks are off for incoming tasks. Ctrl-C to stop.');
});

function newTask(contextId, msg) {
  const t = {
    kind: 'task',
    id: crypto.randomUUID(),
    contextId: contextId || crypto.randomUUID(),
    status: { state: 'submitted', timestamp: new Date().toISOString() },
    history: [{ ...msg, kind: 'message' }],
    artifacts: [],
  };
  tasks.set(t.id, t);
  return t;
}

function enqueue(task, text) {
  const run = queue.then(() => (done(task) ? null : execute(task, text)));
  queue = run.catch(() => {});
  return run;
}

async function execute(task, text) {
  setState(task, 'working');
  const prev = sessions.get(task.contextId);
  const started = Date.now();
  try {
    const { reply, sessionId } = AGENT === 'claude' ? await runClaude(task, text, prev) : await runCodex(task, text, prev);
    if (done(task)) return; // canceled meanwhile
    if (sessionId) sessions.set(task.contextId, sessionId);
    task.artifacts = [{ artifactId: crypto.randomUUID(), name: 'reply', parts: [{ kind: 'text', text: reply }] }];
    setState(task, 'completed', reply);
    log({ event: 'completed', task: task.id, seconds: Math.round((Date.now() - started) / 1000), chars: reply.length });
  } catch (e) {
    if (done(task)) return;
    setState(task, 'failed', String(e?.message ?? e));
    log({ event: 'failed', task: task.id, error: String(e?.message ?? e) });
  }
}

function runClaude(task, text, prev) {
  const args = ['-p', text, '--output-format', 'json', '--dangerously-skip-permissions', '--append-system-prompt', PREAMBLE];
  if (prev) args.push('--resume', prev);
  return spawnAgent(task, 'claude', args).then(({ stdout }) => {
    const out = JSON.parse(stdout.trim().split('\n').pop());
    if (out.is_error) throw new Error(out.result || 'claude reported an error');
    return { reply: out.result ?? '', sessionId: out.session_id };
  });
}

function runCodex(task, text, prev) {
  const last = path.join(os.tmpdir(), `a2a-${task.id}.txt`);
  const common = ['--json', '--dangerously-bypass-approvals-and-sandbox', '--skip-git-repo-check', '-o', last];
  const prompt = `${PREAMBLE}\n\n${text}`;
  // The prompt goes in on stdin ("-"), so no caller text is ever on the command line; that
  // keeps the Windows path (codex is a .cmd there, which needs a shell) free of quoting issues.
  const args = prev ? ['exec', 'resume', ...common, prev, '-'] : ['exec', ...common, '-C', WORKDIR, '-'];
  return spawnAgent(task, 'codex', args, prompt).then(({ stdout }) => {
    let sessionId = prev;
    for (const line of stdout.split('\n')) {
      try {
        const ev = JSON.parse(line);
        sessionId = ev.thread_id || ev.session_id || ev.msg?.session_id || sessionId;
      } catch {}
    }
    const reply = fs.existsSync(last) ? fs.readFileSync(last, 'utf8').trim() : '';
    fs.rmSync(last, { force: true });
    return { reply, sessionId };
  });
}

function spawnAgent(task, cmd, args, stdin) {
  return new Promise((resolve, reject) => {
    const win = process.platform === 'win32';
    if (win) args = args.map((a) => (/[\s"]/.test(a) ? `"${a.replace(/"/g, '\\"')}"` : a));
    const child = spawn(cmd, args, { cwd: WORKDIR, env: process.env, shell: win, stdio: [stdin === undefined ? 'ignore' : 'pipe', 'pipe', 'pipe'] });
    if (stdin !== undefined) child.stdin.end(stdin);
    children.set(task.id, child);
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (d) => (stdout += d));
    child.stderr.on('data', (d) => (stderr += d));
    const timer = setTimeout(() => child.kill('SIGTERM'), RUN_TIMEOUT_MS);
    child.on('error', reject);
    child.on('close', (code) => {
      clearTimeout(timer);
      children.delete(task.id);
      if (code === 0) resolve({ stdout });
      else reject(new Error(`${cmd} exited ${code}: ${(stderr || stdout).slice(-800)}`));
    });
  });
}

function setState(task, state, text) {
  task.status = { state, timestamp: new Date().toISOString() };
  if (text) {
    const m = { kind: 'message', role: 'agent', messageId: crypto.randomUUID(), taskId: task.id, contextId: task.contextId, parts: [{ kind: 'text', text }] };
    task.status.message = m;
    task.history.push(m);
  }
}

function done(t) {
  return ['completed', 'failed', 'canceled', 'rejected'].includes(t.status.state);
}

function authorised(req) {
  const got = Buffer.from((req.headers.authorization || '').replace(/^Bearer\s+/i, ''));
  const want = Buffer.from(TOKEN);
  return got.length === want.length && crypto.timingSafeEqual(got, want);
}

function read(req) {
  return new Promise((resolve, reject) => {
    let s = '';
    req.on('data', (d) => {
      s += d;
      if (s.length > 1_000_000) req.destroy(new Error('body too large'));
    });
    req.on('end', () => resolve(s));
    req.on('error', reject);
  });
}

function json(res, code, obj) {
  res.writeHead(code, { 'content-type': 'application/json' });
  res.end(JSON.stringify(obj));
}

function log(entry) {
  fs.appendFileSync(path.join(LOG_DIR, 'log.jsonl'), JSON.stringify({ t: new Date().toISOString(), ...entry }) + '\n');
}

function loadEnv(file) {
  if (!fs.existsSync(file)) return;
  for (const line of fs.readFileSync(file, 'utf8').split('\n')) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
    if (m && process.env[m[1]] === undefined) process.env[m[1]] = m[2].replace(/^['"]|['"]$/g, '');
  }
}
