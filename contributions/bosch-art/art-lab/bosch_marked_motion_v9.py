"""Revision from the user's object-by-object review: complete silhouettes first.

Broad, feathered original-paint cards are intentional for isolated sky objects.
They include low-contrast paint, tails and props instead of dropping pixels by
color. Bodies are not sliced by an arbitrary wing threshold. Water goes DOWN;
smoke goes UP. No camera motion or deformation of an environmental rectangle.
"""
from pathlib import Path
import copy,json,math
import cv2,numpy as np
from PIL import Image
import bosch_marked_motion as old

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'motion-v9';MASKS=OUT/'mattes';MASKS.mkdir(parents=True,exist_ok=True)
CAT=copy.deepcopy(old.CAT)
CHANGES={
 'G01':([48,96,209,248],'Complete rider, mounts and held branch sway together'),
 'G02':([437,125,572,217],'Complete fish/boat, tail, pole and fruit float together'),
 'G03':([617,157,664,220],'Intentionally static: tiny uncertain detail disabled'),
 'G04':([944,120,1263,207],'Complete flock moves gently as one painted group'),
 'G06':([1540,114,1644,216],'Complete ornament including both wing tips and legs floats'),
 'G07':([1635,185,1734,294],'Two complete birds; wing articulation anchored to the bodies'),
 'G14':([404,493,478,552],'Only the complete lower bank bird; broad silhouette and wing ruffle'),
 'G17':([780,376,816,576],'Visible downward water ribbons, falling drops and splash rings'),
 'G18':([1000,377,1048,576],'Visible downward water ribbons, falling drops and splash rings'),
 'G20':([1024,484,1140,575],'Large waterbird raises a complete front wing and closes it twice'),
 'H01':([437,125,572,217],'Complete dark sky fish/boat floats'),
 'H02':([944,115,1186,211],'Complete dark flock moves together'),
 'H03':([1540,114,1644,216],'Complete dark ornament floats'),
}
for it in CAT:
 if it['id'] in CHANGES:it['box'],it['action']=CHANGES[it['id']]
 if it['id']=='G03':it.update(method='static',status='disabled at user request')
 it['revision']='r4'
(OUT/'motion-catalog.json').write_text(json.dumps({'source_dimensions':[1774,887],'camera':'locked; no movement','period_seconds':8,'items':CAT,'counterpart_effects':{'G05':'Smoke rises from the ruined roof pipe in hell','G07':'Right city flames and smoke rise visibly','G08':'Left city flames and smoke rise visibly'},'intentionally_static':['G03'],'annotations_are_not_model_inputs':True},ensure_ascii=False,indent=2),encoding='utf-8')

POLYS={
 'G01':[(59,192),(76,171),(107,171),(108,147),(117,140),(115,122),(127,109),(150,110),(160,123),(176,125),(186,139),(181,158),(173,164),(176,175),(195,166),(201,170),(190,190),(168,205),(168,225),(154,233),(130,235),(116,232),(99,235),(89,228),(89,214),(72,214),(58,207)],
 'G02':[(457,132),(470,137),(487,142),(513,147),(527,157),(529,178),(541,181),(564,173),(569,181),(564,195),(551,202),(524,207),(495,208),(473,206),(452,203),(441,195),(440,181),(454,177),(453,160)],
 'G06':[(1587,119),(1604,120),(1607,148),(1637,152),(1639,169),(1610,181),(1608,211),(1585,212),(1584,179),(1544,178),(1542,159),(1576,152)],
 'G14':[(444,502),(446,495),(454,495),(456,500),(465,500),(470,506),(461,512),(458,524),(462,530),(474,532),(475,539),(467,542),(456,539),(454,549),(445,550),(443,541),(429,541),(416,546),(408,544),(409,537),(420,531),(426,521),(437,515)],
 'G20':[(1032,502),(1039,496),(1049,496),(1053,505),(1051,514),(1054,518),(1068,520),(1076,517),(1092,522),(1104,534),(1108,543),(1120,546),(1125,552),(1113,557),(1104,553),(1093,552),(1080,559),(1071,559),(1064,550),(1054,547),(1047,536),(1043,524),(1043,510),(1033,510),(1029,507)],
 'G04':[(946,180),(978,164),(1017,145),(1081,126),(1156,127),(1257,141),(1262,177),(1201,181),(1130,174),(1076,169),(1045,183),(1007,190),(979,203),(946,205)],
 'H02':[(947,176),(985,150),(1024,126),(1088,116),(1179,123),(1183,176),(1139,187),(1082,182),(1045,190),(1006,202),(947,208)],
}
POLYS['H01']=POLYS['G02'];POLYS['H03']=POLYS['G06']
BLUE=[(1654,193),(1665,199),(1668,216),(1679,227),(1687,226),(1694,236),(1717,237),(1720,245),(1699,249),(1705,263),(1718,273),(1730,276),(1730,284),(1712,282),(1690,272),(1677,259),(1670,246),(1661,239),(1655,223)]
WHITE=[(1639,247),(1651,246),(1660,250),(1668,245),(1675,248),(1675,259),(1682,269),(1684,280),(1675,283),(1664,275),(1653,269),(1647,260),(1639,256)]

