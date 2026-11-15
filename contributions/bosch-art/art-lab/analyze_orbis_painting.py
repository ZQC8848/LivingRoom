"""Measure raw Orbis composition drift and save inspectable clips/contact sheets."""
from pathlib import Path
import argparse,json,math,subprocess
import cv2
import numpy as np
from PIL import Image,ImageDraw
import imageio_ffmpeg

ROOT=Path(__file__).resolve().parent

def registration(reference,current,mask):
    sift=cv2.SIFT_create(nfeatures=1000)
    k0,d0=sift.detectAndCompute(cv2.cvtColor(reference,cv2.COLOR_RGB2GRAY),mask)
    k1,d1=sift.detectAndCompute(cv2.cvtColor(current,cv2.COLOR_RGB2GRAY),mask)
    if d0 is None or d1 is None:return None,{'valid':False,'reason':'missing descriptors'}
    pairs=cv2.BFMatcher().knnMatch(d1,d0,k=2)
    good=[a for pair in pairs if len(pair)==2 for a,b in [pair] if a.distance<.7*b.distance]
    if len(good)<8:return None,{'valid':False,'matches':len(good)}
    src=np.float32([k1[m.queryIdx].pt for m in good]);dst=np.float32([k0[m.trainIdx].pt for m in good])
    matrix,inliers=cv2.estimateAffinePartial2D(src,dst,method=cv2.RANSAC,ransacReprojThreshold=2.)
    if matrix is None:return None,{'valid':False,'matches':len(good)}
    scale=float(math.hypot(matrix[0,0],matrix[1,0]))
    if int(inliers.sum())<12 or not .7<scale<1.5:return None,{'valid':False,'matches':len(good),'inliers':int(inliers.sum()),'reason':'unreliable or degenerate affine estimate'}
    return matrix,dict(valid=True,matches=len(good),inliers=int(inliers.sum()),dx=round(float(matrix[0,2]),3),dy=round(float(matrix[1,2]),3),rotation_degrees=round(math.degrees(math.atan2(matrix[1,0],matrix[0,0])),4),scale=round(float(math.hypot(matrix[0,0],matrix[1,0])),5))

def analyze(job,run):
    folder=ROOT/'orbis-test'/job/run
    files=sorted((folder/'frames').glob('*.jpg'))
    if not files:raise ValueError('No frames')
    reference=np.asarray(Image.open(folder.parent/'reference.png').convert('RGB'))
    support=np.asarray(Image.open(folder.parent/'context-mask.png'))
    static=np.where(support>2,0,255).astype('uint8')
    samples=sorted(set([0,len(files)//5,len(files)*2//5,len(files)*3//5,len(files)*4//5,len(files)-1]))
    sheet=Image.new('RGB',(1536,3*320),(20,25,19));d=ImageDraw.Draw(sheet)
    items=[('reference',reference)]
    metrics=[]
    for idx in samples:
        current=np.asarray(Image.open(files[idx]).convert('RGB'))
        matrix,m=registration(reference,current,static)
        m.update(frame=idx,mean_absolute_difference=round(float(np.abs(current.astype('float32')-reference).mean()),3))
        metrics.append(m);items.append((f'frame {idx}',current))
    for i,(label,im) in enumerate(items):
        preview=Image.fromarray(im);preview.thumbnail((512,288));x=(i%3)*512;y=(i//3)*320
        sheet.paste(preview,(x,y+27));d.text((x+8,y+7),label,fill='white')
    sheet.save(folder/'contact.jpg',quality=92)
    ff=imageio_ffmpeg.get_ffmpeg_exe()
    command=[ff,'-y','-framerate','18','-i',str(folder/'frames/%04d.jpg'),'-an','-c:v','libx264','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(folder/'raw-orbis.mp4')]
    p=subprocess.run(command,capture_output=True,text=True)
    if p.returncode:raise RuntimeError(p.stderr[-1500:])
    result=dict(job=job,run=run,frames=len(files),raw_video_seconds=len(files)/18,metrics=metrics,scope='Raw model frames compared against the supplied reference, excluding active region for camera matching. This is a diagnostic, not headset validation.')
    (folder/'analysis.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('job');ap.add_argument('run');a=ap.parse_args();analyze(a.job,a.run)
