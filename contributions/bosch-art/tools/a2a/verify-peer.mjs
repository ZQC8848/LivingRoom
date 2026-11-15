// Verify transport and bearer auth without message/send or remote agent execution.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const env=Object.fromEntries(fs.readFileSync(path.join(root,'.env'),'utf8').split(/\r?\n/).filter(l=>l.includes('=')&&!l.trimStart().startsWith('#')).map(l=>{const i=l.indexOf('=');return [l.slice(0,i).trim(),l.slice(i+1).trim().replace(/^['"]|['"]$/g,'')];}));
const base=env.A2A_PEER_URL.replace(/\/?$/,'/');
if(!env.A2A_PEER_TOKEN)throw Error('A2A_PEER_TOKEN is missing.');
const report={checkedAt:new Date().toISOString(),peerUrl:base,checks:{},remoteTaskSubmitted:false};
async function get(suffix){const r=await fetch(base+suffix,{signal:AbortSignal.timeout(12000)});if(!r.ok)throw Error(`HTTP ${r.status}`);return r.json();}
async function lookup(token){const r=await fetch(base,{method:'POST',headers:{'content-type':'application/json',authorization:`Bearer ${token}`},body:JSON.stringify({jsonrpc:'2.0',id:crypto.randomUUID(),method:'tasks/get',params:{id:'a2a-auth-check-'+crypto.randomUUID()}}),signal:AbortSignal.timeout(12000)});return {status:r.status,body:await r.json()};}
try{
 const card=await get('.well-known/agent-card.json');report.peerName=card.name;report.checks.agentCard=card.protocolVersion==='0.3.0';
 const health=await get('health');report.checks.health=health.ok===true;
 const bad=await lookup('invalid-a2a-configuration-test');report.checks.rejectsWrongToken=bad.status===401;
 const good=await lookup(env.A2A_PEER_TOKEN);report.checks.validTokenAccepted=good.status===200&&good.body.error?.code===-32001;
 report.success=Object.values(report.checks).every(Boolean);
 if(!report.success){report.error='Authentication or transport check failed.';process.exitCode=1;}
}catch(error){report.success=false;report.error=String(error.message||error).split(env.A2A_PEER_TOKEN).join('[REDACTED]');process.exitCode=1;}
finally{fs.writeFileSync(path.join(root,'.a2a/peer-verification.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));}
