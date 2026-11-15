// Prepare a private, ignored config for the teammate. Never print its token.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const env=Object.fromEntries(fs.readFileSync(path.join(root,'.env'),'utf8').split(/\r?\n/).filter(l=>l.includes('=')&&!l.trimStart().startsWith('#')).map(l=>{const i=l.indexOf('=');return [l.slice(0,i).trim(),l.slice(i+1).trim().replace(/^['"]|['"]$/g,'')];}));
const target=path.join(root,'.a2a/share-with-teammate.env');
const content='# Private connection settings for the teammate to add to THEIR .env\n'+`A2A_PEER_URL=${env.A2A_PUBLIC_URL}\nA2A_PEER_TOKEN=${env.A2A_TOKEN}\n`;
fs.writeFileSync(target,content,{mode:0o600});
console.log(JSON.stringify({privateShareFile:target,peerUrl:env.A2A_PEER_URL,peerTokenConfigured:Boolean(env.A2A_PEER_TOKEN),tokenPrinted:false}));