def softpoly(shape,points,box,grow=2,feather=.85):
 x0,y0,_,_=box;m=old.poly(shape,[(x-x0,y-y0) for x,y in points])
 if grow:m=cv2.dilate(m,np.ones((grow*2+1,grow*2+1),np.uint8))
 return old.blur(m.astype(np.float32)/255,feather)
def transform(rgb,alpha,pivot,angle,scale=1):
 h,w=alpha.shape;mat=cv2.getRotationMatrix2D(pivot,angle,scale)
 a=np.clip(cv2.warpAffine(alpha,mat,(w,h),flags=cv2.INTER_LINEAR),0,1)
 pm=cv2.warpAffine(rgb*alpha[...,None],mat,(w,h),flags=cv2.INTER_LINEAR)
 return pm,a

class CompleteObject:
 def __init__(self,base,it):
  self.it=it;self.phase=int(it['id'][1:])*.73
  x0,y0,x1,y1=it['box'];pad=40 if it['id'] in ['G07','G20'] else 14
  self.box=(max(0,x0-pad),max(0,y0-pad),min(1774,x1+pad),min(887,y1+pad));a,b,c,d=self.box
  self.rgb=base[b:d,a:c].astype(np.float32);self.flow=None;self.model=None
  if it['id']=='G07':
   self.blue=softpoly(self.rgb.shape,BLUE,self.box,1,.65);self.white=softpoly(self.rgb.shape,WHITE,self.box,1,.65)
   self.alpha=np.maximum(self.blue,self.white)
  else:self.alpha=softpoly(self.rgb.shape,POLYS[it['id']],self.box,2,1)
  remove=cv2.dilate(np.uint8(self.alpha>.02)*255,np.ones((3,3),np.uint8))
  self.remove=old.blur(remove.astype(np.float32)/255,.8)
  self.clean=cv2.inpaint(np.uint8(self.rgb),remove,5,cv2.INPAINT_TELEA).astype(np.float32)
  Image.fromarray(np.uint8(self.alpha*255)).save(MASKS/(it['id']+'-complete.png'))
 def render(self,f,p):
  a,b,c,d=self.box;h,w=self.alpha.shape;id=self.it['id'];s=math.sin(p+self.phase)
  if id=='G07':return self.render_birds(f,p)
  angle=0;dy=0;dx=0;scale=1;pivot=(w/2,h/2)
  if id=='G01':angle=1.9*s;dy=.65*math.sin(p);pivot=(132-a,193-b)
  elif id in ['G02','H01','G06','H03']:angle=1.4*s;dy=4.5*s
  elif id in ['G04','H02']:dx=3.8*math.sin(p);dy=1.7*math.sin(2*p+.5);angle=.35*math.sin(p)
  elif id=='G14':angle=.8*s;dy=.6*s;pivot=(450-a,538-b)
  mat=cv2.getRotationMatrix2D(pivot,angle,scale);mat[0,2]+=dx;mat[1,2]+=dy
  rgb=self.rgb;al=self.alpha
  patch=old.over(f[b:d,a:c],self.clean,self.remove)
  aa=cv2.warpAffine(al,mat,(w,h));pm=cv2.warpAffine(rgb*al[...,None],mat,(w,h))
  patch=patch*(1-aa[...,None])+pm
  if id in ['G14','G20']:
   if id=='G20':
    wing=[(1067,522),(1075,519),(1089,524),(1098,531),(1106,542),(1105,549),(1091,546),(1080,541),(1070,533)]
    hinge=(1069-a,524-b);turn=44*(.5-.5*math.cos(2*p));wing_scale=1+.20*(.5-.5*math.cos(2*p))
   else:
    wing=[(426,527),(434,519),(445,517),(451,524),(447,534),(435,538),(424,537)]
    hinge=(445-a,520-b);turn=18*math.sin(2*p);wing_scale=1
   wa=softpoly(rgb.shape,wing,self.box,0,.5)
   wp,aa=transform(rgb,wa,hinge,turn,wing_scale)
   # The painted folded FAR wing stays on the torso; the full near wing opens.
   # This supplies a body beneath the raised wing rather than a transparent hole.
   patch=patch*(1-aa[...,None])+wp
  f[b:d,a:c]=patch
 def render_birds(self,f,p):
  a,b,c,d=self.box;rgb=self.rgb;h,w=self.alpha.shape
  patch=old.over(f[b:d,a:c],self.clean,self.remove)
  for index,(alpha,points,hinge,amp) in enumerate([
   (self.blue,[(1657,196),(1664,207),(1672,224),(1680,240),(1673,244),(1661,232),(1656,211)],(1677-a,241-b),24),
   (self.white,[(1658,252),(1667,246),(1673,251),(1673,261),(1678,271),(1670,270),(1662,261)],(1659-a,258-b),32),
  ]):
   wing=softpoly(rgb.shape,points,self.box,0,.6)*alpha
   # Remove the complete original wing only. Its root overlaps the complete body.
   body=np.clip(alpha-wing,0,1)
   body=np.maximum(body,alpha*softpoly(rgb.shape,[(hinge[0]+a-3,hinge[1]+b-3),(hinge[0]+a+3,hinge[1]+b-3),(hinge[0]+a+3,hinge[1]+b+3),(hinge[0]+a-3,hinge[1]+b+3)],self.box,0,.5))
   pm,aa=transform(rgb,wing,hinge,amp*math.sin(2*p+index*.8))
   premul=rgb*body[...,None];combined=aa+body*(1-aa)
   combined_pm=pm+premul*(1-aa[...,None])
   # A small whole-bird vertical drift does not split its beak or tail.
   mat=np.array([[1,0,0],[0,1,1.4*math.sin(p+index)]],np.float32)
   ca=cv2.warpAffine(combined,mat,(w,h));cp=cv2.warpAffine(combined_pm,mat,(w,h))
   patch=patch*(1-ca[...,None])+cp
  f[b:d,a:c]=patch

