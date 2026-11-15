"""Fast pacing study. Reuses approved moving objects; no new long video jobs.

Season grades/particles are authored. One imagegen Hell-winter plate is used.
Recorded previews must not be described as fresh realtime model output.
"""
from pathlib import Path
import sys,json,subprocess,shutil
import cv2,numpy as np,imageio_ffmpeg
ROOT=Path(__file__).resolve().parent;LAB=ROOT.parent
OUT=LAB.parent/'handoff/garden-daynight-20261114/fast-study';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(LAB/'garden-daynight-v2'))
from compose import Projection
FF=imageio_ffmpeg.get_ffmpeg_exe();W=1280;H=640;FPS=24
def smooth(v):v=np.clip(v,0,1);return v*v*(3-2*v)
def writer(name,w,h):
 return subprocess.Popen([FF,'-y','-v','error','-f','rawvideo','-pix_fmt','bgr24','-s',f'{w}x{h}','-r',str(FPS),'-i','-','-an','-vf','scale=out_color_matrix=bt709:out_range=tv','-c:v','libx264','-preset','veryfast','-crf','18','-g','48','-keyint_min','48','-sc_threshold','0','-pix_fmt','yuv420p','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-movflags','+faststart',str(OUT/name)],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
def finish(p):
 p.stdin.close();err=p.stderr.read();rc=p.wait()
 if rc:raise RuntimeError(err.decode(errors='replace'))
def im(path):return cv2.resize(cv2.imread(str(path)),(W,H),interpolation=cv2.INTER_AREA).astype(np.float32)
def load_motion(world):
 c=cv2.VideoCapture(str(LAB/'orbis-test/delivery-v6'/f'{world}-source-motion.mp4'));frames=[];i=0
 while True:
  ok,f=c.read()
  if not ok:break
  if i%2==0:frames.append(cv2.resize(f,(W,H),interpolation=cv2.INTER_AREA))
  i+=1
 c.release();stack=np.array(frames);mean=np.zeros((H,W,3),np.float32);sq=mean.copy()
 for f in stack:
  a=f.astype(np.float32);mean+=a;sq+=a*a
 mean/=len(stack);std=np.sqrt(np.maximum(sq/len(stack)-mean*mean,0)).max(axis=2)
 mask=cv2.GaussianBlur(np.uint8(std>2.4).astype(np.float32),(0,0),.65)
 # Occlude the fixed architecture; fountains and nearby animals keep their motion.
 for box in [(195,327,419,568),(223,170,268,334),(575,300,755,416),(650,208,695,305),(819,391,971,568),(874,161,927,391),(1040,286,1208,426),(1404,290,1561,569)]:
  x0,y0,x1,y1=box;mask[round(y0*H/887):round(y1*H/887),round(x0*W/1774):round(x1*W/1774)]=0
 cv2.imwrite(str(OUT/f'{world}-motion-mask.png'),np.uint8(mask*255))
 return stack,mask
def seasonal_plates(base,world):
 hsv=cv2.cvtColor(np.uint8(base),cv2.COLOR_BGR2HSV);h,s,v=cv2.split(hsv)
 yy,xx=np.mgrid[0:H,0:W];allowed=yy>340*H/887
 for x0,y0,x1,y1 in [(96,289,195,409),(282,152,377,275),(104,95,180,185),(1000,178,1155,292)]:
  allowed|=(xx>x0*W/1774)&(xx<x1*W/1774)&(yy>y0*H/887)&(yy<y1*H/887)
 vegetation=((h>20)&(h<85)&(s>35)&allowed).astype(np.float32)
 vegetation=cv2.GaussianBlur(vegetation,(0,0),1.2)
 if world=='garden':
  spring=base*np.array([.99,1.04,.99],np.float32)
  summer=base*np.array([.92,1.01,1.08],np.float32)
  l=cv2.cvtColor(np.uint8(base),cv2.COLOR_BGR2GRAY).astype(np.float32)
  autumn=base*(1-vegetation[...,None]*.72)+np.stack([l*.43,l*.78,l*1.23],axis=2)*vegetation[...,None]*.72
  winter=base*np.array([1.09,1.02,.94],np.float32)
  frost=np.stack([170+l*.31,173+l*.31,169+l*.31],axis=2)
  winter=winter*(1-vegetation[...,None]*.87)+frost*vegetation[...,None]*.87
 else:
  spring=base*np.array([1.37,1.36,1.19],np.float32)+np.array([8,9,7],np.float32)
  summer=base*np.array([.94,1.09,1.26],np.float32)+3
  autumn=base*np.array([1.53,1.33,1.16],np.float32)+np.array([12,8,4],np.float32)
  winter=im(ROOT/'hell-winter.png')
 return [np.clip(x,0,255) for x in (spring,summer,autumn,winter)]
rng=np.random.default_rng(42);particles=rng.random((150,5))
def weather(frame,t,season,world):
 # Explicit post-production weather; trajectories have no random gusts.
 out=frame.copy();weights=np.array([max(0,1-min(abs(season-i),4-abs(season-i))) for i in range(4)])
 for j,p in enumerate(particles):
  x=int((p[0]*W+t*(9+p[3]*7))%W);y=int((p[1]*H+t*(30+p[2]*40))%H)
  if weights[3]>.02:
   a=weights[3]*.65;col=np.array([230,235,234]);r=1+int(p[4]>.8)
   cv2.circle(out,(x,y),r,tuple(float(v) for v in col),-1,cv2.LINE_AA)
  elif weights[2]>.05:
   if world=='hell':cv2.line(out,(x,y),(x+2,y+13),tuple(float(v) for v in (145,154,157)),1,cv2.LINE_AA)
   elif j<65:cv2.ellipse(out,(x,y),(3,1),float((t*85+j*25)%180),0,360,(55,135,210),-1,cv2.LINE_AA)
  elif weights[0]>.25 and world=='garden' and j<38:
   cv2.circle(out,(x,y),1,(191,193,236),-1,cv2.LINE_AA)
 # Fade particles with the season weight; do not let them pop at boundaries.
 a=float(max(weights[0]*.5,weights[2]*.78,weights[3]*.9))
 return frame*(1-a)+out*a
def make(world,kind,stack,mask,base):
 duration=12 if kind=='light' else 8
 plates=seasonal_plates(base,world)
 if kind=='light':
  day=base if world=='garden' else np.clip(base*np.array([1.6,1.48,1.24],np.float32)+np.array([18,14,8],np.float32),0,255)
  night=im(LAB/'garden-daynight-v2/references/night-imagegen.png') if world=='garden' else np.clip(base*np.array([1.10,.91,.87],np.float32),0,255)
  anchors=[day,night]
 else:anchors=plates;day,night=plates[0],plates[3]
 projection=Projection(day,night,w=1536);name=f'{world}-{kind}'
 native=writer(name+'-flat.mp4',W,H);pano=writer(name+'-panorama.mp4',1536,768)
 reference=stack[0].astype(np.float32);contacts=[];active=0
 for i in range(duration*FPS):
  t=i/FPS
  if kind=='light':
   a=float((1-np.cos(2*np.pi*t/12))/2);plate=day*(1-a)+night*a;season=None
  else:
   season=t/2;index=int(season)%4;a=float(smooth(season%1));plate=anchors[index]*(1-a)+anchors[(index+1)%4]*a
  # Two complete approved object cycles in every 8-second seasonal preview.
  p=(t*2%8)*15;j=int(p)%len(stack);f=stack[j].astype(np.float32)*(1-(p-int(p)))+stack[(j+1)%len(stack)].astype(np.float32)*(p-int(p))
  gain=np.clip(cv2.GaussianBlur(plate,(0,0),2)/(cv2.GaussianBlur(base,(0,0),2)+8),.35,2)
  delta=(f-reference)*gain*mask[...,None]*1.1
  image=np.clip(plate+delta,0,255)
  if kind=='season':image=weather(image,t,season,world)
  image=np.uint8(np.clip(np.round(image),0,255))
  capmix=a if kind=='light' else float(.5-.5*np.cos(2*np.pi*t/8))
  native.stdin.write(image.tobytes());pano.stdin.write(projection.render(image,capmix).tobytes())
  if i in (0,int(duration*FPS/4),int(duration*FPS/2),int(duration*FPS*3/4)):
   tile=cv2.resize(image,(640,320));cv2.rectangle(tile,(0,0),(640,28),(18,25,20),-1);cv2.putText(tile,f'{world} {kind} / {t:.1f}s',(10,20),cv2.FONT_HERSHEY_SIMPLEX,.5,(230,235,220),1,cv2.LINE_AA);contacts.append(tile)
  if i%96==0:print(name,i,'/',duration*FPS,flush=True)
 finish(native);finish(pano);cv2.imwrite(str(OUT/(name+'-contact.jpg')),np.vstack(contacts))
 return {'id':name,'world':world,'kind':kind,'seconds':duration,'transition_seconds':6 if kind=='light' else 2,'flat':name+'-flat.mp4','panorama':name+'-panorama.mp4','source_object_motion':'r4 approved 8s object loop, 2x playback','live_generation':False}
def overview(jobs,stacks):
 captures={j['id']:cv2.VideoCapture(str(OUT/j['flat'])) for j in jobs}
 p=writer('overview-19s-silent.mp4',1280,720);yy,xx=np.mgrid[0:H,0:W]
 previous={};labels={'garden':'Garden','hell':'Aftermath'}
 for i in range(19*FPS):
  t=i/FPS;canvas=np.full((720,1280,3),(18,25,20),np.uint8)
  if t<7:
   idx=int((t*2%8)*15)%len(stacks['garden']);g=stacks['garden'][idx];h=stacks['hell'][idx]
   open=float(smooth((t-.7)/.8)*(1-smooth((t-5.8)/.9)))
   cx=W*(.56+.16*np.sin(t*.65));cy=H*.53
   dist=np.sqrt(((xx-cx)/(W*.18))**2+((yy-cy)/(H*.36))**2)
   lens=(1-smooth((dist-.78)/.23))*open
   image=np.uint8(g*(1-lens[...,None])+h*lens[...,None]);canvas[64:704]=image
   cv2.putText(canvas,'1 / REVEAL — the main interaction',(22,31),cv2.FONT_HERSHEY_SIMPLEX,.72,(234,240,224),1,cv2.LINE_AA)
   cv2.putText(canvas,'Recorded reveal illustration; use the original demo for live gestures.',(22,54),cv2.FONT_HERSHEY_SIMPLEX,.43,(186,206,180),1,cv2.LINE_AA)
  else:
   kind='light' if t<13 else 'season';local=t-(7 if kind=='light' else 13)
   cv2.putText(canvas,'2 / DAY AND NIGHT — 6 seconds' if kind=='light' else '3 / SEASONS — a quick passage through time',(22,38),cv2.FONT_HERSHEY_SIMPLEX,.7,(234,240,224),1,cv2.LINE_AA)
   for k,world in enumerate(('garden','hell')):
    cap=captures[world+'-'+kind];ok,f=cap.read()
    if ok:previous[world+'-'+kind]=f
    f=previous[world+'-'+kind];tile=cv2.resize(f,(640,320));x=k*640;canvas[180:500,x:x+640]=tile
    cv2.putText(canvas,labels[world],(x+20,160),cv2.FONT_HERSHEY_SIMPLEX,.7,(211,229,201),1,cv2.LINE_AA)
   cv2.putText(canvas,'Fixed viewpoint / existing object motion / composed preview',(22,550),cv2.FONT_HERSHEY_SIMPLEX,.55,(186,206,180),1,cv2.LINE_AA)
  p.stdin.write(canvas.tobytes())
 finish(p)
 for cap in captures.values():cap.release()
def sound():
 def dec(p):return np.frombuffer(subprocess.run([FF,'-v','error','-i',str(p),'-f','f32le','-ar','48000','-ac','2','pipe:1'],capture_output=True,check=True).stdout,np.float32).reshape(-1,2).copy()
 n=19*48000;bed=dec(LAB/'audio-v1/delivery/music.mp3')[:n];bed*=.032/max(float(np.sqrt(np.mean(bed*bed))),1e-5)
 voice=dec(LAB/'audio-v1/delivery/reveal.mp3');voice*=.085/max(float(np.sqrt(np.mean(voice*voice))),1e-5);start=48000
 bed[start:start+len(voice)]*=.4;bed[start:start+len(voice)]+=voice
 r=subprocess.run([FF,'-y','-v','error','-f','f32le','-ar','48000','-ac','2','-i','pipe:0','-c:a','libmp3lame','-b:a','192k',str(OUT/'overview-sound.en.mp3')],input=bed.astype(np.float32).tobytes(),capture_output=True,check=True)
 subprocess.run([FF,'-y','-v','error','-i',str(OUT/'overview-19s-silent.mp4'),'-i',str(OUT/'overview-sound.en.mp3'),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-t','19','-movflags','+faststart',str(OUT/'overview-19s.mp4')],check=True)
def main():
 stacks={};jobs=[];selected=set(sys.argv[1:]);existing={}
 if selected:existing={j['id']:j for j in json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))['modes']}
 for world in ('garden','hell'):
  stack,mask=load_motion(world);stacks[world]=stack;base=im(LAB/'bosch-world-assets'/f'{world}-generated.png')
  for kind in ('light','season'):
   name=world+'-'+kind
   jobs.append(make(world,kind,stack,mask,base) if not selected or name in selected else existing[name])
 overview(jobs,stacks);sound()
 shutil.copy2(LAB.parent/'handoff/bosch-demo-20261114/r4/media/paired.mp4',OUT/'reveal-packed.mp4')
 m={'title':'Fast time studies','overview_seconds':19,'outline':[{'seconds':[0,7],'mode':'Reveal, recorded illustration'},{'seconds':[7,13],'mode':'Day / Night, two worlds'},{'seconds':[13,19],'mode':'Seasons, two worlds'}],'modes':jobs,'primary_narrative':'Original live Reveal remains the main interaction.','production_reveal_modified':False,'new_video_model_calls':0,'method':'Quick hybrid pacing study. Existing Orbis captures and authored object animation reused from r4. Time-of-day grades, weather particles and season transitions are authored. One imagegen winter aftermath reference.','not_a_live_model_connection':True,'headset_verified':False}
 (OUT/'manifest.json').write_text(json.dumps(m,indent=2),encoding='utf-8');print(json.dumps({'folder':str(OUT),'modes':4,'overview_seconds':19}),flush=True)
if __name__=='__main__':main()
