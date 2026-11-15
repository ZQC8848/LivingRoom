// Import the OTHER machine's identity as our peer, preserving our own token.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
function parse(text){return Object.fromEntries(text.replace(/^\uFEFF/,'').split(/\r?\n/).filter(l=>l.includes('=')&&!l.trimStart().startsWith('#')).map(l=>{const i=l.indexOf('=');return [l.slice(0,i).trim(),l.slice(i+1).trim().replace(/^['"]|['"]$/g,'')];}));}
if(!process.argv[2])throw Error('Provide the teammate configuration file path.');
const source=path.resolve(process.argv[2]),peer=parse(fs.readFileSync(source,'utf8'));
const envFile=path.join(root,'.env');let text=fs.readFileSync(envFile,'utf8');const own=parse(text);
const url=new URL(peer.A2A_PUBLIC_URL||own.A2A_PEER_URL);
if(url.href===new URL(own.A2A_PUBLIC_URL).href)throw Error('The supplied file describes this machine, not the peer.');
if(!peer.A2A_TOKEN||peer.A2A_TOKEN.length<24||/[\r\n]/.test(peer.A2A_TOKEN))throw Error('Peer A2A_TOKEN is missing or invalid.');
for(const [name,value]of Object.entries({A2A_PEER_URL:url.href,A2A_PEER_TOKEN:peer.A2A_TOKEN})){
 const lines=text.split(/\r?\n/);let found=false;
 text=lines.map(line=>{if(line.startsWith(name+'=')){found=true;return name+'='+value;}return line;}).join('\n');
 if(!found)text+=(text.endsWith('\n')?'':'\n')+name+'='+value+'\n';
}
const updated=parse(text);
if(updated.A2A_TOKEN!==own.A2A_TOKEN)throw Error('Local token must not change.');
fs.writeFileSync(envFile,text,{mode:0o600});
const metadata={importedAt:new Date().toISOString(),peerName:peer.A2A_NAME||null,peerUrl:url.href,localTokenPreserved:true,onlyA2AFieldsImported:true,providedPeerFileHasReturnToken:Boolean(peer.A2A_PEER_TOKEN)};
fs.writeFileSync(path.join(root,'.a2a/peer-config.json'),JSON.stringify(metadata,null,2));
console.log(JSON.stringify(metadata));
