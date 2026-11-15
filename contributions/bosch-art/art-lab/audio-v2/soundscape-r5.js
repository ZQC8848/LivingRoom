// All assets are pre-generated static files. No credentials or model APIs run here.
export function createSoundscape({base, parent=document.body, embedded=false}={}) {
  const info={enabled:false,ready:false,loading:false,userMuted:false,errors:[],mix:0,night:0,played:[],completed:[],oneMusicClock:true,contextState:'not-started',assets:0,mode:'reveal'};
  let ctx,manifest,buffers={},nodes={},pending,queue=[],busy=false,voiceSource,serial=0,wasOpen=false;
  let voiceEnabled=true,captionsEnabled=true,volume=.7,suspendTimer;
  const played=new Set(),queued=new Set();
  if(!document.getElementById('sound-style-r4')){
    const style=document.createElement('style');style.id='sound-style-r4';style.textContent=`
    .sound-panel{position:fixed;z-index:20;top:16px;right:16px;display:flex;align-items:center;gap:9px;flex-wrap:wrap;max-width:420px;padding:9px 11px;background:rgba(22,31,26,.91);border:1px solid #586752;border-radius:8px;color:#e6eadd;font:13px system-ui,sans-serif}
    .sound-panel.embedded{position:static;max-width:none;margin:12px 0;background:#202c24}
    .sound-panel button{font:inherit;color:inherit;background:#344633;border:1px solid #6b815b;border-radius:5px;padding:7px 10px;cursor:pointer}.sound-panel button:disabled{opacity:.55;cursor:wait}.sound-panel label{display:flex;gap:4px;align-items:center}.sound-panel input[type=range]{width:82px;min-width:0;flex:none;padding:0;accent-color:#c0dba6}.sound-panel input[type=checkbox]{accent-color:#c0dba6;min-width:0;width:auto;flex:none;padding:0}.sound-panel a{color:#d3e5bf;font-size:12px}.sound-panel :focus-visible{outline:2px solid #d8ebbb;outline-offset:3px}
    .sound-caption{position:fixed;z-index:19;bottom:88px;left:50%;transform:translateX(-50%);max-width:min(680px,90vw);width:max-content;padding:10px 15px;background:rgba(12,18,14,.86);border-radius:6px;color:#f0f1e6;font:17px/1.5 Georgia,serif;text-align:center;pointer-events:none;white-space:normal}.sound-caption:empty{display:none}.sound-caption.embedded{position:static;transform:none;width:auto;max-width:780px;margin:8px auto}
    @media(max-width:950px){.sound-panel:not(.embedded){top:auto;bottom:78px;left:14px;right:14px;max-width:none}.sound-caption:not(.embedded){bottom:183px;font-size:15px}}
    `;document.head.append(style);
  }
  const panel=document.createElement('div');panel.className='sound-panel'+(embedded?' embedded':'');panel.setAttribute('aria-label','Sound controls');
  const toggle=document.createElement('button');toggle.type='button';toggle.textContent='Enable sound';toggle.setAttribute('aria-pressed','false');panel.append(toggle);
  const vl=document.createElement('label');vl.textContent='Volume';const range=document.createElement('input');range.type='range';range.min=0;range.max=1;range.step=.01;range.value=volume;range.setAttribute('aria-label','Sound volume');vl.append(range);panel.append(vl);
  function check(label,value,handler){const l=document.createElement('label'),c=document.createElement('input');c.type='checkbox';c.checked=value;c.setAttribute('aria-label',label);c.onchange=()=>handler(c.checked);l.append(c,document.createTextNode(label));panel.append(l);return c;}
  const voiceCheck=check('Voice',true,v=>{voiceEnabled=v;if(!v){serial++;voiceSource?.stop();busy=false;voiceSource=null;info.narrationId=null;queue=[];queued.clear();caption.textContent='';}else pump();applyMix();});
  check('Captions',true,v=>{captionsEnabled=v;caption.textContent=v&&busy?(manifest?.narration.find(n=>n.id===info.narrationId)?.text||''):'';});
  const replay=document.createElement('button');replay.type='button';replay.textContent='Replay voice';panel.append(replay);
  const research=document.createElement('button');research.type='button';research.textContent='Research story';panel.append(research);
  const transcript=document.createElement('a');transcript.href=new URL('transcript.en.html',base).href;transcript.target='_blank';transcript.rel='noopener';transcript.textContent='Transcript & credits';panel.append(transcript);
  const caption=document.createElement('div');caption.className='sound-caption'+(embedded?' embedded':'');caption.setAttribute('aria-live','polite');parent.append(panel,caption);
  function target(param,value,seconds=.22){if(ctx&&param)param.setTargetAtTime(value,ctx.currentTime,seconds);}
  function applyMix(){
    if(!ctx||!info.ready)return;
    const x=Math.max(info.mix,info.night*.55),duck=busy ? .46 : 1;
    target(nodes.bright.gain,.44*(1-x)*duck);target(nodes.dark.gain,.44*x*duck);
    const gardenPresence=info.mode.startsWith('hell-')?0:1;
    target(nodes.gardenGain.gain,.45*(1-.7*info.mix)*(1-.3*info.night)*gardenPresence*(busy ? .7 : 1));target(nodes.hellGain.gain,.48*info.mix*(busy ? .7 : 1));
    info.gainTargets={bright:.44*(1-x)*duck,dark:.44*x*duck,garden:.45*(1-.7*info.mix)*(1-.3*info.night)*gardenPresence,hell:.48*info.mix};
  }
  async function load(){
    if(info.ready)return;if(pending)return pending;
    pending=(async()=>{
      info.loading=true;toggle.disabled=true;toggle.textContent='Loading sound…';
      const C=window.AudioContext||window.webkitAudioContext;if(!C)throw Error('Web Audio is unavailable');
      ctx??=new C();await ctx.resume();info.contextState=ctx.state;
      const r=await fetch(new URL('manifest-r5.json',base),{cache:'no-cache'});if(!r.ok)throw Error('Audio manifest '+r.status);manifest=await r.json();
      const files=[manifest.music.file,...Object.values(manifest.ambience).map(a=>a.file),...manifest.narration.map(n=>n.file)];
      await Promise.all([...new Set(files)].map(async file=>{const response=await fetch(new URL(file,base));if(!response.ok)throw Error(file+' '+response.status);const bytes=await response.arrayBuffer();buffers[file]=await ctx.decodeAudioData(bytes);info.assets++;}));
      nodes.master=ctx.createGain();nodes.master.gain.value=0;
      nodes.limiter=ctx.createDynamicsCompressor();nodes.limiter.threshold.value=-7;nodes.limiter.knee.value=12;nodes.limiter.ratio.value=3;nodes.limiter.attack.value=.02;nodes.limiter.release.value=.2;
      nodes.analyser=ctx.createAnalyser();nodes.analyser.fftSize=2048;nodes.master.connect(nodes.limiter);nodes.limiter.connect(nodes.analyser);nodes.analyser.connect(ctx.destination);
      nodes.bright=ctx.createGain();nodes.dark=ctx.createGain();nodes.gardenGain=ctx.createGain();nodes.hellGain=ctx.createGain();nodes.voice=ctx.createGain();nodes.voice.gain.value=.95;
      for(const n of ['bright','dark','gardenGain','hellGain'])nodes[n].gain.value=0;
      for(const n of ['bright','dark','gardenGain','hellGain','voice'])nodes[n].connect(nodes.master);
      const music=ctx.createBufferSource();music.buffer=buffers[manifest.music.file];music.loop=true;
      const low=ctx.createBiquadFilter();low.type='lowpass';low.frequency.value=1200;low.Q.value=.65;
      const shelf=ctx.createBiquadFilter();shelf.type='lowshelf';shelf.frequency.value=170;shelf.gain.value=3;
      music.connect(nodes.bright);music.connect(low);low.connect(shelf);shelf.connect(nodes.dark);nodes.music=music;
      const start=ctx.currentTime+.1;music.start(start);
      for(const name of ['garden','hell']){
        const source=ctx.createBufferSource();source.buffer=buffers[manifest.ambience[name].file];source.loop=true;
        const panner=ctx.createPanner();panner.panningModel='HRTF';panner.distanceModel='inverse';panner.refDistance=4;panner.maxDistance=20;panner.rolloffFactor=.15;
        panner.positionZ.value=name==='garden'?-4:3;panner.positionX.value=name==='garden'?0:2;
        source.connect(panner);panner.connect(nodes[name+'Gain']);source.start(start);nodes[name+'Source']=source;nodes[name+'Panner']=panner;
      }
      info.ready=true;info.contextState=ctx.state;applyMix();
    })();
    try{await pending;}catch(e){info.errors.push(e.message);toggle.textContent='Retry sound';throw e;}finally{info.loading=false;toggle.disabled=false;if(!info.ready)pending=null;}
  }
  function enqueue(id){if(!played.has(id)&&!queued.has(id)){queue.push(id);queued.add(id);}pump();}
  function pump(){
    if(!info.enabled||!info.ready||busy||!voiceEnabled||!queue.length)return;
    const id=queue.shift();queued.delete(id);const cue=manifest.narration.find(n=>n.id===id);if(!cue)return;
    busy=true;played.add(id);info.played=[...played];info.narrationId=id;const mine=++serial;
    voiceSource=ctx.createBufferSource();voiceSource.buffer=buffers[cue.file];voiceSource.connect(nodes.voice);caption.textContent=captionsEnabled?cue.text:'';applyMix();
    voiceSource.onended=()=>{if(mine!==serial)return;busy=false;voiceSource=null;info.completed.push(id);info.narrationId=null;caption.textContent='';applyMix();setTimeout(pump,700);};voiceSource.start(ctx.currentTime+.12);
  }
  async function enable(){
    clearTimeout(suspendTimer);await load();await ctx.resume();info.enabled=true;info.userMuted=false;info.contextState=ctx.state;target(nodes.master.gain,volume,.12);toggle.textContent='Mute';toggle.setAttribute('aria-pressed','true');enqueue(info.mode==='reveal'?'arrival':'mode-'+info.mode);pump();return true;
  }
  function disable(){info.enabled=false;info.userMuted=true;target(nodes.master?.gain,0,.035);toggle.textContent='Enable sound';toggle.setAttribute('aria-pressed','false');suspendTimer=setTimeout(()=>{if(!info.enabled&&ctx){ctx.suspend().then(()=>info.contextState=ctx.state);}},140);}
  toggle.onclick=()=>{if(info.enabled)disable();else enable().catch(()=>{});};range.oninput=()=>{volume=Number(range.value);if(info.enabled)target(nodes.master?.gain,volume,.05);};
  function interrupt(){serial++;voiceSource?.stop();busy=false;voiceSource=null;info.narrationId=null;queue=[];queued.clear();caption.textContent='';applyMix();}
  function setMode(mode){if(info.mode===mode)return;interrupt();info.mode=mode;wasOpen=false;if(info.enabled)enqueue(mode==='reveal'?'arrival':'mode-'+mode);}
  async function replayVoice(){await enable();interrupt();voiceEnabled=true;voiceCheck.checked=true;played.clear();info.played=[];info.completed=[];wasOpen=false;enqueue(info.mode==='reveal'?'arrival':'mode-'+info.mode);}
  async function speakResearch(){await enable();interrupt();voiceEnabled=true;voiceCheck.checked=true;played.delete('research');enqueue('research');}
  replay.onclick=()=>replayVoice().catch(()=>{});
  research.onclick=()=>speakResearch().catch(()=>{});
  function update({mix=0,night=0,direction,forward,up}={}){
    const next=Math.max(0,Math.min(1,mix)),darkness=Math.max(0,Math.min(1,night));if(Math.abs(info.mix-next)>.005||Math.abs(info.night-darkness)>.005){info.mix=next;info.night=darkness;applyMix();}
    if(!info.enabled||!info.ready)return;
    if(info.mode==='reveal'&&next>.1){wasOpen=true;enqueue('reveal');}
    if(info.mode==='reveal'&&wasOpen&&next<.02)enqueue('return');
    if(direction){for(const [axis,k] of [['X',0],['Y',1],['Z',2]])target(nodes.hellPanner['position'+axis],direction[k]*4,.06);}
    const listener=ctx.listener;if(forward&&up){
      if(listener.forwardX){for(const [axis,k] of [['X',0],['Y',1],['Z',2]]){listener['forward'+axis].setValueAtTime(forward[k],ctx.currentTime);listener['up'+axis].setValueAtTime(up[k],ctx.currentTime);}}
      else listener.setOrientation(...forward,...up);
    }
  }
  function diagnostics(){let rms=0;if(nodes.analyser){const a=new Float32Array(nodes.analyser.fftSize);nodes.analyser.getFloatTimeDomainData(a);rms=Math.sqrt(a.reduce((s,v)=>s+v*v,0)/a.length);}return {...info,voiceEnabled,captionsEnabled,volume,rms,audioTime:ctx?.currentTime||0,contextState:ctx?.state||'not-started',bufferSeconds:Object.fromEntries(Object.entries(buffers).map(([k,v])=>[k,v.duration]))};}
  return {info,enable,disable,update,setMode,replayVoice,speakResearch,diagnostics,panel,caption};
}
