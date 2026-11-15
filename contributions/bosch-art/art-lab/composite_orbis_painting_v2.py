"""Lock the approved painting, retaining only constrained Orbis-derived motion.

Water/fire: use generated local temporal luminance, preserving source color/detail.
Leaves: stabilize the generated crop, transfer its bounded optical flow to original
painted pixels. Dynamic animal RGB patches are registered and pasted within expanded masks.
No analytic/procedural animation is substituted for generated video.
"""
from pathlib import Path
import json,math,subprocess
import cv2
import numpy as np
from PIL import Image,ImageStat
import imageio_ffmpeg
from analyze_orbis_painting import registration

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'orbis-test'
DELIVERY=OUT/'delivery-v2'
DELIVERY.mkdir(exist_ok=True)
JOBS={j['id']:j for j in json.loads((OUT/'jobs.json').read_text(encoding='utf-8'))}
SELECTED={'water':'run-stable-02','leaves':'run-dynamic-v2','horse':'run-dynamic-v2','bird':'run-dynamic-v2','fire':'run-stable-01'}
N=108;FPS=18

def encode_frames(frames,target,width=None,crf=20):
    h,w=frames[0].shape[:2]
    cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{w}x{h}','-r',str(FPS),'-i','-','-an']
    if width:cmd+=['-vf',f'scale={width}:-2:flags=lanczos']
    cmd+=['-c:v','libx264','-preset','fast','-crf',str(crf),'-pix_fmt','yuv420p','-movflags','+faststart',str(target)]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        for f in frames:p.stdin.write(np.ascontiguousarray(f,dtype=np.uint8).tobytes())
    finally:p.stdin.close()
    if p.wait()!=0:raise RuntimeError('Video encoding failed: '+str(target))

def source_rgb(layer):return np.asarray(Image.open(ROOT/'bosch-world-assets'/f'{layer}-generated.png').convert('RGB'))

def motion_source(name,run):
    job=JOBS[name];folder=OUT/name/run
    paths=sorted((folder/'frames').glob('*.jpg'))
    original=np.asarray(Image.open(OUT/name/'reference.png').convert('RGB'))
    mask=np.asarray(Image.open(OUT/name/'context-mask.png'))
    static=np.where(mask>2,0,255).astype('uint8')
    selected=[];registrations=[]
    last_matrix=None
    for i in (np.linspace(0, min(len(paths)-1,107),55).astype(int) if name in ('horse','bird','leaves') else range(18,73)):
        rgb=np.asarray(Image.open(paths[i]).convert('RGB'))
        if name!='water':
            matrix,metric=registration(original,rgb,static)
            if matrix is None:
                if last_matrix is None:raise ValueError(f'{name} frame {i} cannot be stabilized')
                matrix=last_matrix
            else:last_matrix=matrix
            rgb=cv2.warpAffine(rgb,matrix,(1024,576),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)
            registrations.append(metric)
        selected.append(rgb)
    # Forward/backward loop. Reversal is post-production, not a model loop claim.
    indices=list(range(55))+list(range(53,0,-1))
    assert len(indices)==N
    x0,y0,x1,y1=job['crop'];cw,ch=x1-x0,y1-y0
    if name in ('horse','bird'):
        values=[cv2.resize(selected[i],(cw,ch),interpolation=cv2.INTER_AREA) for i in indices]
        mode='Dynamic RGB, background registration and expanded motion envelope'
    elif name=='leaves':
        gray=[cv2.cvtColor(cv2.resize(f,(512,288)),cv2.COLOR_RGB2GRAY) for f in selected]
        fields=[]
        for g in gray:
            flow=cv2.calcOpticalFlowFarneback(gray[0],g,None,.5,3,19,3,5,1.2,0)
            # Source crop displacement: amplified 4x and bounded to 7 native source pixels.
            flow=cv2.resize(flow,(cw,ch),interpolation=cv2.INTER_LINEAR)
            flow[...,0]*=cw/512;flow[...,1]*=ch/288
            flow=cv2.GaussianBlur(flow,(0,0),1.4)*4.0
            length=np.maximum(1.,np.linalg.norm(flow,axis=2)/7.0)
            fields.append(flow/length[...,None])
        values=[fields[i] for i in indices]
        mode='stabilized Orbis optical flow, amplified 4x, bounded to 7 native pixels, applied to original painting'
    else:
        lum=np.array([cv2.cvtColor(cv2.resize(f,(cw,ch)),cv2.COLOR_RGB2GRAY).astype('float32') for f in selected])
        # Remove frame-wide exposure drift; preserve only local time variation.
        residual=lum-lum.mean(axis=0,keepdims=True)
        residual-=residual.mean(axis=(1,2),keepdims=True)
        # Bound change in source RGB to a few code values, not a new scene patch.
        amplitude=7. if name=='water' else 12.
        residual=np.clip(residual*.65,-amplitude,amplitude)
        values=[residual[i] for i in indices]
        mode='Orbis temporal luminance transferred onto original painting; generated geometry discarded'
    result=dict(id=name,run=run,mode=mode,registrations=registrations,raw_whole_frame_accepted=False,animal_motion_accepted=True if name in ('horse','bird') else None)
    return job,values,result

