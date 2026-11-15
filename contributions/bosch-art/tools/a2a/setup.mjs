import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const file=path.join(root,'.env');
let text=fs.existsSync(file)?fs.readFileSync(file,'utf8'):'';
const existing=new Set([...text.matchAll(/^\s*([A-Z0-9_]+)\s*=/gm)].map(m=>m[1]));
const defaults={
 A2A_AGENT:'codex',A2A_HOST:'127.0.0.1',A2A_PORT:'41241',A2A_WORKDIR:root.replaceAll('\\','/'),
 A2A_NAME:'immerse-the-bay-zoezi-codex',A2A_TOKEN:crypto.randomBytes(24).toString('hex'),
 A2A_PUBLIC_URL:'http://win-tqcecsev19k.tail5a410a.ts.net:41241/',
 A2A_PEER_URL:'http://qinchuans-macbook-pro.tail5a410a.ts.net:41241/',A2A_PEER_TOKEN:'',A2A_RUN_TIMEOUT_MIN:'30'
};
const added=[];
for(const [k,v]of Object.entries(defaults))if(!existing.has(k)){text+=(text&&!text.endsWith('\n')?'\n':'')+`${k}=${v}\n`;added.push(k);}
fs.writeFileSync(file,text,{mode:0o600});
const ignore=path.join(root,'.gitignore');
let rules=fs.existsSync(ignore)?fs.readFileSync(ignore,'utf8'):'';
for(const rule of ['/.env','/.a2a/'])if(!rules.split(/\r?\n/).includes(rule))rules+=(rules&&!rules.endsWith('\n')?'\n':'')+rule+'\n';
fs.writeFileSync(ignore,rules);
fs.mkdirSync(path.join(root,'.a2a'),{recursive:true});
console.log(JSON.stringify({configured:file,added,tokenPrinted:false}));
