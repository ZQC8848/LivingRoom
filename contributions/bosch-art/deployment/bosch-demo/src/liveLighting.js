import * as THREE from 'three';

const clamp=THREE.MathUtils.clamp;
const linear=x=>x<=.04045?x/12.92:Math.pow((x+.055)/1.055,2.4);
const luma=c=>c[0]*.2126+c[1]*.7152+c[2]*.0722;
const ratio=(a,b,min=.12,max=5)=>a.map((x,i)=>clamp(x/Math.max(b[i],.006),min,max));

// Estimates light from actual received pixels, never from a prompt or weather button.
// This is authored colour/exposure compositing, not a physical lighting simulation.
export function createLiveLighting(uniforms,plate){
 const canvas=Object.assign(document.createElement('canvas'),{width:48,height:28});
 const ctx=canvas.getContext('2d',{willReadFrequently:true});
 const info={samples:0,enabled:true,gain:1,error:null,source:'received video pixels',reference:null,current:null};
 let reference=null,plateSky=[.13,.15,.13],plateGround=[.1,.12,.025],lastRead=-Infinity;
 const target={gain:1,tint:[1,1,1],sky:plateSky,ground:plateGround};
 function sample(image,top,bottom){
  ctx.drawImage(image,0,0,48,28);const y=Math.max(0,Math.floor(28*top)),height=Math.max(1,Math.ceil(28*bottom)-y);
  const bytes=ctx.getImageData(0,y,48,Math.min(height,28-y)).data,channels=[[],[],[]];
  for(let n=0;n<bytes.length;n+=4)for(let c=0;c<3;c++)channels[c].push(bytes[n+c]/255);
  return channels.map(values=>{values.sort((a,b)=>a-b);const trim=Math.floor(values.length*.1),slice=values.slice(trim,values.length-trim);return linear(slice.reduce((s,v)=>s+v,0)/slice.length);});
 }
 function setPlate(image){
  try{plateSky=sample(image,.025,.18);plateGround=sample(image,.9,.98);}catch(error){info.error=error.message;}
  reset();
 }
 function reset(){reference=null;lastRead=-Infinity;info.samples=0;info.reference=null;info.current=null;info.error=null;info.gain=1;target.gain=1;target.tint=[1,1,1];target.sky=plateSky;target.ground=plateGround;
  uniforms.uLightGain.value=1;uniforms.uLightTint.value.set(1,1,1);uniforms.uSkyPole.value.fromArray(plateSky);uniforms.uGroundPole.value.fromArray(plateGround);uniforms.uSkyGrade.value.set(1,1,1);uniforms.uGroundGrade.value.set(1,1,1);
 }
 function readFrame(video,time){
  if(time-lastRead<350||video.readyState<2||!video.videoWidth)return;lastRead=time;
  try{
   const sky=sample(video,.15,.35),ground=sample(video,.82,.9);
   if(!reference){reference={sky,ground};info.reference=structuredClone(reference);uniforms.uSkyGrade.value.fromArray(ratio(plateSky,sky));uniforms.uGroundGrade.value.fromArray(ratio(plateGround,ground));}
   const relative=luma(sky)/Math.max(luma(reference.sky),.012);
   target.gain=clamp(Math.pow(relative,1.2),.38,1.3);
   const whiteBalance=ratio(sky,reference.sky,.05,20).map(v=>clamp(v/Math.max(relative,.08),.65,1.55));
   target.tint=whiteBalance.map(v=>1+(v-1)*.42);
   target.sky=sky.map((v,i)=>v*uniforms.uSkyGrade.value.toArray()[i]);target.ground=ground.map((v,i)=>v*uniforms.uGroundGrade.value.toArray()[i]);
   uniforms.uSkyLuma.value=Math.max(luma(sky),.01);info.samples++;info.current={sky,ground,relative_luminance:relative,target_gain:target.gain};info.error=null;
  }catch(error){info.error=error.message;}
 }
 function update(dt){const a=1-Math.exp(-Math.min(dt,.1)*2.1);
  uniforms.uRelight.value=info.enabled?1:0;
  uniforms.uLightGain.value=THREE.MathUtils.lerp(uniforms.uLightGain.value,target.gain,a);
  const to=new THREE.Vector3();uniforms.uLightTint.value.lerp(to.fromArray(target.tint),a);uniforms.uSkyPole.value.lerp(to.fromArray(target.sky),a);uniforms.uGroundPole.value.lerp(to.fromArray(target.ground),a);info.gain=uniforms.uLightGain.value;
 }
 setPlate(plate);
 return{info,setPlate,reset,readFrame,update,setEnabled:value=>{info.enabled=Boolean(value)}};
}