def smoothstep(a,b,x):
    t=np.clip((x-a)/(b-a),0,1)
    return t*t*(3-2*t)

class Panorama:
    def __init__(self,layer,width=2048):
        self.w=width;self.h=width//2
        im=source_rgb(layer);sh,sw=im.shape[:2]
        u=(np.arange(self.w,dtype='float32')+.5)/self.w
        lat=(.5-(np.arange(self.h,dtype='float32')+.5)/self.h)*np.pi
        band=np.deg2rad(64);feather=np.deg2rad(6)
        y=.36-np.tan(np.clip(lat,-band,band))/np.tan(band)*np.where(lat>=0,.36,.64)
        self.mx=np.broadcast_to((u*sw-.5)[None,:],(self.h,self.w)).copy()
        self.my=np.broadcast_to((np.clip(y,.001,.999)*sh-.5)[:,None],(self.h,self.w)).astype('float32').copy()
        self.edge=(1-smoothstep(band-feather,band,np.abs(lat)))[:,None,None]
        sky=im[:round(sh*.04)].mean(axis=(0,1));earth=im[round(sh*.96):].mean(axis=(0,1))
        k=np.clip((np.abs(lat)-band+feather)/(np.pi*.5-band+feather),0,1)
        base=np.where((lat>=0)[:,None],sky[None,:],earth[None,:])*(1-.16*smoothstep(0,1,k))[:,None]
        self.cap=np.broadcast_to(base[:,None,:],(self.h,self.w,3)).astype('float32')
        self.u=u;self.sw=sw
    def render(self,strip):
        frame=cv2.remap(strip,self.mx,self.my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE).astype('float32')
        s=.015
        # Same rear-seam transition as the approved shader.
        for x,u in enumerate(self.u):
            p=u if u<.5 else u-1
            if abs(p)>=s:continue
            left_x=np.clip(1+p,1-s,.9999)*self.sw-.5
            right_x=np.clip(p,.0001,s)*self.sw-.5
            left=cv2.remap(strip,np.full((self.h,1),left_x,'float32'),self.my[:,x:x+1],cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE).reshape(self.h,3)
            right=cv2.remap(strip,np.full((self.h,1),right_x,'float32'),self.my[:,x:x+1],cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE).reshape(self.h,3)
            t=smoothstep(-s,s,p);frame[:,x,:]=left*(1-t)+right*t
        return np.uint8(np.clip(np.round(self.cap*(1-self.edge)+frame*self.edge),0,255))

MASKS={}
for name in JOBS:
    if name not in ('horse','bird','leaves'):
        MASKS[name]=Image.open(OUT/name/'source-mask.png');continue
    from PIL import ImageDraw,ImageFilter
    w,h=JOBS[name]['source_pixels']
    box={'horse':(.009,.535,.105,.636),'bird':(.075,.545,.182,.742),'leaves':(.565,.195,.66,.356)}[name]
    mask=Image.new('L',(w,h));ImageDraw.Draw(mask).rectangle((int(box[0]*w)+4,int(box[1]*h)+4,int(box[2]*w)-4,int(box[3]*h)-4),fill=255)
    MASKS[name]=mask.filter(ImageFilter.GaussianBlur(2))
    MASKS[name].save(DELIVERY/(name+'-mask.png'))
prepared={};reports=[]
for name,run in SELECTED.items():
    job,values,report=motion_source(name,run);prepared[name]=(job,values);reports.append(report)

