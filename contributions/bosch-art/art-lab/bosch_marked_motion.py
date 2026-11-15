"""Periodically animate the user's marked objects without moving scenery tiles.

RGB cutouts keep their original paint; each has a fixed alpha, root pivot and
static clean plate. Model poses, when accepted, replace only an object matte.
No environment optical flow and no animated rectangular exposure corrections.
"""
from pathlib import Path
import json,math
import cv2
import numpy as np
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'motion-v8'; MASKS=OUT/'mattes'; MASKS.mkdir(exist_ok=True)
CAT=json.loads((OUT/'motion-catalog.json').read_text(encoding='utf-8'))['items']

def blur(a,s=.5):return cv2.GaussianBlur(a,(0,0),s)
def poly(shape,points):
    m=np.zeros(shape[:2],np.uint8);cv2.fillPoly(m,[np.array(points,np.int32)],255);return m
def over(dst,rgb,a):return dst*(1-a[...,None])+rgb*a[...,None]
def sample(stack,u):
    p=float(np.clip(u,0,1))*(len(stack)-1);i=int(p);j=min(i+1,len(stack)-1)
    return stack[i]*(1-(p-i))+stack[j]*(p-i)

# Polygon envelopes follow the object, not the rectangle circled by the user.
POLYS={
 'G01':[(68,202),(103,194),(107,167),(114,150),(113,122),(139,108),(166,118),(176,142),(169,165),(154,184),(159,200),(169,207),(168,218),(154,218),(147,232),(134,223),(119,240),(111,231),(98,227),(88,228),(87,218),(70,219)],
 'G02':[(454,139),(474,149),(489,143),(512,147),(529,161),(534,181),(520,193),(546,198),(531,206),(471,206),(450,197),(471,192),(466,174),(459,172)],
 'G03':[(620,170),(638,156),(660,165),(646,180),(654,194),(641,214),(617,215),(630,194)],
 'G05':[(1097,254),(1128,243),(1145,249),(1159,256),(1148,269),(1123,270),(1104,268)],
 'G06':[(1584,122),(1597,127),(1602,149),(1614,154),(1630,153),(1604,171),(1602,197),(1598,207),(1592,196),(1590,171),(1567,155),(1586,159)],
 'G07':[(1657,205),(1678,224),(1688,239),(1707,242),(1700,251),(1710,281),(1683,262),(1670,271),(1651,257),(1659,248),(1664,252),(1676,245),(1669,238)],
 'G11':[(430,412),(441,403),(454,411),(467,404),(477,411),(489,401),(498,410),(518,411),(526,420),(524,441),(511,454),(499,451),(487,457),(476,451),(461,458),(447,451),(436,452),(426,437)],
 'G13':[(563,450),(573,438),(593,438),(608,450),(608,469),(596,482),(578,483),(565,473)],
 'G14':[(416,482),(437,477),(449,484),(455,497),(470,501),(465,519),(450,526),(459,541),(442,546),(412,545),(419,531),(438,518),(434,500),(424,498)],
 'G16':[(639,538),(658,516),(675,510),(690,521),(706,523),(716,510),(742,509),(753,519),(750,534),(731,537),(713,540),(696,556),(668,560),(651,552)],
 'G19':[(1081,468),(1095,466),(1104,474),(1109,485),(1118,491),(1111,500),(1098,501),(1086,494),(1077,483)],
 'G20':[(1041,507),(1051,506),(1063,513),(1065,522),(1081,524),(1096,537),(1102,550),(1087,557),(1070,555),(1050,544),(1041,529)],
 'G21':[(1176,421),(1181,417),(1187,426),(1196,426),(1202,415),(1207,421),(1204,435),(1217,438),(1217,450),(1207,453),(1195,449),(1186,452),(1184,441),(1176,433)],
 'G23':[(1132,628),(1144,614),(1166,610),(1187,612),(1203,621),(1220,622),(1215,629),(1221,637),(1204,635),(1189,643),(1163,644),(1143,637)],
 'H01':[(454,141),(474,149),(491,143),(516,153),(536,166),(536,186),(519,199),(542,200),(529,208),(478,208),(453,196),(472,188),(466,173)],
 'H03':[(1587,122),(1598,126),(1602,150),(1630,153),(1605,172),(1602,201),(1596,209),(1592,173),(1567,156),(1589,159)],
}

