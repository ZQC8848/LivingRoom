const fs=require('node:fs/promises');
const path=require('node:path');
const {chromium}=require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
const base=process.argv[2]||'http://127.0.0.1:5183/';
const out=path.resolve('deployment/review',process.argv[3]||'local');
const wait=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 await fs.mkdir(out,{recursive:true});
 const b=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--autoplay-policy=no-user-gesture-required']});
 const report={url:base,headsetVerified:false,scope:'Real released media and production build in desktop Chrome; synthetic controller events and XR session options are explicitly simulated.'};
 try{
  const p=await b.newPage({viewport:{width:1280,height:900},deviceScaleFactor:1});p.setDefaultTimeout(45000);
  const errors=[];const api=[];p.on('pageerror',e=>errors.push(e.message));p.on('request',r=>{if(/\/api\//.test(r.url())||/reactor\.inc/.test(r.url()))api.push(r.url());});
  await p.goto(new URL('?debug=1',base).href,{waitUntil:'domcontentloaded'});
  await p.waitForFunction(()=>window.__reveal?.info.playing&&window.__reveal.sphere.material.uniforms.uVideoMix.value>.99);
  const state=()=>p.evaluate(()=>{const a=window.__reveal;return {playing:a.info.playing,sourceIsBlob:a.heaven.currentSrc.startsWith('blob:'),fullyBuffered:a.fullyBuffered,storageMode:a.storageMode,oneDecoder:a.heaven===a.hell,oneTexture:a.sphere.material.uniforms.uHeaven.value===a.sphere.material.uniforms.uHell.value,paused:a.heaven.paused,problems:[...a.info.problems],heaven:{t:a.heaven.currentTime,w:a.heaven.videoWidth,h:a.heaven.videoHeight,duration:a.heaven.duration},hell:{t:a.hell.currentTime,w:a.hell.videoWidth,h:a.hell.videoHeight,duration:a.hell.duration},radii:a.state.radiiDeg(),resyncs:a.info.resyncs,rotation:a.camera.rotation.toArray(),position:a.camera.position.toArray(),mix:a.sphere.material.uniforms.uVideoMix.value};});
  report.initial=await state();await p.screenshot({path:path.join(out,'01-panorama.png')});
  let previous=report.initial.heaven.t,wraps=0,maxDrift=0,allPlaying=true,allVisible=true;
  await p.evaluate(()=>{window.__qaFrames=0;const v=window.__reveal.heaven;const tick=()=>{window.__qaFrames++;v.requestVideoFrameCallback(tick);};v.requestVideoFrameCallback(tick);});
  for(let i=0;i<72;i++){
   await p.waitForTimeout(250);const s=await state();if(s.heaven.t<previous-.5)wraps++;previous=s.heaven.t;allPlaying&&=s.playing;allVisible&&=s.mix>.99&&!s.paused&&!s.problems.length;
   const dur=s.heaven.duration;let d=Math.abs(s.heaven.t-s.hell.t);maxDrift=Math.max(maxDrift,Math.min(d,dur-d)*30);
  }
  report.playback={wraps,maxDriftFrames:maxDrift,allPlaying,allVisible,presentedFrames:await p.evaluate(()=>window.__qaFrames)};
  if(report.initial.oneDecoder){
   report.preciseSeek=await p.evaluate(async()=>{const a=window.__reveal,v=a.heaven;v.pause();const target=5;const ready=new Promise(res=>v.addEventListener('seeked',res,{once:true}));v.currentTime=target;await Promise.race([ready,new Promise(r=>setTimeout(r,2500))]);const r={target,actual:v.currentTime,mix:a.sphere.material.uniforms.uVideoMix.value,seekable:v.seekable.length?[[v.seekable.start(0),v.seekable.end(0)]]:[]};await v.play();return r;});
   await p.waitForTimeout(500);const ss=await state();report.resync={singleClock:true,driftFrames:Math.abs(ss.heaven.t-ss.hell.t)*30,keptVideoMix:ss.mix};
  }else{
   const beforeSync=await state();await p.evaluate(()=>{const a=window.__reveal;a.hell.currentTime=(a.heaven.currentTime+2)%a.heaven.duration;});await p.waitForTimeout(1400);
   const ss=await state();let d=Math.abs(ss.heaven.t-ss.hell.t);report.resync={singleClock:false,countIncreased:ss.resyncs>beforeSync.resyncs,driftFrames:Math.min(d,8-d)*30};
  }
  const canvas=p.locator('canvas').first();await canvas.click({position:{x:640,y:450}});await p.waitForTimeout(900);report.open=await state();await p.screenshot({path:path.join(out,'02-reveal.png')});
  await canvas.click({position:{x:640,y:450}});await p.waitForTimeout(700);report.closed=await state();
  // Exercise the actual production controller event handlers without claiming a headset.
  await p.evaluate(()=>{const a=window.__reveal,c=a.renderer.xr.getController(0);c.matrix.makeRotationY(-Math.PI/2);c.matrixWorldNeedsUpdate=true;c.updateMatrixWorld(true);c.dispatchEvent({type:'selectstart'});});await p.waitForTimeout(900);
  const controllerOpen=await state();const direction=await p.evaluate(()=>window.__reveal.sphere.slots[0].toArray());
  await p.evaluate(()=>window.__reveal.renderer.xr.getController(0).dispatchEvent({type:'selectend'}));await p.waitForTimeout(700);
  report.simulatedController={openDegrees:controllerOpen.radii[0],direction,closedDegrees:(await state()).radii[0]};
  await p.evaluate(()=>{const a=window.__reveal;a.openAt(0,0);a.openAt(70,15,1);});await p.waitForTimeout(850);report.twoSlots=(await state()).radii;
  await p.evaluate(()=>{window.__reveal.close();window.__reveal.close(1);});await p.waitForTimeout(650);
  report.focus={};for(const name of ['horse','water','fire']){
   report.focus[name]=await p.evaluate(name=>window.__reveal.focus(name),name);await p.waitForTimeout(850);
   if(name!=='fire'){await p.evaluate(()=>window.__reveal.close());await p.waitForTimeout(650);}
   await p.screenshot({path:path.join(out,`03-${name}.png`)});
  }
  await p.evaluate(()=>{window.__reveal.close();window.__reveal.lookAt(-179,10);window.__reveal.openAt(179,10);});await p.waitForTimeout(850);await p.screenshot({path:path.join(out,'04-seam-reveal.png')});
  await p.evaluate(()=>{window.__reveal.close();window.__reveal.close(1);window.__reveal.lookAt(30,50);});await p.waitForTimeout(700);
  report.color=await p.evaluate(()=>{
   const a=window.__reveal,v=a.heaven,cv=document.createElement('canvas');cv.width=v.videoWidth;cv.height=v.videoHeight;const ctx=cv.getContext('2d');ctx.drawImage(v,0,0);
   const sx=(.5+30/360)*v.videoWidth,sy=(.5-50/180)*(a.heaven===a.hell?v.videoHeight/2:v.videoHeight);
   const pix=ctx.getImageData(Math.round(sx)-2,Math.round(sy)-2,5,5).data;const expected=[0,0,0];for(let i=0;i<pix.length;i+=4)for(let c=0;c<3;c++)expected[c]+=pix[i+c]/25;
   a.renderer.render(a.sphere.mesh.parent,a.camera);const gl=a.renderer.getContext(),rgba=new Uint8Array(5*5*4);gl.readPixels(Math.floor(gl.drawingBufferWidth/2)-2,Math.floor(gl.drawingBufferHeight/2)-2,5,5,gl.RGBA,gl.UNSIGNED_BYTE,rgba);const actual=[0,0,0];for(let i=0;i<rgba.length;i+=4)for(let c=0;c<3;c++)actual[c]+=rgba[i+c]/25;
   return {expected,actual,meanError:actual.reduce((s,x,i)=>s+Math.abs(x-expected[i]),0)/3};
  });
  // Both video inputs keep advancing while the observer orientation stays fixed.
  const still1=await state();await p.waitForTimeout(700);const still2=await state();report.noAutomaticCameraMovement=JSON.stringify(still1.rotation)===JSON.stringify(still2.rotation)&&JSON.stringify(still1.position)===JSON.stringify(still2.position);
  await p.evaluate(()=>{window.__reveal.close();window.__reveal.heaven.pause();window.__reveal.hell.pause();});await p.waitForTimeout(1100);const imageA=await canvas.screenshot();
  await p.evaluate(()=>window.__reveal.camera.position.set(1,.4,-.7));await p.waitForTimeout(150);const imageB=await canvas.screenshot();report.translationDoesNotDistortPanorama=imageA.equals(imageB);
  // Real delivery host must implement byte ranges, not merely advertise them.
  report.range=await p.evaluate(async()=>{const r=await fetch(new URL('scenes/bosch-demo/media/paired.mp4',location.href),{headers:{Range:'bytes=0-1023'}});return {status:r.status,contentRange:r.headers.get('content-range'),length:(await r.arrayBuffer()).byteLength,client:'actual browser fetch'};});
  const m=await b.newPage({viewport:{width:390,height:844},deviceScaleFactor:1});await m.goto(base);await m.waitForFunction(()=>window.__reveal?.info.playing);report.mobile=await m.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth}));await m.screenshot({path:path.join(out,'05-mobile.png')});await m.close();
  const f=await b.newPage({viewport:{width:1280,height:900}});const fallbackErrors=[];f.on('pageerror',e=>fallbackErrors.push(e.message));await f.route('**/*.mp4*',r=>r.abort());await f.goto(base);await f.waitForFunction(()=>window.__reveal?.info.problems.length>0);await f.evaluate(()=>window.__reveal.openAt(0,0));await f.waitForTimeout(1000);report.posterFallback=await f.evaluate(()=>({mix:window.__reveal.sphere.material.uniforms.uVideoMix.value,problemCount:window.__reveal.info.problems.length,hasRetryOverlay:[...document.querySelectorAll('button')].some(b=>b.textContent==='Tap to start')}));report.posterFallback.errors=fallbackErrors;await f.screenshot({path:path.join(out,'06-poster-fallback.png')});await f.close();
  // Verify hand-tracking is requested; deliberately stop before immersive setup.
  const x=await b.newPage();await x.addInitScript(()=>{Object.defineProperty(navigator,'xr',{configurable:true,value:{isSessionSupported:async()=>true,addEventListener(){},requestSession(mode,options){window.__xrRequest={mode,options};return new Promise(()=>{});}}});});await x.goto(base);await x.waitForFunction(()=>window.__reveal);await x.locator('#VRButton').click();await x.waitForFunction(()=>window.__xrRequest);report.simulatedXRRequest=await x.evaluate(()=>window.__xrRequest);await x.close();
  report.errors=errors;report.modelAPIRequests=api;report.transportContract='Full checked Blob preload; HTTP Range is diagnostic only and is not required for playback.';
  report.checks={
   realMediaLoaded:report.initial.heaven.w===2048&&report.initial.heaven.h===(report.initial.oneDecoder?2048:1024)&&report.initial.hell.duration===8,
   loopsAndPlayback:wraps>=2&&allVisible&&report.playback.presentedFrames>30,
   synced:report.initial.oneDecoder&&report.initial.oneTexture&&maxDrift===0&&report.resync.driftFrames===0&&report.resync.keptVideoMix>.99,
   mouseReveal:report.open.radii[0]>37&&report.closed.radii[0]<.01,
   controllerWiring:controllerOpen.radii[0]>37&&direction[0]>.99&&report.simulatedController.closedDegrees<.01,
   twoHands:report.twoSlots.every(r=>r>37),
   focus:Object.values(report.focus).every(Boolean),
   headLocked:report.noAutomaticCameraMovement&&report.translationDoesNotDistortPanorama,
   bufferedTransport:report.initial.sourceIsBlob&&report.initial.fullyBuffered&&report.preciseSeek.seekable.some(r=>r[0]===0&&r[1]>=7.99),
   mobile:report.mobile.scrollWidth===report.mobile.width,
   fallback:report.posterFallback.mix===0&&report.posterFallback.problemCount>0&&!report.posterFallback.hasRetryOverlay&&!fallbackErrors.length,
   handTrackingRequested:report.simulatedXRRequest.options.optionalFeatures.includes('hand-tracking'),
   color:report.color.meanError<12,
   preciseSeek:report.initial.sourceIsBlob&&report.initial.fullyBuffered&&Math.abs(report.preciseSeek.actual-report.preciseSeek.target)<1/30&&report.preciseSeek.mix>.99,
   noModelCalls:api.length===0,
   noPageErrors:errors.length===0,
  };
  await fs.writeFile(path.join(out,'verification.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({url:base,checks:report.checks,playback:report.playback,range:report.range,errors},null,2));
  if(!Object.values(report.checks).every(Boolean))process.exitCode=1;
 }finally{await b.close();}
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
