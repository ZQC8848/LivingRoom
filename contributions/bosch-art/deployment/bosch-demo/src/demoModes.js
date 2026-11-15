import * as THREE from 'three';
import { createVrPanel } from './vrPanel.js';

// Five authored experiences share the existing renderer and ONE video decoder.
// HTML controls remain visible; XR has its own ray-selectable menu and hand target.
export function createDemoModes({ renderer, scene, camera, hud, specs, initialUrl, onSwitch, getSound }) {
  const info = { active: 'reveal', loading: false, error: null, menuOpen: false, liveGeneration: false, switches: 0 };
  const blobs = new Map(initialUrl ? [['reveal', Promise.resolve(initialUrl)]] : []);
  const raycaster = new THREE.Raycaster(), position = new THREE.Vector3(), quaternion = new THREE.Quaternion();
  const forward = new THREE.Vector3(), up = new THREE.Vector3(0,1,0);
  const row = document.createElement('div');row.className='row mode-controls';row.style.alignItems='center';
  const label=document.createElement('label');label.textContent='Mode ';label.htmlFor='experience-mode';
  const select=document.createElement('select');select.id='experience-mode';select.setAttribute('aria-label','Experience mode');
  for(const s of specs){const o=document.createElement('option');o.value=s.id;o.textContent=s.label;select.append(o)}
  const open=document.createElement('button');open.id='open-mode-menu';open.textContent='VR menu';open.title='Preview or reopen the in-world mode menu';
  const guide=document.createElement('a');guide.textContent='How to use';guide.href='/guide/';guide.target='_blank';guide.rel='noopener';guide.style.color='#d9d2b6';
  const live=document.createElement('a');live.textContent='Live lab';live.href='/?experience=live';live.style.color='#d9d2b6';live.title='Actual Orbis streaming; private operator code required';
  row.append(label,select,open,guide,live);hud.append(row);
  const note=document.createElement('div');note.className='mode-note';note.textContent='Reveal is the main story · optional time studies';note.style.cssText='color:#bfc8b4;font:11px/1.4 system-ui;margin-top:5px';hud.append(note);
  const style=document.createElement('style');style.textContent='#experience-mode{max-width:100%;min-width:185px;font:inherit;border:1px solid #786e53;border-radius:5px;color:#f0ecdf;background:#27291f;padding:6px} .mode-controls label{display:flex;gap:7px;align-items:center}.mode-controls button,.mode-controls a{align-self:center}@media(max-width:650px){#hud{max-width:calc(100vw - 24px)}#experience-mode{min-width:150px;max-width:230px}}';document.head.append(style);

  const buttons=specs.map(s=>({id:s.id,label:s.shortLabel||s.label})).concat([{id:'sound',label:'Enable sound'},{id:'voice',label:'Replay narration'},{id:'research',label:'Research story'},{id:'close',label:'Close menu'}]);
  const menu=createVrPanel({buttons,onPress:id=>{
    if(id==='close'){hide();return}
    const sound=getSound();
    if(id==='sound'){if(sound?.info.enabled)sound.disable();else sound?.enable().catch(()=>{});return}
    if(id==='voice'){sound?.replayVoice().catch(()=>{});hide();return}
    if(id==='research'){sound?.speakResearch().catch(()=>{});hide();return}
    choose(id).catch(()=>{});
  }});scene.add(menu.mesh);
  const badgeCanvas=Object.assign(document.createElement('canvas'),{width:512,height:160}),bc=badgeCanvas.getContext('2d');
  bc.fillStyle='rgba(20,28,21,.93)';bc.fillRect(0,0,512,160);bc.strokeStyle='#bdd1a1';bc.lineWidth=6;bc.strokeRect(3,3,506,154);bc.textAlign='center';bc.fillStyle='#edf2df';bc.font='600 64px system-ui';bc.fillText('MODES',256,82);bc.font='28px system-ui';bc.fillText('Point + pinch / trigger',256,129);
  const badgeTex=new THREE.CanvasTexture(badgeCanvas);badgeTex.colorSpace=THREE.SRGBColorSpace;
  const badge=new THREE.Mesh(new THREE.PlaneGeometry(.24,.075),new THREE.MeshBasicMaterial({map:badgeTex,transparent:true,depthTest:false,depthWrite:false}));badge.renderOrder=20;badge.visible=false;scene.add(badge);
  const captionCanvas=Object.assign(document.createElement('canvas'),{width:1280,height:300}),cc=captionCanvas.getContext('2d');
  const captionTex=new THREE.CanvasTexture(captionCanvas);captionTex.colorSpace=THREE.SRGBColorSpace;
  const caption=new THREE.Mesh(new THREE.PlaneGeometry(1.05,.246),new THREE.MeshBasicMaterial({map:captionTex,transparent:true,depthTest:false,depthWrite:false}));caption.renderOrder=19;caption.visible=false;scene.add(caption);
  let pendingOpen=false,lastCaption='',lastSound='',framesInXR=0;
  const current=()=>specs.find(s=>s.id===info.active)||specs[0];
  function show(){
    const head=renderer.xr.isPresenting?renderer.xr.getCamera():camera;head.updateMatrixWorld(true);menu.placeInFront(head);info.menuOpen=true;
    menu.set({status:'Choose an experience',detail:'Point, then pinch / trigger. Grip reopens menu.',highlight:info.active});
  }
  function hide(){menu.mesh.visible=false;info.menuOpen=false}
  function toggle(){if(info.menuOpen)hide();else show()}
  async function blob(spec){
    if(!blobs.has(spec.id))blobs.set(spec.id,(async()=>{
      const res=await fetch(spec.url+(spec.sha256?'?v='+spec.sha256.slice(0,12):''));if(!res.ok)throw Error('HTTP '+res.status);
      const data=await res.arrayBuffer();if(data.byteLength>64*1024*1024||spec.bytes&&data.byteLength!==spec.bytes)throw Error('Media size check failed');
      if(spec.sha256&&crypto?.subtle){const sha=[...new Uint8Array(await crypto.subtle.digest('SHA-256',data))].map(v=>v.toString(16).padStart(2,'0')).join('');if(sha!==spec.sha256)throw Error('Media checksum failed')}
      return URL.createObjectURL(new Blob([data],{type:'video/mp4'}));
    })().catch(e=>{blobs.delete(spec.id);throw e}));
    return blobs.get(spec.id);
  }
  async function choose(id){
    const spec=specs.find(s=>s.id===id);if(!spec||info.loading)return false;
    if(id===info.active&&!info.error){hide();return true}
    info.loading=true;info.error=null;select.disabled=true;note.textContent='Loading '+spec.label+'…';menu.set({status:'Loading '+spec.shortLabel.replace(/\n/g,' '),detail:'The view stays fixed while the video loads.'});
    try{
      const url=await blob(spec);await onSwitch(spec,url);info.active=id;info.switches++;select.value=id;getSound()?.setMode(id);hide();note.textContent=spec.description;
      return true;
    }catch(e){info.error=e.message;select.value=info.active;note.textContent='Could not switch mode. '+e.message;return false}
    finally{info.loading=false;select.disabled=false;menu.set({status:'Choose an experience',highlight:info.active})}
  }
  select.onchange=()=>choose(select.value);open.onclick=toggle;
  window.addEventListener('keydown',e=>{if(e.target.matches('input,select,textarea'))return;if(e.key==='m'||e.key==='M')toggle();const index=Number(e.key)-1;if(index>=0&&index<specs.length)choose(specs[index].id)});
  function controllerRay(c){c.updateMatrixWorld(true);return new THREE.Ray(new THREE.Vector3().setFromMatrixPosition(c.matrixWorld),new THREE.Vector3(0,0,-1).transformDirection(c.matrixWorld))}
  function handleSelect(c){
    if(!renderer.xr.isPresenting&&!menu.mesh.visible)return false;
    const ray=controllerRay(c);
    if(menu.mesh.visible){menu.select(ray);return true}
    if(badge.visible){badge.updateMatrixWorld(true);raycaster.ray.copy(ray);if(raycaster.intersectObject(badge,false).length){show();return true}}
    return false;
  }
  function drawCaption(text){
    if(text===lastCaption)return;lastCaption=text;cc.clearRect(0,0,1280,300);
    if(text){cc.fillStyle='rgba(10,17,12,.88)';cc.fillRect(0,0,1280,300);cc.fillStyle='#eff2e4';cc.font='36px Georgia';cc.textAlign='center';cc.textBaseline='middle';const words=text.split(/\s+/),lines=[];let line='';for(const word of words){if(cc.measureText(line+' '+word).width>1160&&line){lines.push(line);line=word}else line+=(line?' ':'')+word}if(line)lines.push(line);lines.slice(0,5).forEach((s,i)=>cc.fillText(s,640,150+(i-(Math.min(lines.length,5)-1)/2)*48))}
    captionTex.needsUpdate=true;
  }
  renderer.xr.addEventListener('sessionstart',()=>{pendingOpen=true;framesInXR=0});renderer.xr.addEventListener('sessionend',()=>{hide();badge.visible=false;caption.visible=false;pendingOpen=false});
  function update(controllers){
    const sound=getSound();const soundLabel=sound?.info.enabled?'Mute sound':sound?.info.loading?'Loading sound':'Enable sound';if(soundLabel!==lastSound){menu.setButtonLabel('sound',soundLabel);lastSound=soundLabel}
    if(!renderer.xr.isPresenting){badge.visible=false;caption.visible=false;return}
    framesInXR++;if(pendingOpen&&framesInXR>=2){pendingOpen=false;show()}
    const head=renderer.xr.getCamera();head.updateMatrixWorld(true);head.getWorldPosition(position);head.getWorldQuaternion(quaternion);
    badge.position.set(0,-.42,-.94).applyQuaternion(quaternion).add(position);badge.quaternion.copy(quaternion);badge.visible=!menu.mesh.visible;
    caption.position.set(0,-.22,-1.15).applyQuaternion(quaternion).add(position);caption.quaternion.copy(quaternion);drawCaption(sound?.caption?.textContent||'');caption.visible=!menu.mesh.visible&&!!lastCaption;
    const rays=controllers.filter(c=>c.userData.connected).map(controllerRay);menu.hover(rays);
    for(const c of controllers){const gp=c.userData.inputSource?.gamepad;const pressed=!!(gp?.buttons?.[4]?.pressed||gp?.buttons?.[5]?.pressed);if(pressed&&!c.userData.modeButtonWasDown)toggle();c.userData.modeButtonWasDown=pressed}
  }
  return {info,choose,update,handleSelect,show,hide,toggle,menu,badge,caption,specs,remember(id,url){blobs.set(id,Promise.resolve(url))},get active(){return info.active},get revealEnabled(){return info.active==='reveal'&&!info.menuOpen&&!info.loading},current};
}
