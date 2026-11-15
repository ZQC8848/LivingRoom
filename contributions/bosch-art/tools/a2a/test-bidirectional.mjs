// Explicitly requested bidirectional test: no project edits or credential exchange.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const env=Object.fromEntries(fs.readFileSync(path.join(root,'.env'),'utf8').split(/\r?\n/).filter(l=>l.includes('=')&&!l.trimStart().startsWith('#')).map(l=>{const i=l.indexOf('=');return [l.slice(0,i).trim(),l.slice(i+1).trim().replace(/^['"]|['"]$/g,'')];}));
const nonce='a2a-'+crypto.randomBytes(8).toString('hex');
const peer=env.A2A_PEER_URL.replace(/\/?$/,'/'),local=`http://127.0.0.1:${env.A2A_PORT||41241}/`;
const report={startedAt:new Date().toISOString(),nonce,peerUrl:peer,localPublicUrl:env.A2A_PUBLIC_URL,checks:{},scope:'connection test only; no project edits, secret sharing, or permission changes'};
const scrub=value=>{let t=String(value??'');for(const k of [env.A2A_TOKEN,env.A2A_PEER_TOKEN])if(k)t=t.split(k).join('[REDACTED]');return t;};
async function rpc(url,token,method,params){const r=await fetch(url,{method:'POST',headers:{'content-type':'application/json',authorization:`Bearer ${token}`},body:JSON.stringify({jsonrpc:'2.0',id:crypto.randomUUID(),method,params}),signal:AbortSignal.timeout(15000)});if(!r.ok)throw Error('HTTP '+r.status);const b=await r.json();if(b.error)throw Error(b.error.message);return b.result;}
async function task(url,token,text,contextId){
 const start=Date.now();let t=await rpc(url,token,'message/send',{message:{kind:'message',role:'user',messageId:crypto.randomUUID(),...(contextId?{contextId}:{}),parts:[{kind:'text',text}]},configuration:{blocking:false}});
 let last='';
 while(!['completed','failed','canceled','rejected'].includes(t.status.state)){
  if(t.status.state!==last){console.log(JSON.stringify({task:t.id,state:t.status.state,side:url===peer?'peer':'local'}));last=t.status.state;}
  if(Date.now()-start>180000){await rpc(url,token,'tasks/cancel',{id:t.id});throw Error('Own connection-test task timed out and was canceled.');}
  await new Promise(resolve=>setTimeout(resolve,1500));t=await rpc(url,token,'tasks/get',{id:t.id});
 }
 const reply=(t.artifacts?.[0]?.parts||t.status.message?.parts||[]).map(p=>p.text||'').join('\n');
 return {taskId:t.id,contextId:t.contextId,state:t.status.state,reply:scrub(reply),elapsedSeconds:Math.round((Date.now()-start)/1000)};
}
try{
 report.forward=await task(peer,env.A2A_PEER_TOKEN,`Zoe's user explicitly requested a two-way A2A communication check. This is its first, outbound half. Reply with exactly A2A_FORWARD_OK:${nonce}. Do not run tools, change files, read secrets, or send another message yet.`);
 report.checks.localToPeer=report.forward.state==='completed'&&report.forward.reply.trim()===`A2A_FORWARD_OK:${nonce}`;
 if(!report.checks.localToPeer)throw Error('Peer did not return the outbound challenge correctly.');
 const callbackText=`Two-way A2A callback from Qin for nonce ${nonce}. Reply with exactly A2A_CALLBACK_OK:${nonce}. Do not run tools, read files, modify files, or send another message.`;
 report.peerCallbackRequest=await task(peer,env.A2A_PEER_TOKEN,
   `Second half of the user-requested A2A check, nonce ${nonce}. Please make ONE actual callback to Zoe's A2A server at ${env.A2A_PUBLIC_URL} using your EXISTING A2A_PEER_URL and A2A_PEER_TOKEN and the supplied send.mjs client (or the same JSON-RPC protocol). Send this exact text: ${JSON.stringify(callbackText)}. Poll the callback until completed (up to 90 seconds), then report its task ID, context ID, state, and exact returned text. Keep tokens private. Do not modify files, change permissions, restart services, or try to bypass any restriction. If the existing token is missing or the call fails, report the error instead of guessing or changing configuration. Do not ask Zoe's receiver to make another callback.`,report.forward.contextId);
 const entries=fs.readFileSync(path.join(root,'.a2a/log.jsonl'),'utf8').trim().split('\n').map(l=>{try{return JSON.parse(l)}catch{return null}}).filter(Boolean);
 const inbound=entries.findLast(e=>e.event==='message'&&e.t>=report.startedAt&&e.text===callbackText);
 report.checks.peerToLocal=Boolean(inbound);
 if(inbound){
  const t=await rpc(local,env.A2A_TOKEN,'tasks/get',{id:inbound.task});
  const reply=(t.artifacts?.[0]?.parts||[]).map(p=>p.text||'').join('\n');
  report.callback={taskId:t.id,contextId:t.contextId,state:t.status.state,reply:scrub(reply),receivedAt:inbound.t};
  report.checks.callbackReply=t.status.state==='completed'&&reply.trim()===`A2A_CALLBACK_OK:${nonce}`;
 }else report.checks.callbackReply=false;
 report.messageTransportPassed=Object.values(report.checks).every(Boolean);
 // This separate, read-only command probe does not contact the peer. It verifies
 // whether this background Codex receiver can actually launch its shell tools.
 report.localCommandProbe=await task(local,env.A2A_TOKEN,'The user is checking A2A. Run the read-only shell command node --version exactly once and report its output. Do not read files, change files or settings, send messages, or retry through another permission mode. If the tool fails, report the exact error; do not bypass it.');
 report.localCommandExecutionPassed=report.localCommandProbe.state==='completed'&&/\bv\d+\.\d+\.\d+\b/.test(report.localCommandProbe.reply)&&!/sandbox failed|requires an installed app|could not run|unable to run|cannot run/i.test(report.localCommandProbe.reply);
}catch(error){report.error=scrub(error.message||error);report.messageTransportPassed=false;process.exitCode=1;}
finally{report.finishedAt=new Date().toISOString();fs.writeFileSync(path.join(root,'.a2a/bidirectional-verification.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));if(!report.messageTransportPassed)process.exitCode=1;}
