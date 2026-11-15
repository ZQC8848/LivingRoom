const fs=require('node:fs/promises');
const path=require('node:path');
const {chromium}=require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--autoplay-policy=no-user-gesture-required']});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:1000},colorScheme:'dark',deviceScaleFactor:1});page.setDefaultTimeout(45000);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const dir=path.join(__dirname,'review','bosch-orbis-v5');await fs.mkdir(dir,{recursive:true});
  await page.setContent(await fs.readFile(path.join(__dirname,'bosch-orbis-v5.html'),'utf8'),{waitUntil:'load'});
  await page.waitForFunction(()=>document.querySelector('#bosch-orbis-test')?.orbisTest?.state().ready===2&&document.querySelector('#bosch-orbis-test').orbisTest.state().frames>2);
  const get=()=>page.evaluate(()=>document.querySelector('#bosch-orbis-test').orbisTest.state());
  const initial=await get();await page.waitForTimeout(900);const later=await get();
  await page.screenshot({path:path.join(dir,'01-panorama.png'),fullPage:true});
  const samples=[];
  for(const look of ['horse','bird','water','leaves','fire']){
    await page.locator(`[data-look="${look}"]`).click();
    await page.evaluate(()=>document.querySelector('#bosch-orbis-test').orbisTest.seek(1.2));await page.waitForTimeout(130);const a=await page.locator('.viewer').screenshot();
    await page.evaluate(()=>document.querySelector('#bosch-orbis-test').orbisTest.seek(2.8));await page.waitForTimeout(130);const b=await page.locator('.viewer').screenshot();
    samples.push({look,frameChanges:!a.equals(b)});
    await page.screenshot({path:path.join(dir,`02-${look}.png`),fullPage:true});
  }
  await page.locator('[data-look="front"]').click();await page.locator('[data-layer="0"]').click();await page.waitForTimeout(100);const garden=await page.locator('.viewer').screenshot();
  await page.locator('[data-layer="1"]').click();await page.waitForTimeout(100);const reveal=await page.locator('.viewer').screenshot();const handStart=await get();
  const box=await page.locator('.viewer').boundingBox();await page.locator('.viewer').hover({position:{x:box.width*.7,y:box.height*.4}});await page.waitForTimeout(120);const handEnd=await get();
  await page.screenshot({path:path.join(dir,'03-reveal.png'),fullPage:true});
  await page.locator('[data-look="back"]').click();await page.waitForTimeout(100);await page.screenshot({path:path.join(dir,'04-back.png'),fullPage:true});
  await page.locator('.projection').click();await page.waitForTimeout(100);const rectangle=await page.locator('.stage').boundingBox();await page.screenshot({path:path.join(dir,'05-flat.png'),fullPage:true});
  await page.locator('.raw-toggle').click();await page.waitForFunction(()=>document.querySelector('.raw-video').readyState>=2);
  const rawTests=[];
  for(const job of ['water','horse','bird','leaves','fire']){
    await page.locator('.raw-select').selectOption(job);await page.waitForFunction(()=>document.querySelector('.raw-video').readyState>=2);const status=await page.locator('.raw-status').innerText();
    await page.locator('.raw-reference').click();const reference=await page.locator('.raw-image').isVisible();await page.locator('.raw-reference').click();rawTests.push({job,status,reference});
    if(job==='horse')await page.screenshot({path:path.join(dir,'06-raw-horse.png'),fullPage:true});
  }
  await page.locator('.raw-toggle').click();await page.locator('[data-look="water"]').click();
  await page.setViewportSize({width:390,height:950});await page.waitForTimeout(150);await page.screenshot({path:path.join(dir,'07-mobile.png'),fullPage:true});
  const mobile=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));
  await page.setViewportSize({width:1024,height:940});
  const previewPath='C:/Users/zoezi/.codex/visualizations/2026/11/14/01a1db35-61bc-73d0-9c2c-3bdd25ec5898/bosch-orbis-v5.html';
  await page.setContent(await fs.readFile(previewPath,'utf8'),{waitUntil:'load'});await page.waitForFunction(()=>document.querySelector('#bosch-orbis-test')?.orbisTest?.state().frames>2);
  const preview=await get();await page.screenshot({path:path.join(dir,'08-inline.png'),fullPage:true});
  await page.locator('.play').click();const pauseState=await get();await page.waitForTimeout(250);const pauseLater=await get();
  const report={errors,initial,videoAdvances:later.videoTimes.garden.currentTime!==initial.videoTimes.garden.currentTime,videoDoesNotMoveCamera:initial.yaw===later.yaw&&initial.pitch===later.pitch,motionSamples:samples,revealChangesImage:!garden.equals(reveal),handDoesNotMoveCamera:handStart.yaw===handEnd.yaw&&handStart.pitch===handEnd.pitch,handMovesMask:handStart.handU!==handEnd.handU||handStart.handV!==handEnd.handV,layoutAspect:rectangle.width/rectangle.height,rawTests,mobile,preview,pauseWorks:!pauseState.playing&&Math.abs(pauseLater.videoTimes.garden.currentTime-pauseState.videoTimes.garden.currentTime)<.05,inlineBytes:(await fs.stat(previewPath)).size};
  await fs.writeFile(path.join(dir,'verification.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
  if(errors.length||!report.videoAdvances||!report.videoDoesNotMoveCamera||samples.some(s=>!s.frameChanges)||!report.revealChangesImage||!report.handDoesNotMoveCamera||!report.handMovesMask||Math.abs(report.layoutAspect-2)>.01||rawTests.some(t=>!t.reference)||mobile.scroll>mobile.width||!report.pauseWorks||report.inlineBytes>=1000000)process.exitCode=1;
 }finally{await browser.close();}
})().catch(e=>{console.error(e.stack);process.exitCode=1});
