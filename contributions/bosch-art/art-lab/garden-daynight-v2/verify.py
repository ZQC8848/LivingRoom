from pathlib import Path
import json,hashlib,re
import cv2,numpy as np
ROOT=Path(__file__).resolve().parent;OUT=ROOT.parent.parent/'handoff/garden-daynight-20261114'
m=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
def read(p,i):
 c=cv2.VideoCapture(str(p));c.set(cv2.CAP_PROP_POS_FRAMES,i);ok,f=c.read();c.release()
 if not ok:raise RuntimeError('Cannot decode '+str(p)+' frame '+str(i))
 return f
report={'checks':{},'headset_verified':False,'production_reveal_modified':False}
for name,shape in [('garden-daynight-30s-flat.mp4',[1776,888]),('garden-daynight-30s-panorama.mp4',[2048,1024]),('garden-daynight-review-with-voice.mp4',[1776,888])]:
 c=cv2.VideoCapture(str(OUT/name));actual=[int(c.get(cv2.CAP_PROP_FRAME_WIDTH)),int(c.get(cv2.CAP_PROP_FRAME_HEIGHT))];fps=c.get(cv2.CAP_PROP_FPS);count=c.get(cv2.CAP_PROP_FRAME_COUNT);c.release()
 report['checks'][name]={'geometry':actual,'fps':fps,'frames':count,'pass':actual==shape and fps==30 and count==900}
flat=OUT/'garden-daynight-30s-flat.mp4';first=read(flat,0);last=read(flat,899)
loop_diff=np.abs(first.astype(np.float32)-last.astype(np.float32))
report['loop_boundary']={'mean_channel_delta':float(loop_diff.mean()),'p99_channel_delta':float(np.quantile(loop_diff,.99))}
mask=cv2.imread(str(OUT/'motion-water-mask.png'),0);protected=cv2.erode(np.uint8(mask==0)*255,np.ones((5,5),np.uint8))>0
still=read(flat,60);delta=np.abs(still.astype(np.float32)-first.astype(np.float32)).mean(axis=2)
report['hold_phase']={'protected_mean_delta':float(delta[protected].mean()),'water_mean_delta':float(delta[mask>220].mean())}
for label,i in [('day',0),('night',450)]:
 ref=cv2.imread(str(OUT/('day-original.png' if label=='day' else 'night-imagegen.png')));ref=cv2.resize(ref,(1776,888),interpolation=cv2.INTER_CUBIC)
 f=read(flat,i);err=np.abs(ref.astype(np.float32)-f.astype(np.float32))
 # Lossy 4:2:0 compression changes canvas grain/color; assess geometry directly.
 sift=cv2.SIFT_create(nfeatures=4000,contrastThreshold=.015)
 ka,da=sift.detectAndCompute(cv2.cvtColor(ref,cv2.COLOR_BGR2GRAY),np.uint8(protected)*255)
 kb,db=sift.detectAndCompute(cv2.cvtColor(f,cv2.COLOR_BGR2GRAY),np.uint8(protected)*255)
 pairs=cv2.BFMatcher().knnMatch(da,db,k=2);good=[a for a,b in pairs if a.distance<.7*b.distance]
 x=np.float32([ka[v.queryIdx].pt for v in good]);y=np.float32([kb[v.trainIdx].pt for v in good])
 affine,inliers=cv2.estimateAffinePartial2D(x,y,method=cv2.RANSAC,ransacReprojThreshold=1.5)
 keep=inliers.ravel()>0;dist=np.linalg.norm(x[keep]-y[keep],axis=1)
 scale=float(np.hypot(affine[0,0],affine[0,1]));center=np.array([888,444]);shift=affine[:,:2]@center+affine[:,2]-center
 report['checks'][label+'_plate_preserved']={'protected_mean_channel_error':float(err[protected].mean()),'robust_matches':int(keep.sum()),'median_feature_displacement_pixels':float(np.median(dist)),'p95_feature_displacement_pixels':float(np.quantile(dist,.95)),'scale':scale,'centre_displacement_pixels':shift.tolist(),'pass':bool(keep.sum()>50 and np.quantile(dist,.95)<1.5 and abs(scale-1)<.001 and np.linalg.norm(shift)<.35)}
p=OUT/'garden-daynight-30s-panorama.mp4';seam=[]
for i in (0,240,450,660,899):
 f=read(p,i);d=np.abs(f[:,0].astype(np.int16)-f[:,-1].astype(np.int16));seam.append({'frame':i,'mean':float(d.mean()),'p99':float(np.quantile(d,.99))})
report['rear_seam']=seam
report['checks']['no_model_motion_on_fixed_plates']={'pass':m['motion_changed_values_outside_water_mask']==0}
report['checks']['seamless_loop']={'pass':bool(loop_diff.mean()<1.8 and np.quantile(loop_diff,.99)<9)}
report['checks']['decoded_panorama_seam']={'pass':all(s['mean']<3 and s['p99']<12 for s in seam)}
report['checks']['owned_model_session_closed']={'pass':m['owned_session_disconnected'] is True}
leaks=[]
for p in OUT.rglob('*'):
 if p.suffix.lower() in ('.json','.html','.js','.txt'):
  text=p.read_text(encoding='utf-8',errors='replace')
  if re.search(r'sk_[0-9a-f]{24,}|eyJ[A-Za-z0-9_-]{30,}\.',text):leaks.append(str(p.relative_to(OUT)))
report['checks']['no_credentials_in_delivery']={'pass':not leaks}
report['files']={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in OUT.iterdir() if p.is_file() and p.suffix in ('.mp4','.mp3')}
report['pass']=all(x['pass'] for x in report['checks'].values())
(OUT/'qa/media-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2))
if not report['pass']:raise SystemExit(2)
