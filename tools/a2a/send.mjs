#!/usr/bin/env node
// Send one message to a teammate's A2A agent and print its reply. Zero dependencies.
//
//   node tools/a2a/send.mjs "What changed in live.js today?"
//   node tools/a2a/send.mjs --context <contextId> "And the fallback?"   # continue a thread
//   node tools/a2a/send.mjs --card                                      # show the peer's agent card
//
// Config (environment, or the repo's .env):
//   A2A_PEER_URL    the teammate's server, e.g. https://their-mac.their-tailnet.ts.net:8443/
//   A2A_PEER_TOKEN  the token THEY generated for their server
// --url / --self override the URL (--self = this machine's own server, with A2A_TOKEN).
//
// The message is sent non-blocking and the task is polled, so a run of several minutes does
// not depend on one long-lived HTTP request. The reply goes to stdout; progress to stderr.

import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
loadEnv(path.join(ROOT, '.env'));

const args = process.argv.slice(2);
const take = (flag) => {
  const i = args.indexOf(flag);
  return i < 0 ? null : args.splice(i, 2)[1];
};
const has = (flag) => {
  const i = args.indexOf(flag);
  if (i >= 0) args.splice(i, 1);
  return i >= 0;
};
const self = has('--self');
const showCard = has('--card');
const contextId = take('--context');
const url = (take('--url') || (self ? `http://127.0.0.1:${process.env.A2A_PORT || 41241}/` : process.env.A2A_PEER_URL) || '').replace(/\/?$/, '/');
const token = self ? process.env.A2A_TOKEN : process.env.A2A_PEER_TOKEN;
const text = args.join(' ').trim();

if (url === '/') die('No peer URL. Set A2A_PEER_URL in .env or pass --url.');

if (showCard) {
  const r = await fetch(`${url}.well-known/agent-card.json`);
  console.log(JSON.stringify(await r.json(), null, 2));
  process.exit(0);
}
if (!token) die(`No token. Set ${self ? 'A2A_TOKEN' : 'A2A_PEER_TOKEN'} in .env.`);
if (!text) die('Usage: node tools/a2a/send.mjs [--context ID] "message"');

let task = await rpc('message/send', {
  message: { kind: 'message', role: 'user', messageId: crypto.randomUUID(), ...(contextId ? { contextId } : {}), parts: [{ kind: 'text', text }] },
  configuration: { blocking: false },
});
console.error(`task ${task.id}  context ${task.contextId}`);
const started = Date.now();
while (!['completed', 'failed', 'canceled', 'rejected'].includes(task.status.state)) {
  await new Promise((r) => setTimeout(r, 3000));
  task = await rpc('tasks/get', { id: task.id });
  process.stderr.write(`\r${task.status.state} ${Math.round((Date.now() - started) / 1000)}s `);
}
process.stderr.write('\n');
const reply = (task.artifacts?.[0]?.parts ?? task.status.message?.parts ?? []).map((p) => p.text).join('\n');
console.log(reply);
console.error(`\n[${task.status.state}] continue this thread with: --context ${task.contextId}`);
process.exit(task.status.state === 'completed' ? 0 : 2);

async function rpc(method, params) {
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'content-type': 'application/json', authorization: `Bearer ${token}` },
    body: JSON.stringify({ jsonrpc: '2.0', id: crypto.randomUUID(), method, params }),
  });
  if (r.status === 401) die('401: the peer rejected the token.');
  const body = await r.json();
  if (body.error) die(`${method}: ${body.error.message}`);
  return body.result;
}

function die(msg) {
  console.error(msg);
  process.exit(1);
}

function loadEnv(file) {
  if (!fs.existsSync(file)) return;
  for (const line of fs.readFileSync(file, 'utf8').split('\n')) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
    if (m && process.env[m[1]] === undefined) process.env[m[1]] = m[2].replace(/^['"]|['"]$/g, '');
  }
}
