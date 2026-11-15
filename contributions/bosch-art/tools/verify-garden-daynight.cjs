const fs=require('node:fs/promises'),path=require('node:path');
const {chromium}=require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
(async()=>{
 const out=path.resolve('handoff/garden-daynight-20261114/qa');await fs.mkdir(out,{recursive:true});
 const b=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const p=await b.newPage({viewport:{width:1280,height:900}}),errors=[],api=[];
 p.on('pageerror',e=>errors.push(e.message));p.on('request',r=>{if(/reactor\.inc|elevenlabs|\/api\//.test(r.url()))api.push(r.url())});
 try{
  await p.goto('http://127.0.0.1:5191/');await p.waitForTimeout(500);if(errors.length)throw Error(errors.join('; '));await p.waitForFunction(()=>window.__daynight?.info.videoWidth===2048);
  const info=()=>p.evaluate(()=>window.__daynight.info);
  const r={initial:await info(),errors,api,headsetVerified:false};
  await p.locator('#play').click();await p.waitForTimeout(700);r.playing=!(await info()).paused;
  await p.locator('#play').click();await p.evaluate(()=>window.__daynight.seek(15));await p.waitForFunction(()=>Math.abs(document.getElementById('video').currentTime-15)<.1&&document.getElementById('video').readyState>=2);
  await p.waitForTimeout(250);r.night=await info();await p.screenshot({path:path.join(out,'night-inside.png'),fullPage:true});
  await p.evaluate(()=>window.__daynight.seek(0));await p.waitForTimeout(300);await p.screenshot({path:path.join(out,'day-inside.png'),fullPage:true});
  const c=p.locator('#canvas');await c.hover({position:{x:700,y:260}});await p.mouse.down();await p.mouse.move(450,350,{steps:8});await p.mouse.up();r.look=await info();await p.locator('#reset').click();r.center=await info();
  await p.locator('#painting').click();await p.waitForFunction(()=>window.__daynight.info.videoWidth===1776);r.painting=await info();await p.evaluate(()=>window.__daynight.seek(15));await p.waitForTimeout(300);await p.screenshot({path:path.join(out,'night-painting.png'),fullPage:true});
  await p.locator('#sound').check();await p.locator('#play').click();await p.waitForFunction(()=>{const a=document.getElementById('audio'),v=document.getElementById('video');return !a.paused&&a.readyState>=3&&a.currentTime>15&&Math.abs(a.currentTime-v.currentTime)<.4});r.sound=await p.locator('#audio').evaluate(a=>({paused:a.paused,readyState:a.readyState,currentTime:a.currentTime}));
  await p.locator('#sound').uncheck();r.muted=await p.locator('#audio').evaluate(a=>a.paused);
  await p.evaluate(()=>window.__daynight.seek(29.7));await p.waitForTimeout(1100);r.loop=await info();
  await p.setViewportSize({width:390,height:844});r.mobile=await p.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));await p.screenshot({path:path.join(out,'mobile.png'),fullPage:true});
  r.pass=r.initial.paused&&r.initial.live===false&&r.playing&&Math.abs(r.night.currentTime-15)<.1&&Math.abs(r.look.yaw)>.1&&r.center.yaw===0&&r.center.pitch===0&&r.painting.videoWidth===1776&&!r.sound.paused&&r.muted&&r.loop.playbackLoops>=1&&r.mobile.width===r.mobile.scroll&&!errors.length&&!api.length;
  await fs.writeFile(path.join(out,'browser-verification.json'),JSON.stringify(r,null,2));console.log(JSON.stringify(r,null,2));if(!r.pass)process.exitCode=2;
 }catch(e){const state=await p.evaluate(()=>({video:window.__daynight?.info,audio:{time:document.getElementById('audio').currentTime,paused:document.getElementById('audio').paused,ready:document.getElementById('audio').readyState,duration:document.getElementById('audio').duration}}));await fs.writeFile(path.join(out,'failure.json'),JSON.stringify({error:e.message,errors,state},null,2));await p.screenshot({path:path.join(out,'failure.png'),fullPage:true});throw e}finally{await b.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