def make_mask(im,it,box):
    x0,y0,x1,y1=box; xx0,yy0,xx1,yy1=it['box'];h,w=im.shape[:2]
    hsv=cv2.cvtColor(im,cv2.COLOR_RGB2HSV).astype(np.float32)
    H,S,V=cv2.split(hsv)
    if it['id'] in POLYS:
        env=poly(im.shape,[(x-x0,y-y0) for x,y in POLYS[it['id']]])>0
    else:
        env=np.zeros((h,w),np.uint8)
        if it['method']=='wind':
            # Taper foliage envelopes at the root so ground texture is excluded.
            cx=(xx0+xx1)/2;cy=(yy0+yy1)/2
            cv2.ellipse(env,(round(cx-x0),round(cy-y0)),(max(2,round((xx1-xx0)*.49)),max(2,round((yy1-yy0)*.49))),0,0,360,255,-1)
        else:env[max(0,yy0-y0):yy1-y0,max(0,xx0-x0):xx1-x0]=255
        env=env>0
    id=it['id'];method=it['method']
    border=np.concatenate([hsv[:8].reshape(-1,3),hsv[-8:].reshape(-1,3),hsv[:,:8].reshape(-1,3),hsv[:,-8:].reshape(-1,3)])
    bgv=float(np.median(border[:,2])); bgs=float(np.median(border[:,1]))
    if method=='wind':
        if id in ['G08','G09','G10','G12','G15','G24','G25','G31']:
            fg=(H<70)&(S>35)&(V<bgv-12)
        elif id in ['G35','G36','G37','G38']:
            fg=(H<65)&(S>32)&(V<205)
        else:
            fg=((V<bgv-23)&(S>45))|((S<min(120,bgs*.70))&(V>bgv+15))
    elif id in ['G01','G02','G03','G06','G07']:
        # Sky is cyan; silhouettes are warm paint, dark ink or bright feathers.
        fg=((H<56)&(S>48))|(V<bgv-28)|((S>100)&(H>96))
        if id=='G07':fg=(V<159)|(V>188)|(S>104)
        if id=='G03':
            line=np.zeros((h,w),np.uint8)
            cv2.polylines(line,[np.array([(x-x0,y-y0) for x,y in POLYS[id]],np.int32)],True,255,1,cv2.LINE_AA)
            return blur(line.astype(np.float32)/255,.45)+env*.10
    elif id in ['H01','H03']:
        bg=np.median(im[np.logical_not(env)],axis=0)
        fg=np.linalg.norm(im.astype(np.float32)-bg,axis=2)>17
    elif id in ['G11','G21','G14']:
        fg=((H<35)&(V<160))|(V<100)|((S<83)&(V>160))
    elif id in ['G19','G20','G16','G23']:
        fg=((H<50)&(V>93))|(V<120)
    elif id=='G13':fg=env
    elif id in ['G22','G39','H04']:
        fg=((H<35)&(S<143)&(V>115))|(V<75)
        if id=='H04':
            yy,xx=np.mgrid[0:h,0:w]; fg=(V<48)&(yy+y0>375)&(yy+y0<405)&(xx+x0>68)&(xx+x0<97)
    else:fg=env
    matte=np.uint8(env&fg)*255
    if method not in ['wind','puppet']:
        matte=cv2.morphologyEx(matte,cv2.MORPH_CLOSE,np.ones((2,2),np.uint8))
    return blur(matte.astype(np.float32)/255,.45)

