const fs=require('node:fs/promises');
const path=require('node:path');
const {chromium}=require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');

(async()=>{
  const root=__dirname;
  await fs.mkdir(path.join(root,'review'),{recursive:true});
  const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const page=await browser.newPage({viewport:{width:1280,height:960},deviceScaleFactor:1,colorScheme:'dark'});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.setContent(await fs.readFile(path.join(root,'index.html'),'utf8'),{waitUntil:'load'});
  await page.waitForFunction(()=>document.querySelector('#painting-lab')?.paintingLab?.state().frameStats.frames>4);
  await page.waitForTimeout(400);
  const studies=await page.evaluate(()=>document.querySelector('#painting-lab').paintingLab.studies);
  const results=[];
  async function hash(){return page.evaluate(()=>{const c=document.querySelector('.world'),g=c.getContext('webgl');const a=new Uint8Array(c.width*c.height*4);g.readPixels(0,0,c.width,c.height,g.RGBA,g.UNSIGNED_BYTE,a);let sum=0,variance=0;for(let i=0;i<a.length;i+=64){sum+=(a[i]+a[i+1]+a[i+2]);variance+=Math.abs(a[i]-a[Math.max(0,i-64)]);}return {sum,variance};});}
  for(const study of studies){
    await page.locator(`[data-study="${study.id}"]`).click();
    await page.waitForTimeout(250);
    const before=await page.locator('.world').screenshot();
    const initial=await hash();
    if(study.id==='repin')await page.locator('.hotspot').first().click();
    await page.locator('.advance').click();
    await page.waitForTimeout(600);
    const after=await page.locator('.world').screenshot();
    const state=await page.evaluate(()=>document.querySelector('#painting-lab').paintingLab.state());
    const render=await hash();
    results.push({id:study.id,phase:state.phase,changed:!before.equals(after),render,source:state.frameStats.source,videoTracks:state.videoTracks});
    if(['levi','cards','damage','escher'].includes(study.id))await page.screenshot({path:path.join(root,'review',study.id+'.png'),fullPage:true});
  }
  const completion=await page.evaluate(()=>{
    const lab=document.querySelector('#painting-lab').paintingLab;
    return lab.studies.map(study=>{
      lab.select(study.id);
      let s=lab.state();
      for(let n=s.phase;n<study.steps;n++)lab.advance();
      s=lab.state();
      return {id:study.id,finalPhase:s.phase,expected:study.steps,weather:s.weather};
    });
  });
  await page.locator('[data-study="cards"]').click();
  await page.locator('.restart').click();
  const center=await page.locator('.world').screenshot();
  await page.locator('[data-turn="180"]').click();
  await page.waitForTimeout(600);
  const back=await page.locator('.world').screenshot();
  const backState=await page.evaluate(()=>document.querySelector('#painting-lab').paintingLab.state());
  await page.locator('[data-turn="0"]').click();
  await page.locator('[data-rating="值得深化"]').click();
  const ratingSaved=await page.locator('[data-rating="值得深化"]').getAttribute('aria-pressed');
  await page.setViewportSize({width:390,height:900});
  await page.locator('.mobile-picker').selectOption('damage');
  await page.waitForTimeout(200);
  await page.screenshot({path:path.join(root,'review','mobile.png'),fullPage:true});
  const mobile=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,title:document.querySelector('.study-title').textContent,visible:document.querySelector('.world').getBoundingClientRect().width}));
  await page.setViewportSize({width:1280,height:960});
  await page.evaluate(()=>document.querySelector('#painting-lab').paintingLab.select('cards'));
  await page.waitForTimeout(300);
  await page.screenshot({path:path.join(root,'review','cover.png'),fullPage:true});
  const report={errors,studies:results,completion,turningChangesView:!center.equals(back),backYaw:backState.yaw,ratingSaved,mobile};
  await fs.writeFile(path.join(root,'review','verification.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify(report,null,2));
  await browser.close();
  if(errors.length||results.some(r=>!r.changed||r.videoTracks!==1||r.render.variance<100)||completion.some(r=>r.finalPhase!==r.expected)||completion.find(r=>r.id==='spring').weather!==0||mobile.scroll>mobile.width)process.exitCode=1;
})().catch(e=>{console.error(e.stack);process.exitCode=1});