class MarkedMotion(old.MarkedMotion):
 def __init__(self,garden,hell):
  old.CAT=CAT;old.MASKS=MASKS;old.OUT=OUT
  super().__init__(garden,hell)
  corrected=set(POLYS)|{'G07'}
  for layer in ['garden','hell']:
   self.actors[layer]=[o for o in self.actors[layer] if o.it['id'] not in corrected|{'G03'}]
   for it in CAT:
    if it['layer']==layer and it['id'] in corrected:self.actors[layer].append(CompleteObject(self.bases[layer],it))
  self.flocks={} # complete flock cards supersede partial color-key components
  self.setup_fire(hell);self.make_matte_sheet()
 def setup_falls(self,base):
  self.falls=[]
  # These trace the source water, rather than the pink ornaments beside it.
  for points in [[(801,383),(794,406),(791,449),(790,499),(789,559)],[(811,386),(806,420),(805,476),(804,558)],[(1010,386),(1017,420),(1019,480),(1019,559)],[(1022,383),(1028,418),(1029,482),(1030,559)]]:
   x0=min(x for x,y in points)-7;x1=max(x for x,y in points)+8;y0=points[0][1];y1=572
   yy,xx=np.mgrid[y0:y1,x0:x1].astype(np.float32)
   center=np.interp(yy[:,0],[y for x,y in points],[x for x,y in points])[:,None]
   core=np.exp(-((xx-center)/1.0)**2);halo=np.exp(-((xx-center)/2.6)**2)
   self.falls.append(dict(box=(x0,y0,x1,y1),xx=xx,yy=yy,core=core,halo=halo,center=center,points=points))
 def falling_water(self,f,p):
  for n,stream in enumerate(self.falls):
   x0,y0,x1,y1=stream['box'];yy=stream['yy'];core=stream['core'];halo=stream['halo'];height=559-y0
   # Travelling translucent painted streaks: phase increases -> y increases.
   flow=.55+.45*np.sin((yy-y0)*.22-8*p+n*.7)
   alpha=core*(.12+.24*flow)+halo*.04
   fade=np.clip((yy-y0)/8,0,1)*np.clip((563-yy)/8,0,1);alpha*=fade
   patch=f[y0:y1,x0:x1];patch=old.over(patch,np.full_like(patch,[198,222,202]),alpha)
   for k in range(5):
    age=(p/(2*np.pi)*2+k/5+n*.19)%1
    cy=y0+height*(age**1.65)
    # Gravity: droplets visibly accelerate, never oscillate sideways.
    trail=np.exp(-((yy-cy)/4.2)**2)*core
    patch=old.over(patch,np.full_like(patch,[218,236,215]),trail*.65*math.sin(math.pi*age)**.5)
   f[y0:y1,x0:x1]=patch
   cx=stream['points'][-1][0];cy=560
   xa,xb=max(0,cx-21),min(1774,cx+22);ya,yb=cy-5,cy+8
   gy,gx=np.mgrid[ya:yb,xa:xb].astype(np.float32)
   r=np.sqrt((gx-cx)**2+((gy-cy)*3.4)**2)
   rings=np.exp(-((r-(7+(p/(2*np.pi)*3+n*.2)%1*14))/1.3)**2)*.15
   f[ya:yb,xa:xb]=old.over(f[ya:yb,xa:xb],np.full_like(f[ya:yb,xa:xb],[177,209,185]),rings)
 def setup_fire(self,base):
  self.plumes=[]
  sites=[(43,301,90),(412,306,78),(497,296,112),(795,310,88),(976,310,84),(1318,304,128),(1686,299,145)]
  for n,(cx,cy,rise) in enumerate(sites):
   x0=max(0,cx-63);x1=min(1774,cx+66);y0=max(0,cy-rise-24);y1=cy+17
   rgb=base[y0:y1,x0:x1].astype(np.float32);yy,xx=np.mgrid[y0:y1,x0:x1].astype(np.float32)
   hsv=cv2.cvtColor(np.uint8(rgb),cv2.COLOR_RGB2HSV)
   skyline=(hsv[...,2]<72)&(yy>cy-36)
   self.plumes.append(dict(box=(x0,y0,x1,y1),cx=cx,cy=cy,rise=rise,xx=xx,yy=yy,skyline=skyline,index=n))
  # The ruined counterpart of the roof fish emits a distinct small smoke plume.
  self.pipe=dict(box=(1108,175,1197,270),cx=1155,cy=251,rise=58)
 def fire(self,f,p):
  for obj in self.plumes:
   x0,y0,x1,y1=obj['box'];xx,yy=obj['xx'],obj['yy'];n=obj['index'];cx,cy,rise=obj['cx'],obj['cy'],obj['rise'];patch=f[y0:y1,x0:x1]
   flames=np.zeros(xx.shape,np.float32);cores=np.zeros_like(flames)
   for k in range(6):
    base_x=cx+(k-2.5)*11
    ht=26+8*math.sin(3*p+n*.5+k)+5*math.sin(5*p+k*.7)
    dy=cy-yy;z=np.clip(dy/ht,0,1)
    center=base_x+2.8*np.sin(dy*.16-4*p+k)
    width=1.0+4.6*(1-z)
    tongue=np.clip(1-((xx-center)/width)**2,0,1)*(dy>0)*(dy<ht)
    tongue*=np.clip(np.sin(np.pi*z),0,1)**.65
    flames=np.maximum(flames,tongue*.78);cores=np.maximum(cores,tongue*np.clip((.65-z)/.6,0,1)*.7)
   flames[obj['skyline']]=0;cores[obj['skyline']]=0
   patch=old.over(patch,np.full_like(patch,[199,81,24]),old.blur(flames,.65))
   patch=old.over(patch,np.full_like(patch,[235,151,52]),old.blur(cores,.6))
   smoke=np.zeros(xx.shape,np.float32)
   for k in range(7):
    age=(p/(2*np.pi)*1.0+k/7+n*.17)%1
    py=cy-15-rise*age;px=cx+15*age+5*math.sin(2*p+k+n)
    rx=7+13*age;ry=11+14*age
    puff=np.exp(-(((xx-px)/rx)**2+((yy-py)/ry)**2)*1.2)
    smoke+=puff*(math.sin(math.pi*age)**.8)*.16
   smoke=np.clip(smoke,0,.40);smoke[obj['skyline']]=0
   patch=old.over(patch,np.full_like(patch,[89,83,69]),smoke)
   f[y0:y1,x0:x1]=patch
  self.pipe_smoke(f,p)
 def pipe_smoke(self,f,p):
  o=self.pipe;x0,y0,x1,y1=o['box'];yy,xx=np.mgrid[y0:y1,x0:x1].astype(np.float32);alpha=np.zeros(xx.shape,np.float32)
  for k in range(5):
   age=(p/(2*np.pi)+k/5)%1;py=o['cy']-o['rise']*age;px=o['cx']+9*age+2*math.sin(2*p+k)
   alpha+=np.exp(-(((xx-px)/(3+9*age))**2+((yy-py)/(5+8*age))**2))*math.sin(math.pi*age)*.21
  # Preserve the pipe's painted tip and black foreground branches.
  ref=self.bases['hell'][y0:y1,x0:x1];dark=cv2.cvtColor(ref,cv2.COLOR_RGB2GRAY)<32
  alpha[dark]=0;alpha[yy>247]=0
  f[y0:y1,x0:x1]=old.over(f[y0:y1,x0:x1],np.full_like(f[y0:y1,x0:x1],[114,108,91]),np.clip(alpha,0,.40))
 def render(self,frame,layer,p):
  if layer=='hell':self.water(frame,p);self.fire(frame,p)
  for obj in self.actors[layer]:obj.render(frame,p)
  if layer=='garden':self.falling_water(frame,p)
  return frame
