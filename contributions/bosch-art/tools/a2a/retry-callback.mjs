// One process-local environment retry for the explicit bidirectional check.
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const env=Object.fromEntries(fs.readFileSync(path.join(root,'.env'),'utf8').split(/\r?\n/).filter(l=>l.includes('=')&&!l.trimStart().startsWith('#')).map(l=>{const i=l.indexOf('=');return [l.slice(0,i).trim(),l.slice(i+1).trim().replace(/^['"]|['"]$/g,'')];}));
const file=path.join(root,'.a2a/bidirectional-verification.json'),report=JSON.parse(fs.readFileSync(file,'utf8'));
if(!report.peerCallbackRequest?.reply.includes('No token. Set A2A_PEER_TOKEN'))throw Error('This retry is only for the observed empty-env token condition.');
const peer=env.A2A_PEER_URL,local=`http://127.0.0.1:${env.A2A_PORT||41241}/`;
const scrub=v=>{let t=String(v??'');for(const k of [env.A2A_TOKEN,env.A2A_PEER_TOKEN])if(k)t=t.split(k).join('[REDACTED]');return t;};
async function rpc(url,token,method,params){const r=await fetch(url,{method:'POST',headers:{'content-type':'application/json',authorization:`Bearer ${token}`},body:JSON.stringify({jsonrpc:'2.0',id:crypto.randomUUID(),method,params}),signal:AbortSignal.timeout(15000)});if(!r.ok)throw Error('HTTP '+r.status);const b=await r.json();if(b.error)throw Error(b.error.message);return b.result;}
const text=`Two-way A2A callback from Qin for nonce ${report.nonce}. Reply with exactly A2A_CALLBACK_OK:${report.nonce}. Do not run tools, read files, modify files, or send another message.`;
const instruction=`Please retry the SAME user-requested bidirectional test once. The user has authorized this communication test, and using the existing configured credential is in scope. For THIS CLIENT PROCESS ONLY, remove the empty A2A_PEER_TOKEN environment override so the existing send.mjs can read the real value from your project's .env normally. On macOS, the bounded form is: env -u A2A_PEER_TOKEN node tools/a2a/send.mjs <message>. Keep every other environment variable unchanged. Send exactly this message to the existing peer URL ${env.A2A_PUBLIC_URL}: ${JSON.stringify(text)}. Poll it to completion up to 90 seconds, then report task ID, context ID and exact response. Do not modify files, persist environment changes, alter permissions, restart services, print credentials, or ask the receiver to call back again. If this still fails, report the actual error and stop.`;
try{
 let task=await rpc(peer,env.A2A_PEER_TOKEN,'message/send',{message:{kind:'message',role:'user',messageId:crypto.randomUUID(),contextId:report.forward.contextId,parts:[{kind:'text',text:instruction}]},configuration:{blocking:false}});
 const start=Date.now();let last='';
 while(!['completed','failed','canceled','rejected'].includes(task.status.state)){
  if(last!==task.status.state){console.log(JSON.stringify({task:task.id,state:task.status.state}));last=task.status.state;}
  if(Date.now()-start>150000){await rpc(peer,env.A2A_PEER_TOKEN,'tasks/cancel',{id:task.id});throw Error('Own callback retry timed out and was canceled.');}
  await new Promise(resolve=>setTimeout(resolve,1500));task=await rpc(peer,env.A2A_PEER_TOKEN,'tasks/get',{id:task.id});
 }
 const reply=(task.artifacts?.[0]?.parts||task.status.message?.parts||[]).map(p=>p.text||'').join('\n');
 report.callbackRetry={taskId:task.id,contextId:task.contextId,state:task.status.state,reply:scrub(reply),elapsedSeconds:Math.round((Date.now()-start)/1000),processLocalEnvCleanupOnly:true};
 const entries=fs.readFileSync(path.join(root,'.a2a/log.jsonl'),'utf8').trim().split('\n').map(l=>{try{return JSON.parse(l)}catch{return null}}).filter(Boolean);
 const entry=entries.findLast(e=>e.event==='message'&&e.t>=report.startedAt&&e.text===text);
 report.checks.peerToLocal=Boolean(entry);
 if(entry){const callback=await rpc(local,env.A2A_TOKEN,'tasks/get',{id:entry.task});const answer=(callback.artifacts?.[0]?.parts||[]).map(p=>p.text||'').join('\n');report.callback={taskId:callback.id,contextId:callback.contextId,state:callback.status.state,reply:scrub(answer),receivedAt:entry.t};report.checks.callbackReply=callback.status.state==='completed'&&answer.trim()===`A2A_CALLBACK_OK:${report.nonce}`;}
 report.messageTransportPassed=Object.values(report.checks).every(Boolean);
 report.defaultPeerClientEnvironmentPassed=false;
}catch(error){report.retryError=scrub(error.message||error);process.exitCode=1;}
finally{report.finishedAt=new Date().toISOString();fs.writeFileSync(file,JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));if(!report.messageTransportPassed)process.exitCode=1;}
