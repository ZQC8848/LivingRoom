const fs=require('node:fs/promises');
const path=require('node:path');
const {chromium}=require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');

(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:1030},colorScheme:'dark',deviceScaleFactor:1});page.setDefaultTimeout(60000);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const dir=path.join(__dirname,'review','bosch-room');await fs.mkdir(dir,{recursive:true});
  await page.setContent(await fs.readFile(path.join(__dirname,'bosch-room.html'),'utf8'),{waitUntil:'load'});
  await page.waitForFunction(()=>document.querySelector('#bosch-ring-room')?.boschRoom?.state().frames>4);
  const get=()=>page.evaluate(()=>document.querySelector('#bosch-ring-room').boschRoom.state());
  const initial=await get();
  await page.locator('.reference-toggle').click();
  const referenceShown=await page.locator('.reference-panel').isVisible();
  await page.screenshot({path:path.join(dir,'00-original-reference.png'),fullPage:true});
  await page.locator('.reference-toggle').click();
  await page.locator('.animate').uncheck();await page.waitForTimeout(120);
  await page.screenshot({path:path.join(dir,'01-gallery-belt.png'),fullPage:true});
  const garden=await page.locator('.viewer').screenshot();
  await page.locator('[data-look="up"]').click();await page.waitForTimeout(150);const up=await page.locator('.viewer').screenshot();
  await page.screenshot({path:path.join(dir,'02-dome.png'),fullPage:true});
  await page.locator('[data-look="down"]').click();await page.waitForTimeout(150);const down=await page.locator('.viewer').screenshot();
  await page.locator('[data-look="front"]').click();await page.locator('[data-layer="1"]').click();await page.waitForTimeout(150);
  const reveal=await page.locator('.viewer').screenshot();const fixed=await get();
  const box=await page.locator('.viewer').boundingBox();await page.locator('.viewer').hover({position:{x:box.width*.7,y:box.height*.45}});await page.waitForTimeout(150);
  const moved=await get();
  await page.screenshot({path:path.join(dir,'03-portal.png'),fullPage:true});
  await page.locator('.projection').click();await page.waitForTimeout(150);const rect=await page.locator('.stage').boundingBox();
  await page.screenshot({path:path.join(dir,'04-layout.png'),fullPage:true});
  await page.locator('.regions').check();await page.waitForTimeout(100);
  await page.screenshot({path:path.join(dir,'06-region-layout.png'),fullPage:true});
  await page.locator('.regions').uncheck();
  const boundaryTests=[];
  for(const layer of [0,2]){
    await page.evaluate(layer=>{const r=document.querySelector('#bosch-ring-room').boschRoom;r.set({flat:true,layer,animate:false,showRegions:false,probe:0});},layer);
    await page.waitForTimeout(100);
    await page.evaluate(()=>{const c=document.querySelector('.viewer'),g=c.getContext('webgl'),p=new Uint8Array(c.width*c.height*4);g.readPixels(0,0,c.width,c.height,g.RGBA,g.UNSIGNED_BYTE,p);window.__patchBaseline={p,w:c.width,h:c.height};document.querySelector('#bosch-ring-room').boschRoom.set({probe:1});});
    await page.waitForTimeout(100);
    boundaryTests.push(await page.evaluate(layer=>{
      const c=document.querySelector('.viewer'),g=c.getContext('webgl'),before=window.__patchBaseline,p=new Uint8Array(c.width*c.height*4);g.readPixels(0,0,c.width,c.height,g.RGBA,g.UNSIGNED_BYTE,p);
      const api=document.querySelector('#bosch-ring-room').boschRoom,s=api.state(),kind=layer===0?'garden':'hell',regions=api.regions.filter(r=>r.layer===kind),aspect=s.sourcePixels[kind][0]/s.sourcePixels[kind][1],band=s.band*Math.PI/180,span=2*Math.tan(band)*aspect;
      let changedInside=0,changedOutside=0;
      for(let y=0;y<c.height;y++){const lat=((y+.5)/c.height-.5)*Math.PI,sy=.5-Math.tan(lat)/(2*Math.tan(band));for(let x=0;x<c.width;x++){const i=(y*c.width+x)*4;if(p[i]===before.p[i]&&p[i+1]===before.p[i+1]&&p[i+2]===before.p[i+2])continue;const lon=((x+.5)/c.width-.5)*Math.PI*2,sx=.5+lon/span;const inside=Math.abs(lat)<band&&regions.some(r=>sx>=r.active[0]&&sx<=r.active[2]&&sy>=r.active[1]&&sy<=r.active[3]);if(inside)changedInside++;else changedOutside++;}}
      return {layer:kind,changedInside,changedOutside};
    },layer));
  }
  await page.evaluate(()=>document.querySelector('#bosch-ring-room').boschRoom.set({probe:0,layer:0}));
  for(const [name,layer]of [['garden',0],['hell',2]]){
   const data=await page.evaluate(({width,layer})=>document.querySelector('#bosch-ring-room').boschRoom.exportMaster(width,layer),{width:8192,layer});
   await fs.writeFile(path.join(__dirname,'bosch-hd',`${name}-equirect-8192.jpg`),Buffer.from(data.split(',')[1],'base64'));
  }
  await page.setViewportSize({width:390,height:900});await page.locator('.projection').click();await page.waitForTimeout(200);
  await page.screenshot({path:path.join(dir,'05-mobile.png'),fullPage:true});
  const mobile=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));
  // Verify the self-contained compressed conversation edition separately.
  await page.setContent(await fs.readFile('C:/Users/zoezi/.codex/visualizations/2026/11/14/01a1db35-61bc-73d0-9c2c-3bdd25ec5898/bosch-ring-room.html','utf8'),{waitUntil:'load'});
  await page.waitForFunction(()=>document.querySelector('#bosch-ring-room')?.boschRoom?.state().frames>2);
  const preview=await get();
  const report={errors,initial,referenceShown,boundaryTests,capViewsDiffer:!garden.equals(up)&&!garden.equals(down)&&!up.equals(down),revealChangesImage:!garden.equals(reveal),handLeavesCameraFixed:fixed.yaw===moved.yaw&&fixed.pitch===moved.pitch,layoutAspect:rect.width/rect.height,mobile,preview};
  await fs.writeFile(path.join(dir,'verification.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify(report,null,2));
  if(errors.length||initial.sourceInstances!==1||initial.sourceSpanDegrees>90||!referenceShown||boundaryTests.some(r=>r.changedOutside!==0||r.changedInside===0)||!report.capViewsDiffer||!report.revealChangesImage||!report.handLeavesCameraFixed||Math.abs(report.layoutAspect-2)>.01||mobile.scroll>mobile.width)process.exitCode=1;
 }finally{await browser.close();}
})().catch(e=>{console.error(e.stack);process.exitCode=1});
