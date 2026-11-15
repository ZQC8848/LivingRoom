"""30s fixed-viewpoint HYBRID loop plus honest re-anchor evidence recording.

Imagegen: aligned night plate. Orbis: fresh day/night water variation. Fixed
plates retain geometry; only bounded temporal luminance enters the water matte.
The 30s presentation is authored playback, not an active model connection.
"""
from pathlib import Path
import json,sys,subprocess,shutil,hashlib
import cv2,numpy as np,imageio_ffmpeg
ROOT=Path(__file__).resolve().parent;LAB=ROOT.parent
OUT=LAB.parent/'handoff/garden-daynight-20261114';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(LAB))
from package_bosch_live_modes import encode
FF=imageio_ffmpeg.get_ffmpeg_exe();W=1776;H=888;FPS=30;N=900
def smooth(a,b,x):
    v=np.clip((x-a)/(b-a),0,1);return v*v*(3-2*v)
def band(im,width=1280):
    h,w=im.shape[:2];return cv2.resize(im[round(h*48/736):round(h*688/736)],(width,width//2),interpolation=cv2.INTER_AREA)
def writer(path,w,h,fps=FPS):
    return subprocess.Popen([FF,'-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{w}x{h}','-r',str(fps),'-i','-','-an','-vf','scale=out_color_matrix=bt709:out_range=tv','-c:v','libx264','-preset','fast','-crf','17','-g','60','-keyint_min','60','-sc_threshold','0','-pix_fmt','yuv420p','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-movflags','+faststart',str(path)],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
def finish(p):
    p.stdin.close();err=p.stderr.read();rc=p.wait()
    if rc:raise RuntimeError(err.decode(errors='replace')[-800:])
class Projection:
    def __init__(self,day,night,w=2048):
        self.w=w;self.h=w//2;sh,sw=day.shape[:2]
        u=(np.arange(w,dtype=np.float32)+.5)/w;lat=(.5-(np.arange(self.h,dtype=np.float32)+.5)/self.h)*np.pi
        angle=np.deg2rad(64);feather=np.deg2rad(6)
        y=.36-np.tan(np.clip(lat,-angle,angle))/np.tan(angle)*np.where(lat>=0,.36,.64)
        self.mx=np.broadcast_to((u*sw-.5)[None,:],(self.h,w)).copy()
        self.my=np.broadcast_to((np.clip(y,.001,.999)*sh-.5)[:,None],(self.h,w)).astype(np.float32).copy()
        self.edge=(1-smooth(angle-feather,angle,np.abs(lat)))[:,None,None]
        k=np.clip((np.abs(lat)-angle+feather)/(np.pi*.5-angle+feather),0,1)
        self.caps=[]
        for im in (day,night):
            sky=im[:round(sh*.04)].mean(axis=(0,1));earth=im[round(sh*.96):].mean(axis=(0,1))
            cap=np.where((lat>=0)[:,None],sky[None,:],earth[None,:])*(1-.16*smooth(0,1,k))[:,None]
            self.caps.append(np.broadcast_to(cap[:,None,:],(self.h,w,3)).astype(np.float32))
        p=np.where(u<.5,u,u-1);self.cols=np.flatnonzero(np.abs(p)<.015)
        self.lx=np.broadcast_to((np.clip(1+p[self.cols],.985,.9999)*sw-.5)[None,:],(self.h,len(self.cols))).astype(np.float32).copy()
        self.rx=np.broadcast_to((np.clip(p[self.cols],.0001,.015)*sw-.5)[None,:],(self.h,len(self.cols))).astype(np.float32).copy()
        self.sy=self.my[:,self.cols].copy();self.mix=smooth(-.015,.015,p[self.cols])[None,:,None]
    def render(self,im,a):
        f=cv2.remap(im,self.mx,self.my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
        left=cv2.remap(im,self.lx,self.sy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
        right=cv2.remap(im,self.rx,self.sy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
        f[:,self.cols]=left*(1-self.mix)+right*self.mix
        cap=self.caps[0]*(1-a)+self.caps[1]*a
        return np.uint8(np.clip(np.round(cap*(1-self.edge)+f*self.edge),0,255))
def motion_fields(folder):
    r=json.loads((folder/'report.json').read_text(encoding='utf-8'))
    paths=sorted((folder/'frames').glob('*.jpg'))[:r['frames']]
    ts=np.array(r['frame_timestamps']);ts-=ts[0]
    # A 6s model excerpt with 1s overlap yields a 5s cyclic motion field.
    sample=np.arange(48)/8+2
    fields=[]
    for t in sample:
        i=int(np.argmin(np.abs(ts-t)));im=band(cv2.imread(str(paths[i])))
        l=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY).astype(np.float32)
        fields.append(l-cv2.GaussianBlur(l,(0,0),2.3))
    fields=np.array(fields);fields-=fields.mean(axis=0,keepdims=True)
    # No artificial flow: only the model's temporal water-detail residual.
    cyclic=list(fields[8:40])
    for i in range(8):
        a=float(smooth(0,1,i/8));cyclic.append(fields[40+i]*(1-a)+fields[i]*a)
    return np.array(cyclic,dtype=np.float16),r,paths
def sample_field(fields,t):
    p=(t%5)*8;i=int(p);a=p-i
    return fields[i%40].astype(np.float32)*(1-a)+fields[(i+1)%40].astype(np.float32)*a
def raw_evidence():
    root_report=json.loads((ROOT/'capture-report.json').read_text(encoding='utf-8'))
    phase_data=[]
    for r in root_report['phases']:
        folder=Path(r['folder']);paths=sorted((folder/'frames').glob('*.jpg'))[:r['frames']]
        times=r['frame_timestamps'];encode(paths,times,OUT/f"raw-{r['id']}.mp4")
        phase_data.append((r,paths,np.array(times)))
    # Show real waits and accepted requests. The status strip is authored UI.
    start=phase_data[0][2][0];end=phase_data[-1][2][-1];p=writer(OUT/'reanchor-evidence.mp4',960,540,24)
    last=None
    for n in range(round((end-start)*24)):
        t=start+n/24;active=phase_data[0]
        for v in phase_data:
            if t>=v[0]['request_t']:active=v
        r,paths,ts=active;waiting=t<ts[0]
        if not waiting:
            i=max(0,min(len(paths)-1,int(np.searchsorted(ts,t,side='right')-1)))
            im=band(cv2.imread(str(paths[i])),960);last=im
        elif last is None:last=band(cv2.imread(str(paths[0])),960)
        canvas=np.full((540,960,3),(19,25,21),np.uint8);canvas[60:]=last
        cv2.putText(canvas,'SCRIPTED RE-ANCHOR TEST / ACTUAL STREAM RECORDING',(12,23),cv2.FONT_HERSHEY_SIMPLEX,.49,(228,239,225),1,cv2.LINE_AA)
        status=f"Request: {r['reference'].upper()} | "+('generating; previous frame held' if waiting else 'new generated frames')
        cv2.putText(canvas,status,(12,47),cv2.FONT_HERSHEY_SIMPLEX,.47,(205,222,201),1,cv2.LINE_AA)
        p.stdin.write(canvas.tobytes())
    finish(p)
    return root_report
def main():
    day=cv2.resize(cv2.imread(str(ROOT/'references/day-original.png')),(W,H),interpolation=cv2.INTER_CUBIC).astype(np.float32)
    night=cv2.resize(cv2.imread(str(ROOT/'references/night-imagegen.png')),(W,H),interpolation=cv2.INTER_CUBIC).astype(np.float32)
    alpha=cv2.imread(str(LAB/'orbis-test/delivery-v6/whole-river-matte.png'),0)
    alpha=cv2.resize(alpha,(W,H),interpolation=cv2.INTER_AREA)
    hard=cv2.erode(np.uint8(alpha>200)*255,np.ones((7,7),np.uint8))
    dist=cv2.distanceTransform(hard,cv2.DIST_L2,3);mask=np.clip(dist/4,0,1).astype(np.float32)
    cv2.imwrite(str(OUT/'motion-water-mask.png'),np.uint8(mask*255))
    day_fields,dr,_=motion_fields(ROOT/'captures/day');night_fields,nr,_=motion_fields(ROOT/'captures/night')
    projector=Projection(day,night)
    native=writer(OUT/'garden-daynight-30s-flat.mp4',W,H);pano=writer(OUT/'garden-daynight-30s-panorama.mp4',2048,1024)
    leak=0;max_seam=0;contact=[]
    try:
        for i in range(N):
            t=i/FPS;a=float(smooth(3,12,t)*(1-smooth(18,27,t)))
            base=day*(1-a)+night*a
            delta=sample_field(day_fields,t)*(1-a)+sample_field(night_fields,t)*a
            delta=cv2.resize(delta,(W,H),interpolation=cv2.INTER_LINEAR)
            delta=np.tanh(delta/8)*9*mask
            f=np.uint8(np.clip(np.round(base+delta[...,None]),0,255))
            if i in (0,90,240,450,660,810,899):
                expected=np.uint8(np.clip(np.round(base),0,255))
                leak=max(leak,int(np.max(np.abs(f.astype(np.int16)-expected.astype(np.int16))[mask==0])))
            projected=projector.render(f,a);native.stdin.write(f.tobytes());pano.stdin.write(projected.tobytes())
            max_seam=max(max_seam,int(np.max(np.abs(projected[:,0].astype(np.int16)-projected[:,-1].astype(np.int16)))))
            if i in (0,240,450,660):
                tile=cv2.resize(f,(888,444));cv2.rectangle(tile,(0,0),(888,35),(19,25,21),-1)
                cv2.putText(tile,f'{t:.0f}s / night mix {a:.2f}',(12,25),cv2.FONT_HERSHEY_SIMPLEX,.6,(235,240,230),1,cv2.LINE_AA);contact.append(tile)
            if i%150==0:print('Loop frame',i,'/',N,flush=True)
        finish(native);finish(pano)
    finally:
        for p in (native,pano):
            if p.poll() is None:p.kill()
    cv2.imwrite(str(OUT/'loop-contact.jpg'),np.vstack(contact),[cv2.IMWRITE_JPEG_QUALITY,94])
    actual=json.loads((ROOT/'capture-report.json').read_text(encoding='utf-8')) if (OUT/'reanchor-evidence.mp4').exists() else raw_evidence()
    for label in ['day-original','night-imagegen']:
        shutil.copy2(ROOT/'references'/f'{label}.png',OUT/f'{label}.png')
    shutil.copy2(ROOT/'reference-check.json',OUT/'reference-check.json')
    save={'kind':'Authored 30-second fixed-viewpoint hybrid loop','seconds':30,'fps':30,'frames':N,
          'camera_transform':'Constant approved panorama mapping; no frame-dependent camera transform.',
          'plates':'Original day + imagegen night relighting reference. Matched feature median shift about 1 original pixel.',
          'model_role':'Fresh Orbis day/night temporal water-detail variation, constrained by the water matte. Full raw model geometry is excluded.',
          'authored_parts':['day/night dissolve timing','fixed structural plates','bounded water compositing','cyclic overlap','sky/floor projection and rear-seam feather'],
          'motion_changed_values_outside_water_mask':leak,'maximum_rear_seam_channel_delta':max_seam,
          'not_live_playback':True,'live_evidence':'reanchor-evidence.mp4',
          'reanchor_latency_seconds':{p['id']:p['first_frame_latency_seconds'] for p in actual['phases']},
          'raw_model_limitation':'Re-anchor preserves time-of-day but does not guarantee intact architecture; raw captures still reinterpret buildings.',
          'headset_verified':False,'production_reveal_modified':False,'owned_session_disconnected':actual.get('owned_session_disconnected',False)}
    if leak:raise ValueError('Water variation leaked onto fixed plates')
    (OUT/'manifest.json').write_text(json.dumps(save,indent=2),encoding='utf-8')
    shutil.copy2(ROOT/'capture-report.json',OUT/'capture-report.json')
    print(json.dumps(save,indent=2),flush=True)
if __name__=='__main__':main()
