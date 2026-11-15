from pathlib import Path
import cv2,numpy as np
from PIL import Image
root=Path(__file__).resolve().parent.parent
out=root/'deployment/bosch-demo/public/scenes/bosch-demo/live'
polys=[[(230,215),(450,215),(480,440),(210,440)],[(740,265),(830,265),(855,330),(925,380),(925,440),(610,440),(655,345),(715,315)],[(965,205),(1090,205),(1120,440),(935,440)],[(1220,270),(1365,270),(1365,340),(1430,355),(1460,440),(1145,440),(1175,345)],[(1640,280),(1755,280),(1815,440),(1575,440)]]
boxes=[(45,190,235,350),(505,225,665,345),(1090,215,1430,310),(1770,195,1880,320),(1865,285,2030,455)]
for world,file in [('garden','poster.jpg'),('hell','hell-poster.jpg')]:
 im=cv2.imread(str(root/'deployment/bosch-demo/public/scenes/bosch-demo/media'/file));h,w=im.shape[:2]
 labels=np.full((h,w),cv2.GC_PR_BGD,np.uint8)
 labels[435:]=cv2.GC_FGD;labels[:190]=cv2.GC_BGD
 for p in polys:cv2.fillPoly(labels,[np.array(p,np.int32)],cv2.GC_PR_FGD)
 for x0,y0,x1,y1 in boxes:labels[y0:y1,x0:x1]=cv2.GC_PR_FGD
 if world=='hell':labels[190:435,70:230]=cv2.GC_PR_FGD
 # Every pixel below the safe sky boundary is protected. Learn building/leaf colour from it.
 labels[435:]=cv2.GC_FGD
 cv2.grabCut(im,labels,None,np.zeros((1,65),np.float64),np.zeros((1,65),np.float64),6,cv2.GC_INIT_WITH_MASK)
 sky=np.isin(labels,[cv2.GC_BGD,cv2.GC_PR_BGD]).astype(np.uint8)*255
 sky[430:]=0
 # Keep only sky connected to the top, rather than isolated blue highlights inside an object.
 n,components,stats,_=cv2.connectedComponentsWithStats(sky,8)
 top=set(components[0]);sky=np.isin(components,list(top-{0})).astype(np.uint8)*255
 # Erode into sky before the short feather: object silhouettes remain untouched.
 sky=cv2.erode(sky,np.ones((3,3),np.uint8));sky=cv2.GaussianBlur(sky,(5,5),.8)
 fade=np.clip((430-np.arange(h)[:,None])/190,0,1);fade=fade*fade*(3-2*fade);sky=(sky*fade).astype(np.uint8)
 # Bottom empty polar ground is independent from the protected painting band.
 y=np.arange(h)[:,None];ground=np.clip((y-850)/55,0,1);ground=ground*ground*(3-2*ground);ground=np.broadcast_to(ground*255,(h,w)).astype(np.uint8)
 mask=np.maximum(sky,ground);cv2.imwrite(str(out/(world+'-environment-mask.png')),mask)
 cv2.imwrite(str(root/'art-lab'/('live-mask-'+world+'.png')),mask)
 if world=='garden':
  raw=cv2.imread(str(root/'deployment/review/live-local-r6b/dusk-raw.jpg'))
  crop=raw[round(raw.shape[0]*48/736):round(raw.shape[0]*688/736)]
  raw=cv2.resize(crop,(w,h));a=mask[...,None]/255
  cv2.imwrite(str(root/'art-lab/live-composite-review.jpg'),(im*(1-a)+raw*a).astype(np.uint8))
 print(world,'live pixel area',round((mask>0).mean()*100,1),'percent')
