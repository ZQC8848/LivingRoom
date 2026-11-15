import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
for(const file of [path.join(root,'.env'),...(process.env.BOSCH_ENV_FILE?[path.resolve(process.env.BOSCH_ENV_FILE)]:[])])if(fs.existsSync(file))for(const line of fs.readFileSync(file,'utf8').split('\n')){const m=line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$/);if(m&&!process.env[m[1]])process.env[m[1]]=m[2].replace(/^['"]|['"]$/g,'');}
const key=process.env.REACTOR_API_KEY;if(!key)throw Error('Missing server-side Reactor credential');
const port=41243,model='reactor/visko-orbis-dynamic',seconds=180;
const liveConfig=JSON.parse(fs.readFileSync(path.join(root,'deployment/bosch-demo/public/live-config.json')));
const permittedHosts=new Set(['127.0.0.1:'+port,'localhost:'+port,new URL(liveConfig.broker).host]);
const privateDir=path.join(root,'.a2a');fs.mkdirSync(privateDir,{recursive:true});
const operatorFile=path.join(privateDir,'live-operator.json');
const operator=fs.existsSync(operatorFile)?JSON.parse(fs.readFileSync(operatorFile)): {code:crypto.randomBytes(8).toString('hex'),created_at:new Date().toISOString()};
fs.writeFileSync(operatorFile,JSON.stringify(operator,null,2));
const budgetFile=path.join(privateDir,'live-budget.json');let budget=fs.existsSync(budgetFile)?JSON.parse(fs.readFileSync(budgetFile)):{};
let lease=null,issuing=false;const failures=new Map();
function json(res,status,data,origin){res.writeHead(status,{'content-type':'application/json','cache-control':'no-store','access-control-allow-origin':origin||'null','vary':'Origin','x-content-type-options':'nosniff'});res.end(JSON.stringify(data));}
function allowed(origin){return origin==='https://livingroom-bosch-demo.sandy-toad-8179.chatgpt.site'||/^http:\/\/(127\.0\.0\.1|localhost):518[23]$/.test(origin||'');}
function same(a,b){const x=Buffer.from(a||''),y=Buffer.from(b);return x.length===y.length&&crypto.timingSafeEqual(x,y);}
async function body(req){let text='';for await(const c of req){text+=c;if(text.length>2048)throw Error('Request too large');}return text?JSON.parse(text):{};}
async function end(active,reason){if(!active||active.ending)return;active.ending=true;try{if(active.sessionId)await fetch('https://api.reactor.inc/sessions/'+encodeURIComponent(active.sessionId),{method:'DELETE',headers:{authorization:'Bearer '+key,'content-type':'application/json'},body:JSON.stringify({reason}),signal:AbortSignal.timeout(12000)});}catch{}finally{if(lease===active)lease=null;}}
const server=http.createServer(async(req,res)=>{const origin=req.headers.origin,url=new URL(req.url,'http://localhost');
 try{
  if(!permittedHosts.has(req.headers.host)){json(res,403,{error:'Host not allowed'});return;}
  if(url.pathname==='/operator'&&['127.0.0.1:'+port,'localhost:'+port].includes(req.headers.host)){
   let config={};try{config=JSON.parse(fs.readFileSync(path.join(root,'deployment/bosch-demo/public/live-config.json')))}catch{}
   const target='https://livingroom-bosch-demo.sandy-toad-8179.chatgpt.site/?experience=live#code='+operator.code;
   res.writeHead(200,{'content-type':'text/html','cache-control':'no-store'});res.end('<!doctype html><meta name="referrer" content="no-referrer"><title>Live operator</title><body style="font:20px system-ui;max-width:700px;margin:50px auto"><h1>Private live operator entry</h1><p>Keep this page private. The public stable experience never needs this code.</p><p><a href="'+target+'">Open the live experience, already unlocked</a></p><p>For Quest, open the public Live page and enter:</p><input readonly value="'+operator.code+'" style="font:24px monospace;width:100%"><p>Broker: '+(config.broker||'not configured')+'</p><p>One owned Orbis session at a time; 180 seconds maximum. Stop releases only that session. This machine and HTTPS tunnel must remain running.</p>');return;
  }
  if(origin&&!allowed(origin)){json(res,403,{error:'Origin not allowed'});return;}
  if(req.method==='OPTIONS'){res.writeHead(204,{'access-control-allow-origin':origin||'null','access-control-allow-methods':'GET,POST,OPTIONS','access-control-allow-headers':'content-type,x-live-code','access-control-max-age':'600','vary':'Origin'});res.end();return;}
  if(req.method==='GET'&&url.pathname==='/health'){json(res,200,{service:'Bosch live operator broker',model,max_session_seconds:seconds,active:!!lease,runtime_generation:true},origin);return;}
  const ip=req.headers['cf-connecting-ip']||req.socket.remoteAddress,now=Date.now(),f=failures.get(ip)||{count:0,until:0};
  if(f.until>now){json(res,429,{error:'Wait before retrying the operator code'},origin);return;}
  if(!same(req.headers['x-live-code'],operator.code)){f.count++;if(f.count>=8){f.until=now+60000;f.count=0;}failures.set(ip,f);json(res,401,{error:'Enter the private operator code'},origin);return;}
  if(req.method==='POST'&&url.pathname==='/v1/lease'){
   if(lease||issuing){json(res,409,{error:'A live operator session is already reserved. Stop it or wait for its three-minute limit.'},origin);return;}
   const day=new Date().toISOString().slice(0,10);if(budget.day!==day)budget={day,issued:0};if(budget.issued>=15){json(res,429,{error:'Today’s bounded demo session budget is exhausted'},origin);return;}
   issuing=true;try{
    const upstream=await fetch('https://api.reactor.inc/tokens',{method:'POST',headers:{'Reactor-API-Key':key,'content-type':'application/json'},body:JSON.stringify({expires_after:90,authorization_details:[{type:'session',resources:{models:{match:[model]}},constraints:{max_sessions:1,max_session_duration_seconds:seconds}}]}),signal:AbortSignal.timeout(20000)});
    if(!upstream.ok){json(res,502,{error:'Sponsor token service returned '+upstream.status},origin);return;}const token=await upstream.json();
    lease={id:crypto.randomUUID(),jwt:token.jwt,sessionId:null,created:Date.now(),seen:Date.now()};budget.issued++;fs.writeFileSync(budgetFile,JSON.stringify(budget));
    const current=lease;setTimeout(()=>end(current,'Bounded Bosch live demo timeout'),(seconds+95)*1000).unref();
    json(res,200,{jwt:token.jwt,lease_id:lease.id,model,max_session_seconds:seconds,expires_after:90},origin);
   }finally{issuing=false;}return;
  }
  const match=url.pathname.match(/^\/v1\/lease\/([a-f0-9-]+)\/(register|stop|heartbeat)$/);
  if(req.method==='POST'&&match){if(!lease||lease.id!==match[1]){json(res,match[2]==='stop'?200:404,match[2]==='stop'?{stopped:true}:{error:'Live lease has ended'},origin);return;}const active=lease;
   if(match[2]==='heartbeat'){active.seen=Date.now();json(res,200,{alive:true},origin);return;}
   if(match[2]==='stop'){await end(active,'Operator stopped Bosch live demo');json(res,200,{stopped:true},origin);return;}
   const data=await body(req);if(active.sessionId||!/^[-a-f0-9]{36}$/i.test(data.session_id||'')){json(res,400,{error:'Invalid session registration'},origin);return;}
   const check=await fetch('https://api.reactor.inc/sessions/'+data.session_id,{headers:{authorization:'Bearer '+active.jwt},signal:AbortSignal.timeout(12000)});
   if(!check.ok){json(res,403,{error:'Session is not owned by this lease'},origin);return;}
   const session=await check.json();if(session.model_name&&session.model_name!==model){json(res,403,{error:'Unexpected session model'},origin);return;}
   active.sessionId=data.session_id;json(res,200,{registered:true,max_session_seconds:seconds},origin);return;
  }
  json(res,404,{error:'No such live operation'},origin);
 }catch{if(!res.headersSent)json(res,500,{error:'Live broker request failed'},origin);else res.end();}
});
server.listen(port,'127.0.0.1',()=>console.log('Operator broker ready on http://127.0.0.1:'+port+'/operator (no session started)'));
setInterval(()=>{if(lease?.sessionId&&Date.now()-lease.seen>45000)end(lease,'Live viewer heartbeat expired');},5000).unref();
for(const signal of ['SIGINT','SIGTERM'])process.on(signal,async()=>{await end(lease,'Live broker stopped');server.close(()=>process.exit(0));setTimeout(()=>process.exit(0),15000).unref();});
