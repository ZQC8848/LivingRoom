"""Package received model frames without adding environmental animation.

Keeps raw delivered composition and a separately labelled 2:1 review crop.
Geometry crop undoes the documented contain margins; not panorama completion.
"""
from pathlib import Path
import argparse,json,subprocess
import cv2, numpy as np, imageio_ffmpeg
ROOT=Path(__file__).resolve().parent/'live-modes-v1'
FF=imageio_ffmpeg.get_ffmpeg_exe()

def encode(images,times,target):
    # Timed concat preserves arrival-time progression instead of speeding up stalls.
    spec=target.with_suffix('.ffconcat')
    lines=['ffconcat version 1.0']
    for i,p in enumerate(images):
        lines.append("file '"+str(p.resolve()).replace('\\','/')+"'")
        lines.append('duration '+str(max(.001,times[i+1]-times[i]) if i+1<len(times) else 1/24))
    lines.append("file '"+str(images[-1].resolve()).replace('\\','/')+"'")
    spec.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    p=subprocess.run([FF,'-y','-safe','0','-i',str(spec),'-an','-r','24','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],capture_output=True)
    if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace')[-700:])

def pano(im):
    h,w=im.shape[:2];a=round(h*48/736);b=round(h*688/736)
    # Service scales its native raster into delivery tiers; restore art's known 2:1.
    return cv2.resize(im[a:b],(960,480),interpolation=cv2.INTER_AREA)

def drift(a,b):
    gray=[cv2.cvtColor(x,cv2.COLOR_BGR2GRAY) for x in (a,b)]
    mask=np.zeros((480,960),np.uint8)
    for x0,y0,x1,y1 in [(105,140,205,290),(320,100,410,225),(435,120,540,285),(555,150,650,245),(760,115,860,300)]:
        mask[y0:y1,x0:x1]=255
    sift=cv2.SIFT_create(nfeatures=2000,contrastThreshold=.015)
    ka,da=sift.detectAndCompute(gray[0],mask);kb,db=sift.detectAndCompute(gray[1],mask)
    if da is None or db is None:return {'status':'insufficient features'}
    good=[m for pair in cv2.BFMatcher().knnMatch(da,db,k=2) if len(pair)==2 for m,n in [pair] if m.distance<.75*n.distance]
    if len(good)<8:return {'status':'insufficient matches','matches':len(good)}
    x=np.float32([ka[m.queryIdx].pt for m in good]);y=np.float32([kb[m.trainIdx].pt for m in good])
    mat,inl=cv2.estimateAffinePartial2D(x,y,method=cv2.RANSAC,ransacReprojThreshold=2.5)
    if mat is None:return {'status':'no robust estimate'}
    if int(inl.sum())<12:return {'status':'insufficient robust inliers','matches':len(good),'inliers':int(inl.sum()),'note':'Do not interpret this estimate as a camera-motion measurement.'}
    scale=float(np.hypot(mat[0,0],mat[0,1]));rotation=float(np.degrees(np.arctan2(mat[1,0],mat[0,0])))
    center=np.array([480,240]);shift=mat[:,:2]@center+mat[:,2]-center
    return {'status':'estimated','matches':len(good),'inliers':int(inl.sum()),'scale':round(scale,5),
            'rotation_degrees':round(rotation,3),'center_displacement_pixels_at_960w':np.round(shift,2).tolist(),
            'note':'Architecture feature alignment is a drift proxy; human review still required.'}

def package(folder):
    r=json.loads((folder/'report.json').read_text(encoding='utf-8'))
    frames=sorted((folder/'frames').glob('*.jpg'));times=r.get('frame_timestamps',[])
    if not frames:return None
    if len(frames)<len(times):raise ValueError('Missing recorded frame files: '+str(folder))
    untimed_tail=len(frames)-len(times)
    # Decoder callbacks can finish a frame after pause/report snapshot. Retain the
    # original file as evidence, but do not invent an arrival time for that tail.
    frames=frames[:len(times)]
    encode(frames,times,folder/'raw-received.mp4')
    views=folder/'panorama-frames';views.mkdir(exist_ok=True)
    for f in frames:cv2.imwrite(str(views/f.name),pano(cv2.imread(str(f))),[cv2.IMWRITE_JPEG_QUALITY,95])
    pframes=[views/f.name for f in frames];encode(pframes,times,folder/'panorama-review.mp4')
    stages=[c for c in r['commands'] if c['command']=='set_prompt']
    selected=[]
    for i,c in enumerate(stages):
        t=(times[0]+1.0) if i==0 else (stages[i+1]['sent_t']-.2 if i+1<len(stages) else times[-1])
        n=min(range(len(times)),key=lambda n:abs(times[n]-t))
        im=cv2.imread(str(pframes[n]));selected.append(im)
        label=f"Target: {c['stage']} | received +{times[n]-times[0]:.1f}s"
        cv2.rectangle(im,(0,0),(960,36),(17,22,19),-1)
        cv2.putText(im,label,(14,25),cv2.FONT_HERSHEY_SIMPLEX,.62,(235,240,230),1,cv2.LINE_AA)
    sheet=np.vstack(selected);cv2.imwrite(str(folder/'stages.jpg'),sheet,[cv2.IMWRITE_JPEG_QUALITY,93])
    qa={'id':r['id'],'status':r['status'],'frames':len(frames),'excluded_untimed_tail_frames':untimed_tail,'seconds':round(times[-1]-times[0],2),
        'hot_prompt_stages':[{'label':c['stage'],'sent_after_first_frame_seconds':round(c['sent_t']-times[0],3),'ack_after_send_seconds':round(c['returned_t']-c['sent_t'],3),'reply_type':c['reply_type']} for c in stages],
        'drift_first_to_last':drift(pano(cv2.imread(str(frames[0]))),pano(cv2.imread(str(frames[-1])))),
        'projection_note':'Review crop restores the 2:1 reference band. It does not guarantee periodic seam consistency or constitute an approved immersive panorama.',
        'added_animation':False,'source':'Actual Orbis Dynamic stream, live prompt changes; replay recording.'}
    (folder/'review.json').write_text(json.dumps(qa,indent=2),encoding='utf-8')
    return qa

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--attempt',default='01');a=ap.parse_args()
    qa=[]
    for p in ROOT.glob(f'*/run-{a.attempt}/report.json'):
        x=package(p.parent)
        if x:qa.append(x);print(json.dumps(x),flush=True)
    (ROOT/f'batch-{a.attempt}'/'review.json').write_text(json.dumps(qa,indent=2),encoding='utf-8')
