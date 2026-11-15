import fs from 'node:fs';
for (const line of fs.readFileSync(new URL('../../.env', import.meta.url),'utf8').split('\n')) {
  const m=line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$/);
  if(m && process.env[m[1]]===undefined) process.env[m[1]]=m[2].replace(/^['"]|['"]$/g,'');
}
const r=await fetch(process.env.A2A_PEER_URL,{method:'POST',headers:{'content-type':'application/json',authorization:`Bearer ${process.env.A2A_PEER_TOKEN}`},body:JSON.stringify({jsonrpc:'2.0',id:1,method:'tasks/get',params:{id:'e0de2dc7-4c07-4af1-86d4-fa4785085620'}}),signal:AbortSignal.timeout(15000)});
const b=await r.json(); const t=b.result;
console.log(JSON.stringify(t ? {state:t.status,artifacts:t.artifacts} : b.error,null,2));