class Cutout:
    def __init__(self,base,it):
        self.it=it;id=it['id'];x0,y0,x1,y1=it['box'];pad=14
        self.box=(max(0,x0-pad),max(0,y0-pad),min(base.shape[1],x1+pad),min(base.shape[0],y1+pad))
        a,b,c,d=self.box;self.rgb=base[b:d,a:c].astype(np.float32)
        self.alpha=make_mask(np.uint8(self.rgb),it,self.box)
        removal=cv2.dilate(np.uint8(self.alpha>.15)*255,np.ones((3,3),np.uint8))
        self.remove=blur(removal.astype(np.float32)/255,.45)
        self.clean=cv2.inpaint(np.uint8(self.rgb),removal,4,cv2.INPAINT_TELEA).astype(np.float32)
        self.phase=int(id[1:])*.73
        self.pivot=((x0+x1)/2-a,y1-b-3)
        Image.fromarray(np.uint8(self.alpha*255)).save(MASKS/f'{id}.png')
        self.model=None
        self.flow=None
        if it.get('job'):
            cache=OUT/'generation'/it['job']/'accepted-poses.npz'
            if cache.exists():
                with np.load(cache) as z:self.model={k:z[k] for k in z.files}
            flowcache=OUT/'generation'/it['job']/'accepted-flow.npz'
            if flowcache.exists():
                with np.load(flowcache) as z:self.flow=z['flow']
    def render(self,frame,p):
        a,b,c,d=self.box;w,h=c-a,d-b;id=self.it['id'];kind=self.it['method']
        q=p+self.phase;s=math.sin(q);s2=math.sin(2*q+.5)
        mat=np.array([[1.,0.,0.],[0.,1.,0.]],np.float32)
        if kind=='wind':
            # 3–7 painted pixels at canopy tips, roots anchored. No building warp.
            amplitude=min(5.0,max(2.5,240/max(30,h)))
            mat=cv2.getRotationMatrix2D(self.pivot,amplitude*(.8*s+.2*s2),1)
        elif id in ['G02','G06','H01','H03']:
            mat=cv2.getRotationMatrix2D((w/2,h/2),1.3*s,1);mat[1,2]+=4*s
        elif id=='G13':
            sx=1+.045*s;sy=1-.035*s;px,py=self.pivot
            mat=np.array([[sx,0,px*(1-sx)],[0,sy,py*(1-sy)]],np.float32)
        elif id in ['G03','G05']:
            mat=cv2.getRotationMatrix2D(self.pivot,5*s,1)
        elif id=='G23':mat[1,2]=2.6*s;mat[0,2]=1.5*math.sin(p)
        elif id=='G16':mat=cv2.getRotationMatrix2D((w*.42,h*.7),2.4*s,1)
        elif kind=='orbis' and self.model is not None:
            obj=self.model;u=(1-math.cos(p))/2
            ox0,oy0,ox1,oy1=[int(v) for v in obj['box']]
            patch=frame[oy0:oy1,ox0:ox1]
            patch=over(patch,obj['clean'],obj['removal'])
            frame[oy0:oy1,ox0:ox1]=over(patch,sample(obj['rgb'],u),sample(obj['alpha'],u))
            return
        elif kind in ['orbis','puppet']:
            # Fallback: source-paint puppetry, explicitly recorded as such. Heads
            # and bodies remain one unchanging texture. No invented anatomy.
            if id=='G01':
                pass # the rider/tree/body has no translation; only fins flap
            elif id=='G07':mat[1,2]=2.8*s
            else:
                mat=cv2.getRotationMatrix2D(self.pivot,1.5*s,1)
                mat[0,2]+=1.8*math.sin(p)
        # Sub-part wing articulation is applied in local coordinates below.
        rgb=self.rgb;alpha=self.alpha
        if self.flow is not None or id in ['G11','G21','G39','H04']:
            yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
            fx=np.zeros((h,w),np.float32);fy=np.zeros_like(fx)
            if self.flow is not None:
                flow=sample(self.flow,(1-math.cos(p))/2)
                fx+=flow[...,0];fy+=flow[...,1]
            if id in ['G11','G21','G39','H04']:
                gy=yy+b
                knee={'G11':436,'G21':443,'G39':393,'H04':394}[id]
                foot={'G11':457,'G21':453,'G39':406,'H04':406}[id]
                taper=np.clip((gy-knee)/max(1,foot-knee),0,1)
                fx+=1.6*taper*np.sin(2*p+(xx+a)*.35)
            mx=xx-fx;my=yy-fy
            ap=cv2.remap(alpha,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
            pm=cv2.remap(rgb*alpha[...,None],mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
            rgb=pm/np.maximum(ap[...,None],1e-5);alpha=ap
        if id in ['G01','G07','G14','G19','G20']:
            yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
            if id=='G01':
                cx,cy=116-a,207-b;wing=((xx+a<119)&(yy+b>183)&(yy+b<226))|((xx+a>143)&(yy+b>185)&(yy+b<221))
            elif id=='G07':cx,cy=1682-a,246-b;wing=yy+b<247
            elif id=='G14':cx,cy=444-a,531-b;wing=(yy+b>519)&(xx+a<460)
            elif id=='G19':cx,cy=1100-a,489-b;wing=(yy+b>482)&(xx+a>1092)
            else:cx,cy=1080-a,538-b;wing=(yy+b>525)&(xx+a>1067)
            wm=alpha*wing
            # A fixed source wing unfolds via a pivot, with the rest of the
            # creature retained. This avoids rectangular generated backgrounds.
            wa=cv2.getRotationMatrix2D((cx,cy),12*math.sin(2*p+self.phase),1)
            warped=cv2.warpAffine(wm,wa,(w,h));pr=cv2.warpAffine(rgb*wm[...,None],wa,(w,h))
            bodya=alpha*(1-wing);rgbprem=rgb*bodya[...,None]
            combined=warped+bodya*(1-warped)
            rgb=(pr+rgbprem*(1-warped[...,None]))/np.maximum(combined[...,None],1e-5);alpha=combined
        al=cv2.warpAffine(alpha,mat,(w,h),flags=cv2.INTER_LINEAR)
        pm=cv2.warpAffine(rgb*alpha[...,None],mat,(w,h),flags=cv2.INTER_LINEAR)
        patch=over(frame[b:d,a:c],self.clean,self.remove)
        frame[b:d,a:c]=patch*(1-al[...,None])+pm

class Flock:
    def __init__(self,base,it):
        self.it=it;x0,y0,x1,y1=it['box'];self.box=it['box']
        im=base[y0:y1,x0:x1]; gray=cv2.cvtColor(im,cv2.COLOR_RGB2GRAY)
        # Local dark-ink contrast isolates real painted birds from canvas grain.
        residual=cv2.GaussianBlur(gray,(0,0),3).astype(float)-gray
        threshold=8.0 if it['layer']=='garden' else 4.7
        m=np.uint8(residual>threshold)*255
        n,labels,stats,_=cv2.connectedComponentsWithStats(m,8)
        keep=np.zeros_like(m)
        for k in range(1,n):
            x,y,w,h,area=stats[k]
            if 4<=area<=95 and 4<=w<=18 and 2<=h<=10 and w>=h*1.2 and y<im.shape[0]*.85:
                keep[labels==k]=255
        self.a=blur(keep.astype(np.float32)/255,.35)
        self.rgb=im.astype(np.float32)
        rem=cv2.dilate(keep,np.ones((3,3),np.uint8));self.rem=blur(rem/255.,.5).astype(np.float32)
        self.clean=cv2.inpaint(im,rem,3,cv2.INPAINT_TELEA).astype(np.float32)
        self.birds=[]
        n,labels,stats,_=cv2.connectedComponentsWithStats(keep,8)
        for k in range(1,n):
            x,y,w,h,_=stats[k];pad=5
            box=(max(0,x-pad),max(0,y-pad),min(im.shape[1],x+w+pad),min(im.shape[0],y+h+pad))
            self.birds.append((box,k,labels))
        Image.fromarray(keep).save(MASKS/f'{it["id"]}.png')
    def render(self,f,p):
        x0,y0,x1,y1=self.box;patch=over(f[y0:y1,x0:x1],self.clean,self.rem)
        for idx,(box,k,labels) in enumerate(self.birds):
            a,b,c,d=box;h,w=d-b,c-a;al=self.a[b:d,a:c]*(labels[b:d,a:c]==k)
            sy=.7+.3*math.cos(3*p+idx)
            mat=np.array([[1,0,2.2*math.sin(p+idx*.2)],[0,sy,h/2*(1-sy)+1.4*math.sin(2*p+idx)]],np.float32)
            aa=cv2.warpAffine(al,mat,(w,h));pm=cv2.warpAffine(self.rgb[b:d,a:c]*al[...,None],mat,(w,h))
            patch[b:d,a:c]=patch[b:d,a:c]*(1-aa[...,None])+pm
        f[y0:y1,x0:x1]=patch

class MarkedMotion:
    def __init__(self,garden,hell):
        self.bases={'garden':garden,'hell':hell};self.actors={'garden':[],'hell':[]};self.flocks={}
        self.fireitems=[i for i in CAT if i['method']=='fire-smoke']
        for it in CAT:
            if it['method'] in ['water','waterfall','fire-smoke']:continue
            if it['method']=='flock':self.flocks[it['layer']]=Flock(self.bases[it['layer']],it)
            else:self.actors[it['layer']].append(Cutout(self.bases[it['layer']],it))
        self.setup_water(hell);self.setup_falls(garden);self.make_matte_sheet()
    def make_matte_sheet(self):
        actors=sum(self.actors.values(),[]);cw,ch=200,155
        sheet=Image.new('RGB',(cw*6,ch*math.ceil(len(actors)/6)),(22,24,22));d=ImageDraw.Draw(sheet)
        for n,obj in enumerate(actors):
            a=np.clip(obj.rgb*.5+np.stack([obj.alpha*80,np.zeros_like(obj.alpha),obj.alpha*50],-1),0,255).astype(np.uint8)
            im=Image.fromarray(a);im.thumbnail((195,125));x=n%6*cw;y=n//6*ch
            sheet.paste(im,(x,y+25));d.text((x+3,y+4),obj.it['id']+' '+obj.it['method'],fill='white')
        sheet.save(OUT/'cutout-review.jpg',quality=93)
    def setup_falls(self,base):
        self.falls=[]
        # Narrow paths track the existing white streams, excluding the domes.
        for points in [[(804,388),(807,422),(799,464),(787,501),(783,537),(787,562)],[(962,390),(976,424),(990,462),(999,504),(1002,546),(999,565)]]:
            m=np.zeros(base.shape[:2],np.uint8);cv2.polylines(m,[np.array(points,np.int32)],False,255,6,cv2.LINE_AA)
            yy,xx=np.indices(m.shape,dtype=np.float32)
            self.falls.append((blur(m/255.,1.0).astype(np.float32),xx,yy))
    def setup_water(self,hell):
        pts=[(0,596),(95,586),(200,576),(305,560),(410,545),(500,520),(640,490),(712,449),(772,438),(804,440),(810,505),(969,514),(978,451),(1056,435),(1140,446),(1235,462),(1331,463),(1380,500),(1437,537),(1513,553),(1585,551),(1654,535),(1773,518),(1773,635),(1663,645),(1585,665),(1470,660),(1360,675),(1220,681),(1110,677),(1000,684),(875,682),(761,688),(649,683),(538,681),(424,675),(305,666),(208,667),(97,647),(0,665)]
        env=poly(hell.shape,pts);hsv=cv2.cvtColor(hell,cv2.COLOR_RGB2HSV)
        m=(env>0)&(hsv[...,2]<107)&((hsv[...,1]<110)|(hsv[...,0]>5))
        # Central face, both shell buildings, foreground lute and islands stay fixed.
        for ps in [[(736,375),(1032,375),(1048,571),(727,575)],[(1394,409),(1580,409),(1595,574),(1397,574)],[(280,544),(369,548),(356,594),(286,596)],[(1291,631),(1410,616),(1413,692),(1286,697)]]:m[poly(hell.shape,ps)>0]=False
        # Pool left of the spherical shell has its own bank outline.
        pool=np.zeros(hell.shape[:2],np.uint8);cv2.ellipse(pool,(1236,480),(141,17),0,0,360,255,-1)
        m|=(pool>0)&(hsv[...,2]<100)
        self.hm=blur(cv2.erode(np.uint8(m)*255,np.ones((3,3),np.uint8))/255.,.7).astype(np.float32)
        self.hell=hell.astype(np.float32);self.yy,self.xx=np.indices(hell.shape[:2],dtype=np.float32)
        Image.fromarray(np.uint8(self.hm*255)).save(MASKS/'H12.png')
    def water(self,f,p):
        # Horizontal ripples in dark water, with visible warm reflected highlights.
        y0,y1=432,691;xx=self.xx[y0:y1];yy=self.yy[y0:y1]
        dx=2.8*np.sin(.16*yy+.011*xx-p)+1.6*np.sin(.29*yy-.012*xx+2*p)
        dy=.75*np.sin(.19*yy+.018*xx+p)
        rgb=cv2.remap(self.hell[y0:y1],xx+dx,yy-y0+dy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)
        orange=np.clip((rgb[...,0]-rgb[...,2]-9)/30,0,1)
        light=(2.1+orange*5)*np.sin(.31*yy+.018*xx-2*p)
        rgb=np.clip(rgb+light[...,None]*np.array([1,.7,.4],np.float32),0,255)
        f[y0:y1]=over(f[y0:y1],rgb,self.hm[y0:y1])
    def fire(self,f,p):
        # Procedural smoke and flame accents augment the existing Orbis keyed
        # fire. Only emission and translucent smoke move; buildings never warp.
        base=self.bases['hell']
        for n,it in enumerate(self.fireitems):
            if it['id']=='H10':continue # retained original Orbis city covers this one
            x0,y0,x1,y1=it['box'];ref=base[y0:y1,x0:x1].astype(np.float32)
            h,w=ref.shape[:2];yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
            hsv=cv2.cvtColor(np.uint8(ref),cv2.COLOR_RGB2HSV)
            warm=np.clip((ref[...,0]-ref[...,2]-15)/35,0,1)*np.clip((ref[...,0]-38)/50,0,1)
            skyline=(hsv[...,2]<63)&(yy>h*.49)
            flicker=.6+.4*np.sin(2*p+n*.7+xx*.23+yy*.24)
            a=blur(warm*flicker,1.0)*.30; a[skyline]=0
            f[y0:y1,x0:x1]=over(f[y0:y1,x0:x1],np.full_like(ref,[170,89,31]),a)
            # Three billowing, slow smoke wisps; sinusoidal field is periodic.
            smoke=np.zeros((h,w),np.float32)
            for k in range(3):
                cx=w*(.35+.19*k)+3*np.sin(p+n+k)-.14*yy
                band=np.exp(-((xx-cx)/(8+yy*.15))**2)
                smoke+=band*(.55+.45*np.sin(.13*yy+p+k))
            smoke*=np.sin(np.pi*np.clip(yy/h,0,1))**2*.045
            smoke[skyline]=0
            f[y0:y1,x0:x1]=over(f[y0:y1,x0:x1],np.full_like(ref,[73,69,59]),smoke)
    def render(self,frame,layer,p):
        if layer=='hell':self.water(frame,p);self.fire(frame,p)
        for obj in self.actors[layer]:obj.render(frame,p)
        if layer in self.flocks:self.flocks[layer].render(frame,p)
        if layer=='garden':
            for mask,xx,yy in self.falls:
                wave=3.8*np.sin(yy*.37-4*p)+1.7*np.sin(yy*.71-6*p)
                frame+=mask[...,None]*wave[...,None]*np.array([.8,1,1],np.float32)
        return frame
