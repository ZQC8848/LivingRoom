const fs=require('node:fs/promises');
const path=require('node:path');
const {chromium}=require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
(async()=>{
 const url=process.argv[2]||'http://127.0.0.1:5183/review/';
 const out=path.resolve('deployment/review',process.argv[3]||'review-r3');await fs.mkdir(out,{recursive:true});
 const b=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--autoplay-policy=no-user-gesture-required']});
 const p=await b.newPage({viewport:{width:1440,height:1100}});const errors=[];p.on('pageerror',e=>errors.push(e.message));
 try{
  await p.goto(url);await p.waitForFunction(()=>{const v=document.getElementById('video');return v.videoWidth===1776&&v.currentTime>.5});
  const report={url,options:await p.locator('#region option').count(),initial:await p.locator('#video').evaluate(v=>({w:v.videoWidth,h:v.videoHeight,d:v.duration,blob:v.currentSrc.startsWith('blob:')})),errors};
  await p.selectOption('#region','G07');await p.waitForTimeout(200);report.selected=await p.locator('#detail').textContent();
  await p.locator('#play').click();report.paused=await p.locator('#video').evaluate(v=>v.paused);
  await p.locator('#seek').fill('4.983');await p.waitForTimeout(300);report.seek=await p.locator('#video').evaluate(v=>v.currentTime);
  await p.selectOption('#rate','0.5');report.rate=await p.locator('#video').evaluate(v=>v.playbackRate);
  await p.screenshot({path:path.join(out,'review-birds.png'),fullPage:true});
  await p.selectOption('#region','');await p.screenshot({path:path.join(out,'review-full.png'),fullPage:true});
  await p.setViewportSize({width:390,height:844});report.mobile=await p.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth}));
  report.pass=report.options===52&&report.initial.w===1776&&report.initial.h===1776&&report.initial.d===8&&report.initial.blob&&report.paused&&Math.abs(report.seek-5)<.1&&report.rate===.5&&report.selected.includes('G07')&&report.mobile.width===report.mobile.scrollWidth&&!errors.length;
  await fs.writeFile(path.join(out,'review-verification.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));if(!report.pass)process.exitCode=2;
 }finally{await b.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