metrics={}
for layer,names in [('garden',['water','horse','bird','leaves']),('hell',['fire'])]:
    base=source_rgb(layer);h,w=base.shape[:2]
    union=np.zeros((h,w),dtype='uint8')
    for name in names:union=np.maximum(union,np.asarray(MASKS[name]))
    strips=[];changed_outside=0;changed_inside=0;max_delta=0
    for i in range(N):
        frame=base.copy()
        for name in names:
            job,values=prepared[name];x0,y0,x1,y1=job['crop'];ch,cw=y1-y0,x1-x0
            original=base[y0:y1,x0:x1].astype('float32')
            alpha=np.asarray(MASKS[name])[y0:y1,x0:x1].astype('float32')/255
            if name=='leaves':
                yy,xx=np.mgrid[0:ch,0:cw].astype('float32');flow=values[i]
                patch=cv2.remap(original,xx-flow[...,0],yy-flow[...,1],cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)
            elif name in ('horse','bird'):patch=values[i].astype('float32')
            else:patch=original+values[i][...,None]
            target=np.uint8(np.clip(np.round(original*(1-alpha[...,None])+patch*alpha[...,None]),0,255))
            frame[y0:y1,x0:x1]=target
        diff=np.max(np.abs(frame.astype('int16')-base),axis=2)
        changed_outside+=int(np.count_nonzero(diff[union==0]));changed_inside+=int(np.count_nonzero(diff[union>0]));max_delta=max(max_delta,int(diff.max()))
        strips.append(frame)
    if changed_outside:raise ValueError('Motion leaked beyond its support')
    # The native 1774x887 strip has an odd height; H.264 4:2:0 needs even axes.
    encode_frames(strips,DELIVERY/f'{layer}-source-motion.mp4',width=1776,crf=18)
    projector=Panorama(layer)
    # Encode progressively to avoid retaining 108 large projected frames in memory.
    projected=[projector.render(strip) for strip in strips]
    poster=projector.render(base)
    # Compare against the previously approved WebGL projection. A media file can
    # decode successfully while containing incorrectly sampled pixels.
    expected=np.asarray(Image.open(ROOT/'bosch-world-assets'/f'{layer}-equirect-2048.jpg').convert('RGB'))
    projection_error=float(np.abs(expected.astype('float32')-poster).mean())
    if projection_error>8:raise ValueError(f'{layer}: projection differs from approved geometry: {projection_error}')
    Image.fromarray(poster).save(DELIVERY/f'{layer}-poster.jpg',quality=88)
    encode_frames(projected,DELIVERY/f'{layer}-equirect-2048.mp4',crf=19)
    encode_frames(projected,DELIVERY/f'{layer}-preview.mp4',width=1024,crf=31)
    source_loop=float(np.abs(strips[-1].astype('float32')-strips[0]).mean())
    metrics[layer]=dict(validation_stage='before lossy video encoding',projection_difference_from_approved_webgl_reference=projection_error,changed_pixels_outside_support=changed_outside,changed_pixels_inside_support=changed_inside,max_source_channel_delta=max_delta,loop_last_to_first_mean_absolute_difference=source_loop,frame_count=N,fps=FPS,duration_seconds=N/FPS,projection_pixels=[2048,1024],motions=names)
    print(layer,json.dumps(metrics[layer]),flush=True)

for name,run in [('water','run-stable-02'),('horse','run-dynamic-v2'),('bird','run-dynamic-v2'),('leaves','run-dynamic-v2'),('fire','run-stable-01')]:
    source=OUT/name/run/'raw-orbis.mp4'
    command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-i',str(source),'-an','-vf','scale=512:288','-c:v','libx264','-crf','35','-pix_fmt','yuv420p','-movflags','+faststart',str(DELIVERY/f'{name}-raw-preview.mp4')]
    p=subprocess.run(command,capture_output=True)
    if p.returncode:raise RuntimeError('Raw preview encoding failed')

attempts=[json.loads(p.read_text(encoding='utf-8')) for p in OUT.glob('*/run-*/report.json')]
capacity_failures=sum(a.get('model','').endswith('dynamic') and a.get('status')=='failed' for a in attempts)
summary=dict(model='Orbis Dynamic animals/leaves, retained previous Stable water/fire',dynamic_attempts_without_capacity=capacity_failures,actual_model_generation=True,live_model_call_in_browser=False,processing='local deterministic registration, motion extraction and masked compositing; ComfyUI not run',native_model_resolution=[832,480],delivered_stream_resolution=[2560,1440],retained_source_resolution=[1774,887],outputs=metrics,accepted_for_post=['water luminance only','stabilized leaf optical flow','stabilized distant fire luminance','Dynamic unicorn RGB','Dynamic bird wingbeat RGB'],rejected_subject_animations={},animal_revision='Dynamic RGB replaces previous rejected Stable tests; muzzle and wing motion require ongoing visual review',raw_whole_frame_generation_approved=False,headset_performance_verified=False,reports=reports)
(DELIVERY/'report.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print('delivery',DELIVERY)
