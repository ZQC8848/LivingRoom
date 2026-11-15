const fs=require('node:fs/promises');
const path=require('node:path');
const {chromium}=require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');

(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:1050},colorScheme:'dark',deviceScaleFactor:1});page.setDefaultTimeout(45000);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const dir=path.join(__dirname,'review','bosch-world');await fs.mkdir(dir,{recursive:true});
  await page.setContent(await fs.readFile(path.join(__dirname,'bosch-world.html'),'utf8'),{waitUntil:'load'});
  await page.waitForFunction(()=>document.querySelector('#bosch-world-room')?.boschRoom?.state().frames>2);
  const api=()=>document.querySelector('#bosch-world-room').boschRoom;
  const get=()=>page.evaluate(()=>document.querySelector('#bosch-world-room').boschRoom.state());
  const initial=await get();await page.locator('.animate').uncheck();
  const cardinalViews=[],cardinalReveal=[];
  for(const direction of ['front','left','right','back']){
    await page.locator(`[data-look="${direction}"]`).click();await page.locator('[data-layer="0"]').click();await page.waitForTimeout(100);
    const garden=await page.locator('.viewer').screenshot();cardinalViews.push(garden);
    await page.screenshot({path:path.join(dir,`${direction}-garden.png`),fullPage:true});
    await page.locator('[data-layer="1"]').click();await page.waitForTimeout(100);
    const reveal=await page.locator('.viewer').screenshot();
    cardinalReveal.push({direction,changed:!garden.equals(reveal)});
    if(direction==='front'||direction==='back')await page.screenshot({path:path.join(dir,`${direction}-reveal.png`),fullPage:true});
  }
  const fixed=await get();const box=await page.locator('.viewer').boundingBox();
  await page.locator('.viewer').hover({position:{x:box.width*.7,y:box.height*.4}});await page.waitForTimeout(100);
  const moved=await get();
  await page.locator('[data-look="front"]').click();await page.locator('[data-layer="2"]').click();await page.waitForTimeout(100);
  await page.screenshot({path:path.join(dir,'front-hell.png'),fullPage:true});
  const hell=await page.locator('.viewer').screenshot();
  await page.locator('[data-look="up"]').click();await page.waitForTimeout(100);const up=await page.locator('.viewer').screenshot();
  await page.locator('[data-look="down"]').click();await page.waitForTimeout(100);const down=await page.locator('.viewer').screenshot();
  await page.locator('.reference-toggle').click();const referenceShown=await page.locator('.reference-panel').isVisible();await page.locator('.reference-toggle').click();
  await page.locator('.projection').click();await page.waitForTimeout(100);
  const rect=await page.locator('.stage').boundingBox();
  await page.locator('[data-layer="0"]').click();await page.waitForTimeout(100);
  await page.screenshot({path:path.join(dir,'flat-garden.png'),fullPage:true});
  const seam=await page.evaluate(()=>{
    const c=document.querySelector('.viewer'),g=c.getContext('webgl'),p=new Uint8Array(c.width*c.height*4);g.readPixels(0,0,c.width,c.height,g.RGBA,g.UNSIGNED_BYTE,p);
    let total=0,max=0,n=0;for(let y=Math.floor(c.height*.3);y<c.height*.7;y++)for(let k=0;k<3;k++){const a=(y*c.width)*4+k,b=(y*c.width+c.width-1)*4+k,d=Math.abs(p[a]-p[b]);total+=d;max=Math.max(max,d);n++;}
    return {meanChannelDelta:total/n,maxChannelDelta:max};
  });
  await page.locator('.regions').check();await page.waitForTimeout(100);await page.screenshot({path:path.join(dir,'flat-regions.png'),fullPage:true});await page.locator('.regions').uncheck();
  const boundaryTests=[];
  for(const layer of [0,2]){
    await page.evaluate(layer=>document.querySelector('#bosch-world-room').boschRoom.set({flat:true,layer,animate:false,showRegions:false,probe:0}),layer);await page.waitForTimeout(100);
    await page.evaluate(()=>{const c=document.querySelector('.viewer'),g=c.getContext('webgl'),p=new Uint8Array(c.width*c.height*4);g.readPixels(0,0,c.width,c.height,g.RGBA,g.UNSIGNED_BYTE,p);window.__baseline=p;document.querySelector('#bosch-world-room').boschRoom.set({probe:1});});await page.waitForTimeout(100);
    boundaryTests.push(await page.evaluate(layer=>{
      const c=document.querySelector('.viewer'),g=c.getContext('webgl'),p=new Uint8Array(c.width*c.height*4);g.readPixels(0,0,c.width,c.height,g.RGBA,g.UNSIGNED_BYTE,p);
      const a=document.querySelector('#bosch-world-room').boschRoom,s=a.state(),kind=layer===0?'garden':'hell',regions=a.regions.filter(r=>r.layer===kind),band=s.band*Math.PI/180;
      let changedInside=0,changedOutside=0;
      for(let y=0;y<c.height;y++){const lat=((y+.5)/c.height-.5)*Math.PI,sy=.36-Math.tan(lat)/Math.tan(band)*(lat>=0?.36:.64);for(let x=0;x<c.width;x++){const i=(y*c.width+x)*4;if(p[i]===window.__baseline[i]&&p[i+1]===window.__baseline[i+1]&&p[i+2]===window.__baseline[i+2])continue;const sx=(x+.5)/c.width;const inside=Math.abs(lat)<band&&regions.some(r=>sx>=r.active[0]&&sx<=r.active[2]&&sy>=r.active[1]&&sy<=r.active[3]);if(inside)changedInside++;else changedOutside++;}}
      return {layer:kind,changedInside,changedOutside};
    },layer));
  }
  await page.evaluate(()=>document.querySelector('#bosch-world-room').boschRoom.set({probe:0}));
  for(const [name,layer] of [['garden',0],['hell',2]]){
    const data=await page.evaluate(layer=>document.querySelector('#bosch-world-room').boschRoom.exportMaster(2048,layer),layer);
    await fs.writeFile(path.join(__dirname,'bosch-world-assets',`${name}-equirect-2048.jpg`),Buffer.from(data.split(',')[1],'base64'));
  }
  await page.setViewportSize({width:390,height:930});await page.locator('[data-look="front"]').click();await page.locator('[data-layer="1"]').click();await page.waitForTimeout(150);
  await page.screenshot({path:path.join(dir,'mobile.png'),fullPage:true});
  const mobile=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));
  await page.setViewportSize({width:1024,height:960});
  await page.setContent(await fs.readFile('C:/Users/zoezi/.codex/visualizations/2026/11/14/01a1db35-61bc-73d0-9c2c-3bdd25ec5898/bosch-world.html','utf8'),{waitUntil:'load'});
  await page.waitForFunction(()=>document.querySelector('#bosch-world-room')?.boschRoom?.state().frames>2);
  const preview=await get();await page.locator('[data-layer="1"]').click();await page.waitForTimeout(100);await page.screenshot({path:path.join(dir,'inline-preview.png'),fullPage:true});
  const distinctCardinalViews=cardinalViews.every((a,i)=>cardinalViews.every((b,j)=>i===j||!a.equals(b)));
  const report={errors,initial,referenceShown,distinctCardinalViews,cardinalReveal,handMovesMask:moved.handU!==fixed.handU||moved.handV!==fixed.handV,handLeavesCameraFixed:fixed.yaw===moved.yaw&&fixed.pitch===moved.pitch,capsDiffer:!hell.equals(up)&&!hell.equals(down)&&!up.equals(down),layoutAspect:rect.width/rect.height,seam,boundaryTests,mobile,preview};
  await fs.writeFile(path.join(dir,'verification.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
  if(errors.length||initial.sourceSpanDegrees!==360||!distinctCardinalViews||cardinalReveal.some(r=>!r.changed)||!report.handMovesMask||!report.handLeavesCameraFixed||!report.capsDiffer||!referenceShown||Math.abs(report.layoutAspect-2)>.01||seam.meanChannelDelta>5||boundaryTests.some(r=>r.changedOutside||!r.changedInside)||mobile.scroll>mobile.width)process.exitCode=1;
 }finally{await browser.close();}
})().catch(e=>{console.error(e.stack);process.exitCode=1});
