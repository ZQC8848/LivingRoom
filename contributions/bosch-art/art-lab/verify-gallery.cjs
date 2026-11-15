const fs=require('node:fs/promises');
const path=require('node:path');
const {chromium}=require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');

(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  try{
    const page=await browser.newPage({viewport:{width:1280,height:1050},deviceScaleFactor:1,colorScheme:'dark'});
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    const dir=path.join(__dirname,'review','gallery');await fs.mkdir(dir,{recursive:true});
    await page.setContent(await fs.readFile(path.join(__dirname,'gallery.html'),'utf8'),{waitUntil:'load'});
    const state=()=>page.evaluate(()=>document.querySelector('#painting-gallery').paintingLab.state());
    await page.waitForFunction(()=>document.querySelector('#painting-gallery')?.paintingLab.state().frameStats.frames>6);
    await page.waitForTimeout(500);
    await page.screenshot({path:path.join(dir,'01-gallery.png'),fullPage:true});
    const first=await state();
    const galleryVariation=await page.evaluate(()=>{const c=document.querySelector('.world'),g=c.getContext('webgl'),a=new Uint8Array(c.width*c.height*4);g.readPixels(0,0,c.width,c.height,g.RGBA,g.UNSIGNED_BYTE,a);let v=0;for(let i=64;i<a.length;i+=64)v+=Math.abs(a[i]-a[i-64]);return v;});
    const bounds=await page.locator('.world').boundingBox();
    // Click the painting itself in the panorama, not a test-only hook.
    await page.locator('.world').click({position:{x:bounds.width/2,y:bounds.height/2}});
    await page.waitForFunction(()=>{const s=document.querySelector('#painting-gallery').paintingLab.state();return s.mode==='world'&&!s.transitioning});
    await page.waitForTimeout(400);
    const entered=await state();
    await page.screenshot({path:path.join(dir,'02-garden.png'),fullPage:true});
    await page.locator('.advance').click();
    await page.waitForTimeout(500);
    const before=await page.locator('.world').screenshot();
    await page.waitForTimeout(600);
    const after=await page.locator('.world').screenshot();
    const revealed=await state();
    await page.screenshot({path:path.join(dir,'03-hell-window.png'),fullPage:true});
    await page.locator('.effects').uncheck();
    await page.waitForTimeout(400);
    const paused=await state();
    await page.locator('.effects').check();
    // Move the reveal aperture without changing the viewpoint.
    await page.locator('.world').hover({position:{x:bounds.width*.62,y:bounds.height*.58}});
    await page.waitForTimeout(250);
    const moved=await state();
    await page.locator('.return-gallery').click();
    await page.waitForFunction(()=>{const s=document.querySelector('#painting-gallery').paintingLab.state();return s.mode==='gallery'&&!s.transitioning});
    await page.waitForTimeout(350);
    const returned=await state();
    await page.screenshot({path:path.join(dir,'04-returned.png'),fullPage:true});
    const loop=[];
    for(const id of ['cards','levi','repin','mirror']){
      await page.locator('.mobile-picker').selectOption(id);
      await page.locator('.advance').click();
      await page.waitForFunction(()=>{const s=document.querySelector('#painting-gallery').paintingLab.state();return s.mode==='world'&&!s.transitioning});
      await page.locator('.advance').click();
      const s=await state();loop.push({id:s.id,phase:s.phase,videoTracks:s.videoTracks});
      await page.locator('.return-gallery').click();
      await page.waitForFunction(()=>{const s=document.querySelector('#painting-gallery').paintingLab.state();return s.mode==='gallery'&&!s.transitioning});
    }
    await page.setViewportSize({width:390,height:900});
    await page.locator('.mobile-picker').selectOption('bosch');
    await page.waitForTimeout(300);
    await page.screenshot({path:path.join(dir,'05-mobile.png'),fullPage:true});
    const mobile=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));
    const report={errors,startsInGallery:first.mode==='gallery',selected:first.id,galleryVariation,paintingClickEnters:entered.mode==='world'&&entered.id==='bosch',revealPhase:revealed.phase,fireChangesAtFixedView:!before.equals(after),fireCanPause:paused.effects===false,apertureLeavesViewFixed:moved.yaw===revealed.yaw&&moved.pitch===revealed.pitch,returnsToGallery:returned.mode==='gallery',retainsTrace:returned.revealed.includes('bosch'),singleVideoTrack:revealed.videoTracks===1,source:revealed.frameStats.source,loop,mobile};
    await fs.writeFile(path.join(dir,'verification.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
    if(errors.length||galleryVariation<30000||!report.paintingClickEnters||!report.fireChangesAtFixedView||!report.retainsTrace||!report.singleVideoTrack||mobile.scroll>mobile.width)process.exitCode=1;
  }finally{await browser.close();}
})().catch(e=>{console.error(e.stack);process.exitCode=1});
