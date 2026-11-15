import { Reactor } from '@reactor-team/js-sdk';

// Only this opt-in route loads the SDK. The stable player never mints a token.
export function createLiveSession({broker,getCode,onVideo,onChange,onFreeze}){
  const info={phase:'idle',model:'reactor/visko-orbis-dynamic',frames:0,events:[],commands:[],live:false,error:null,sessionId:null};
  let client=null,lease=null,timer,heartbeat,stopping=false,available=[],generationReady=false;
  const stamp=()=>new Date().toISOString();
  function changed(){onChange?.({...info});}
  async function rpc(route,data={}){const r=await fetch(broker+route,{method:'POST',headers:{'content-type':'application/json','x-live-code':getCode()},body:JSON.stringify(data)});const b=await r.json();if(!r.ok)throw Error(b.error||'Live service '+r.status);return b;}
  function event(type,data={}){const e={type,at:stamp(),...data};info.events.push(e);if(info.events.length>100)info.events.shift();changed();return e;}
  async function command(name,data){const e={command:name,sent_at:stamp(),...(name==='set_prompt'?{prompt:data.prompt}:{})};info.commands.push(e);const reply=await client.sendCommand(name,data);e.returned_at=stamp();e.reply=reply?.type;changed();return reply;}
  async function anchor(reference,prompt){
    if(!client||stopping)throw Error('Start Live first');
    generationReady=false;info.phase='anchoring';info.live=false;onFreeze?.();changed();
    await command('reset',{});
    if(available.includes('1080p'))await command('set_resolution',{resolution:'1080p'});
    const r=await fetch(reference);if(!r.ok)throw Error('Missing scene reference');
    const file=await client.uploadFile(new File([await r.blob()],'scene-reference.jpg',{type:'image/jpeg'}));
    await command('set_image',{image:file});
    await command('set_prompt',{prompt,passthrough:true});
    await command('start',{});info.phase='priming';changed();
  }
  async function start(reference,prompt){
    if(client||lease)throw Error('A session is already active');info.error=null;info.phase='connecting';changed();
    try{
      lease=await rpc('/v1/lease');client=new Reactor({modelName:lease.model});
      client.on('message',m=>{const d=m?.data||{};if(m?.type==='state'){const state=d.state||d;available=state.available_resolutions||available;}
        if(['prompt_accepted','generation_started','generation_complete','chunk_complete','command_error'].includes(m?.type)){
          event(m.type,m.type==='chunk_complete'?{frames_emitted:d.frames_emitted,delivered:d.delivered}:{});
          if(m.type==='prompt_accepted')info.prompt_accepted_at=stamp();
          if(m.type==='chunk_complete'&&d.frames_emitted>0)info.chunk_received_at=stamp();
          if(m.type==='chunk_complete'&&d.frames_emitted>0)generationReady=true;
          if(m.type==='command_error'){info.error=String(d.message||d.code||'Model command rejected');changed();}
          if(m.type==='generation_complete'){info.phase='generation-ended';info.live=false;onFreeze?.();changed();}
        }});
      client.on('error',e=>{info.error=String(e.message||e.code||'Live connection error');changed();});
      client.on('trackReceived',(name,track,stream)=>{if(name==='main_video')onVideo(stream,()=>{if(!generationReady||!['priming','streaming'].includes(info.phase))return;info.frames++;info.last_frame_at=stamp();if(!info.live){info.live=true;info.phase='streaming';event('first_received_frame');}changed();});});
      await client.connect(lease.jwt);
      info.sessionId=client.getSessionId();await rpc('/v1/lease/'+lease.lease_id+'/register',{session_id:info.sessionId});
      heartbeat=setInterval(()=>{if(lease)rpc('/v1/lease/'+lease.lease_id+'/heartbeat').catch(()=>{info.error='Live operator connection interrupted';changed();});},10000);
      info.started_at=stamp();info.ends_at=new Date(Date.now()+lease.max_session_seconds*1000).toISOString();timer=setTimeout(()=>stop(),(lease.max_session_seconds-2)*1000);
      await anchor(reference,prompt);
    }catch(e){info.error=e.message;await stop();info.phase=/capacity|429|already reserved/i.test(e.message)?'busy':'error';changed();throw e;}
  }
  async function steer(prompt){if(!client||!info.live)throw Error('Wait for live frames before sending a change');const previous=info.commands.at(-1);if(previous?.command==='set_prompt'&&Date.now()-Date.parse(previous.sent_at)<3500)throw Error('Allow a few seconds between changes');await command('set_prompt',{prompt,passthrough:true});event('prompt_sent');}
  async function stop(){if(stopping)return;stopping=true;clearTimeout(timer);clearInterval(heartbeat);onFreeze?.();const old=client,oldLease=lease;client=null;lease=null;await Promise.allSettled([Promise.race([old?.disconnect(),new Promise(r=>setTimeout(r,8000))]),oldLease?rpc('/v1/lease/'+oldLease.lease_id+'/stop'):Promise.resolve()]);info.live=false;info.phase='stopped';info.sessionId=null;stopping=false;changed();}
  window.addEventListener('pagehide',()=>{if(lease)fetch(broker+'/v1/lease/'+lease.lease_id+'/stop',{method:'POST',headers:{'content-type':'application/json','x-live-code':getCode()},body:'{}',keepalive:true}).catch(()=>{});client?.disconnect().catch(()=>{});});
  return{info,start,stop,anchor,steer};
}
