const fs=require('node:fs/promises'),path=require('node:path');
const {chromium}=require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
(async()=>{
 const base=process.argv[2]||'http://127.0.0.1:5183/';const out=path.resolve('deployment/review',process.argv[3]||'sound-local-r4');await fs.mkdir(out,{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const p=await browser.newPage({viewport:{width:1280,height:900}});const errors=[],requests=[];p.on('pageerror',e=>errors.push(e.message));p.on('request',r=>requests.push(r.url()));
 const read=()=>p.evaluate(()=>window.__sound.diagnostics());const report={url:base,headsetVerified:false,scope:'Real static MP3s decoded and played through Web Audio in Chrome; headset acoustics and comfort are not evaluated.'};
 try{
  await p.goto(base);await p.waitForFunction(()=>window.__sound&&window.__reveal?.info.playing);
  report.before=await read();report.audioRequestsBeforeOptIn=requests.filter(x=>/\.mp3/.test(x)).length;
  await p.getByRole('button',{name:'Enable sound',exact:true}).click();await p.waitForFunction(()=>window.__sound?.info.enabled&&window.__sound.info.ready);await p.waitForTimeout(700);
  report.garden=await read();report.caption=await p.locator('.sound-caption').textContent();
  await p.locator('canvas').first().click({position:{x:640,y:450}});await p.waitForTimeout(1100);report.hidden=await read();
  await p.locator('canvas').first().click({position:{x:640,y:450}});await p.waitForTimeout(850);report.returned=await read();
  await p.waitForFunction(()=>window.__sound.info.completed.length===3,{timeout:25000});
  report.completed=await read();await p.waitForTimeout(2500);report.afterAnotherLoop=await read();
  await p.getByRole('button',{name:'Mute',exact:true}).click();await p.waitForTimeout(500);report.muted=await read();
  await p.getByRole('button',{name:'Enable sound',exact:true}).click();await p.waitForTimeout(400);report.resumed=await read();
  await p.getByRole('checkbox',{name:'Voice',exact:true}).uncheck();report.voiceOff=await read();
  await p.getByRole('checkbox',{name:'Voice',exact:true}).check();await p.getByRole('button',{name:'Replay voice',exact:true}).click();await p.waitForTimeout(300);report.replay=await read();
  await p.getByRole('checkbox',{name:'Captions',exact:true}).uncheck();report.captionOff=await p.locator('.sound-caption').textContent();
  await p.screenshot({path:path.join(out,'sound-controls.png')});
  await p.setViewportSize({width:390,height:844});report.mobile=await p.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,panel:document.querySelector('.sound-panel').getBoundingClientRect().toJSON()}));await p.screenshot({path:path.join(out,'sound-mobile.png')});
  report.musicFetches=requests.filter(x=>/\/music\.mp3/.test(x)).length;report.modelCalls=requests.filter(x=>/reactor\.inc|elevenlabs\.io|suno\.com|\/api\//.test(x));report.englishOnly=await p.evaluate(()=>!/[\u4e00-\u9fff]/.test(document.body.innerText));
  const fail=await browser.newPage();const failureErrors=[];fail.on('pageerror',e=>failureErrors.push(e.message));await fail.route('**/music.mp3',r=>r.abort());await fail.goto(base);await fail.waitForFunction(()=>window.__sound&&window.__reveal?.info.playing);await fail.getByRole('button',{name:'Enable sound',exact:true}).click();await fail.waitForFunction(()=>window.__sound.info.errors.length>0);
  report.audioFailure=await fail.evaluate(()=>({playing:window.__reveal.info.playing,videoMix:window.__reveal.sphere.material.uniforms.uVideoMix.value,audioErrors:window.__sound.info.errors}));report.audioFailure.pageErrors=failureErrors;await fail.close();
  report.errors=errors;report.checks={
   optIn:!report.before.enabled&&report.audioRequestsBeforeOptIn===0,
   actualDecodedAudio:report.garden.ready&&report.garden.assets===6&&report.garden.rms>.0001&&report.garden.bufferSeconds['music.mp3']>100,
   revealMix:report.hidden.mix>.98&&report.hidden.gainTargets.dark>.1&&report.hidden.gainTargets.hell>.4&&report.returned.mix<.02,
   caption:report.caption.startsWith('A garden offers everything.'),
   oncePerEncounter:JSON.stringify(report.completed.completed)===JSON.stringify(['arrival','reveal','return'])&&report.afterAnotherLoop.completed.length===3,
   muteResume:report.muted.contextState==='suspended'&&report.muted.userMuted&&!report.muted.enabled&&report.resumed.contextState==='running'&&report.resumed.enabled,
   separateVoiceAndCaptions:!report.voiceOff.voiceEnabled&&report.replay.narrationId==='arrival'&&report.captionOff==='',
   oneMusicFetch:report.musicFetches===1,
   mobile:report.mobile.scrollWidth===report.mobile.width&&report.mobile.panel.right<=391,
   englishOnly:report.englishOnly,
   visualSurvivesAudioFailure:report.audioFailure.playing&&report.audioFailure.videoMix>.99&&!failureErrors.length,
   noModelCalls:report.modelCalls.length===0,
   noPageErrors:errors.length===0,
  };
  await fs.writeFile(path.join(out,'sound-verification.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({url:base,checks:report.checks,errors},null,2));if(Object.values(report.checks).some(v=>!v))process.exitCode=2;
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
