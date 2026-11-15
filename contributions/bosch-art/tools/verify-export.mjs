import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const manifest=JSON.parse(fs.readFileSync(path.join(root,'FILES.sha256.json')));
let count=0,bytes=0,failures=[];
for(const file of manifest.files){
 const target=path.resolve(root,file.path);
 if(!target.startsWith(root+path.sep)){failures.push({path:file.path,error:'outside contribution'});continue;}
 try{const data=fs.readFileSync(target);if(data.subarray(0,100).toString().startsWith('version https://git-lfs.github.com/spec/v1'))throw Error('LFS pointer: run git lfs pull');
 const sha=crypto.createHash('sha256').update(data).digest('hex');if(data.length!==file.bytes||sha!==file.sha256)throw Error('size or SHA-256 mismatch');count++;bytes+=data.length;
 }catch(error){failures.push({path:file.path,error:error.message});}
}
console.log(JSON.stringify({verified_files:count,verified_bytes:bytes,failures},null,2));
process.exitCode=failures.length?1:0;
