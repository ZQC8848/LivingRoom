from pathlib import Path
import sys,json,math
import cv2,numpy as np
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bosch_marked_motion_v9 import *
g=np.asarray(Image.open(ROOT/'bosch-world-assets/garden-generated.png').convert('RGB'));h=np.asarray(Image.open(ROOT/'bosch-world-assets/hell-generated.png').convert('RGB'));m=MarkedMotion(g,h)
pins={'G01':[(121,174),(99,220),(148,218),(84,178),(173,140)],'G02':[(465,166),(462,138),(493,199),(558,188)],'G06':[(1549,168),(1628,161),(1598,202),(1592,127)],'G07':[(1659,204),(1710,242),(1719,277),(1644,251),(1677,276)],'G14':[(454,505),(414,541),(468,537)],'G20':[(1037,504),(1044,501),(1081,554),(1116,550)]}
report={'headset_verified':False,'coverage':{},'g03_actor_disabled':not any(o.it['id']=='G03' for o in m.actors['garden'])}
for id,points in pins.items():
 obj=next(o for o in m.actors['garden'] if o.it['id']==id);a,b,c,d=obj.box
 values=[float(obj.alpha[y-b,x-a]) for x,y in points];report['coverage'][id]={'points':points,'alpha':values,'pass':min(values)>.95}
big=next(o for o in m.actors['garden'] if o.it['id']=='G20');small=next(o for o in m.actors['garden'] if o.it['id']=='G19')
a,b,c,d=big.box;aa,bb,cc,dd=small.box;occ=np.zeros(g.shape[:2],np.float32);occ[bb:dd,aa:cc]=small.alpha
wing=[(1067,522),(1075,519),(1089,524),(1098,531),(1106,542),(1105,549),(1091,546),(1080,541),(1070,533)];wa=softpoly(big.rgb.shape,wing,big.box,0,.5)
collisions=[]
for p in np.linspace(0,2*np.pi,96,endpoint=False):
 u=.5-.5*math.cos(2*p);_,al=transform(big.rgb,wa,(1069-a,524-b),44*u,1+.2*u)
 collisions.append(int(((al>.12)&(occ[b:d,a:c]>.25)).sum()))
report['large_wing_vs_small_bird_max_overlap_pixels']=max(collisions)
source=ROOT/'orbis-test/delivery-v6';caps={layer:cv2.VideoCapture(str(source/f'{layer}-source-motion.mp4')) for layer in ['garden','hell']}
specs=[('G01','garden',(45,95,210,252)),('G02','garden',(433,121,580,220)),('G04','garden',(937,114,1268,211)),('G06','garden',(1531,110,1650,225)),('G07','garden',(1630,177,1740,297)),('G14','garden',(399,489,483,553)),('G20','garden',(1022,471,1146,577)),('Water','garden',(768,370,1047,580)),('Fire left','hell',(0,177,125,331)),('Fire right','hell',(1605,140,1763,330)),('Roof smoke','hell',(1078,168,1214,289))]
sheet=Image.new('RGB',(1280,245*len(specs)),(19,24,20));draw=ImageDraw.Draw(sheet)
for row,(id,layer,box) in enumerate(specs):
 for col,index in enumerate([0,30,60,90]):
  cap=caps[layer];cap.set(cv2.CAP_PROP_POS_FRAMES,index);ok,f=cap.read()
  if not ok:raise ValueError((id,index))
  im=Image.fromarray(cv2.resize(cv2.cvtColor(f,cv2.COLOR_BGR2RGB),(1774,887))).crop(box);im.thumbnail((310,208));sheet.paste(im,(col*320,row*245+28));draw.text((col*320+4,row*245+6),f'{id} {index/30:.1f}s',fill='white')
sheet.save(OUT/'encoded-fix-contact.jpg',quality=96)
samples=[]
for index in range(0,240,12):
 caps['garden'].set(cv2.CAP_PROP_POS_FRAMES,index);ok,f=caps['garden'].read();f=cv2.resize(f,(1774,887));samples.append(f[157:220,617:664].astype(np.float32))
report['g03_encoded_mean_temporal_std']=float(np.std(np.array(samples),axis=0).mean())
for cap in caps.values():cap.release()
report['checks']={'complete_keypoints':all(r['pass'] for r in report['coverage'].values()),'wing_avoids_neighbor':max(collisions)==0,'g03_static':report['g03_actor_disabled'] and report['g03_encoded_mean_temporal_std']<.5}
(OUT/'revision-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if not all(report['checks'].values()):raise SystemExit(2)
