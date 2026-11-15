import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const env=Object.fromEntries(fs.readFileSync(path.join(root,'.env'),'utf8').split(/\r?\n/).filter(l=>l.includes('=')&&!l.trimStart().startsWith('#')).map(l=>{const i=l.indexOf('=');return [l.slice(0,i).trim(),l.slice(i+1).trim().replace(/^['"]|['"]$/g,'')];}));
const base=`http://127.0.0.1:${env.A2A_PORT||41241}/`;
const report={startedAt:new Date().toISOString(),target:'self only',checks:{}};
async function rpc(method,params,token=env.A2A_TOKEN){
 const response=await fetch(base,{method:'POST',headers:{'content-type':'application/json',...(token?{authorization:`Bearer ${token}`}:{})},body:JSON.stringify({jsonrpc:'2.0',id:crypto.randomUUID(),method,params}),signal:AbortSignal.timeout(15000)});
 return {status:response.status,body:await response.json()};
}
async function sendAndPoll(text,contextId){
 const initial=await rpc('message/send',{message:{kind:'message',role:'user',messageId:crypto.randomUUID(),...(contextId?{contextId}:{}),parts:[{kind:'text',text}]},configuration:{blocking:false}});
 if(initial.body.error)throw Error(initial.body.error.message);
 let task=initial.body.result;const start=Date.now();let previous='';
 while(!['completed','failed','canceled'].includes(task.status.state)){
  if(task.status.state!==previous){console.log(JSON.stringify({task:task.id,state:task.status.state}));previous=task.status.state;}
  if(Date.now()-start>150000){await rpc('tasks/cancel',{id:task.id});throw Error('Smoke test timed out; its own task was canceled.');}
  await new Promise(resolve=>setTimeout(resolve,1500));
  task=(await rpc('tasks/get',{id:task.id})).body.result;
 }
 const reply=(task.artifacts?.[0]?.parts||task.status.message?.parts||[]).map(p=>p.text||'').join('\n');
 if(task.status.state!=='completed')throw Error(reply);
 return {taskId:task.id,contextId:task.contextId,reply,elapsedSeconds:Math.round((Date.now()-start)/1000)};
}
try{
 const health=await fetch(base+'health',{signal:AbortSignal.timeout(5000)});
 report.checks.health=health.ok&&(await health.json()).ok;
 const card=await fetch(base+'.well-known/agent-card.json');report.card=await card.json();report.checks.card=card.ok&&report.card.protocolVersion==='0.3.0';
 report.checks.rejectsMissingToken=(await rpc('tasks/get',{id:'unknown'},'')).status===401;
 report.checks.rejectsWrongToken=(await rpc('tasks/get',{id:'unknown'},'invalid-test-token')).status===401;
 const lookup=await rpc('tasks/get',{id:'unknown'});report.checks.authenticatedLookup=lookup.status===200&&lookup.body.error?.code===-32001;
 console.log(JSON.stringify({protocolChecks:report.checks}));
 if(Object.values(report.checks).some(v=>!v))throw Error('Protocol or authentication check failed.');
 report.first=await sendAndPoll('This is a local A2A configuration test. Reply with exactly A2A_READY. Do not run tools, read files, or change anything.');
 report.checks.codexExecution=report.first.reply.trim()==='A2A_READY';
 report.resumed=await sendAndPoll('This is the follow-up for the same A2A configuration test. Reply with exactly A2A_RESUME_READY. Do not run tools or change anything.',report.first.contextId);
 report.checks.contextContinuation=report.resumed.contextId===report.first.contextId&&report.resumed.reply.trim()==='A2A_RESUME_READY';
 report.success=Object.values(report.checks).every(Boolean);
}catch(error){report.success=false;report.error=String(error.message||error);console.error(report.error);process.exitCode=1;}
finally{report.finishedAt=new Date().toISOString();fs.writeFileSync(path.join(root,'.a2a/verification.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));if(!report.success)process.exitCode=1;}
