"""Object mattes and controlled painted motion; never warp an environment tile.

Orbis supplies the bird poses and fire shapes. Horse-head articulation, trees and
whole-river ripples are deterministic 2D animation. This is a hybrid, not a claim
that Orbis generated an intact, stable panoramic movie.
"""
from pathlib import Path
import ast, json, math, subprocess, os
import cv2
import numpy as np
from PIL import Image
import imageio_ffmpeg
from analyze_orbis_painting import registration
from bosch_marked_motion_v9 import MarkedMotion

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'orbis-test/delivery-v6'
OUT.mkdir(exist_ok=True)
JOBS={j['id']:j for j in json.loads((ROOT/'orbis-test/jobs.json').read_text(encoding='utf-8'))}
N=240; FPS=30
# Reuse the already checked projection, without importing the old compositor's
# top-level generation job or retaining any of its motion processing.
tree=ast.parse((ROOT/'composite_orbis_painting_v2.py').read_text(encoding='utf-8'))
for node in tree.body:
    if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name in ('source_rgb','encode_frames','smoothstep','Panorama'):
        exec(compile(ast.Module(body=[node],type_ignores=[]),'projection_helpers','exec'))

def blur(a,sigma): return cv2.GaussianBlur(a,(0,0),sigma)

def polygon(shape,points):
    m=np.zeros(shape[:2],np.uint8)
    cv2.fillPoly(m,[np.array(points,np.int32)],255)
    return m

def blend(base,rgb,alpha):
    return base*(1-alpha[...,None])+rgb*alpha[...,None]

def time_filter(stack,sigma=1.3):
    r=math.ceil(sigma*3);weights=np.exp(-np.arange(-r,r+1)**2/(2*sigma*sigma));weights/=weights.sum()
    padded=np.pad(stack,((r,r),(0,0),(0,0),(0,0)),mode='edge')
    return sum(w*padded[i:i+len(stack)] for i,w in enumerate(weights))

def sample(stack,u):
    p=np.clip(u,0,1)*(len(stack)-1);a=int(p);b=min(a+1,len(stack)-1)
    return stack[a]*(1-(p-a))+stack[b]*(p-a)

def read_registered(name,run):
    job=JOBS[name]; x0,y0,x1,y1=job['crop']
    ref=np.asarray(Image.open(ROOT/'orbis-test'/name/'reference.png').convert('RGB'))
    support=np.asarray(Image.open(ROOT/'orbis-test'/name/'context-mask.png'))
    mask=np.where(support>2,0,255).astype(np.uint8)
    paths=sorted((ROOT/'orbis-test'/name/run/'frames').glob('*.jpg'))
    matrices=[];frames=[];last=np.array([[1,0,0],[0,1,0]],np.float64)
    for p in paths:
        f=np.asarray(Image.open(p).convert('RGB'))
        mat,_=registration(ref,f,mask)
        if mat is not None:last=mat
        matrices.append(last.copy());frames.append(f)
    # Smooth the registration trajectory: frame-to-frame RANSAC noise must not
    # become a new camera movement in a small foreground object.
    matrices=np.asarray(matrices)
    for i in range(2):
        for j in range(3):
            v=matrices[:,i,j];pad=np.pad(v,(4,4),mode='edge')
            matrices[:,i,j]=np.convolve(pad,np.ones(9)/9,mode='valid')
    output=[]
    for f,mat in zip(frames,matrices):
        f=cv2.warpAffine(f,mat,(1024,576),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)
        output.append(cv2.resize(f,(x1-x0,y1-y0),interpolation=cv2.INTER_AREA))
    print('registered',name,len(output),flush=True)
    return np.array(output,dtype=np.float32)

def exposure_match(stack,reference,envelope):
    valid=envelope==0
    coeff=[]
    for f in stack:
        a=[];b=[]
        for c in range(3):
            x=f[...,c][valid];y=reference[...,c][valid]
            # Trim outliers such as a reconstructed flower or a new highlight.
            sel=(x>np.quantile(x,.10))&(x<np.quantile(x,.90))
            xx=x[sel];yy=y[sel]
            gain=np.clip(np.std(yy)/(np.std(xx)+1e-5),.65,1.5)
            a.append(gain);b.append(np.median(yy-gain*xx))
        coeff.append([a,b])
    coeff=np.asarray(coeff)
    for i in range(2):
        for c in range(3):
            v=coeff[:,i,c];coeff[:,i,c]=np.convolve(np.pad(v,(4,4),mode='edge'),np.ones(9)/9,mode='valid')
    result=[]
    for f,(a,b) in zip(stack,coeff):
        matched=f*a+b
        # A masked low-frequency correction catches spatial exposure gradients,
        # using only the unanimated surroundings, never the bird's moving wing.
        v=valid.astype(np.float32);den=np.maximum(blur(v,13),.015)
        bias=blur((matched-reference)*v[...,None],13)/den[...,None]
        result.append(np.clip(matched-bias,0,255))
    return np.array(result,np.float32),coeff

def object_matte(rgb,name,box):
    x0,y0,x1,y1=box;h,w=rgb.shape[:2]
    yy,xx=np.mgrid[y0:y1,x0:x1]
    hsv=cv2.cvtColor(np.uint8(np.clip(rgb,0,255)),cv2.COLOR_RGB2HSV)
    if name=='bird':
        pts=[(135,563),(153,539),(198,519),(260,523),(294,544),(302,576),(278,601),(240,607),(200,609),(161,607),(136,587)]
        envelope=polygon(rgb.shape,[(x-x0,y-y0) for x,y in pts])
        blue=(hsv[...,0]>83)&(hsv[...,0]<125)&(hsv[...,1]>58)&(yy<605)
        cream=(xx>215)&(xx<251)&(yy>535)&(yy<595)&(hsv[...,0]>10)&(hsv[...,0]<38)&(hsv[...,2]>130)&(hsv[...,1]<145)
        seeds=(blue|cream)&(envelope>0)
    else:
        pts=[(45,489),(63,482),(93,484),(119,496),(131,516),(158,541),(138,548),(102,544),(68,544),(45,532)]
        envelope=polygon(rgb.shape,[(x-x0,y-y0) for x,y in pts])
        seeds=(hsv[...,1]<88)&(hsv[...,2]>127)&(envelope>0)
    gc=np.zeros((h,w),np.uint8)
    gc[envelope>0]=cv2.GC_PR_BGD
    gc[seeds]=cv2.GC_PR_FGD
    sure=cv2.erode(np.uint8(seeds)*255,np.ones((3,3),np.uint8))>0
    gc[sure]=cv2.GC_FGD
    if sure.any():
        cv2.grabCut(np.uint8(np.clip(rgb,0,255)),gc,None,np.zeros((1,65)),np.zeros((1,65)),3,cv2.GC_INIT_WITH_MASK)
    alpha=np.uint8((gc==cv2.GC_FGD)|(gc==cv2.GC_PR_FGD))*255
    alpha=cv2.morphologyEx(alpha,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
    if name=='bird':
        # Feet and beak stay in the fixed painting. Only the pose-bearing body,
        # neck and wings are replaced; water below the feet never joins the matte.
        alpha[yy>604]=0
    # Discard disconnected blue flowers/decorations picked up by the color key.
    count,labels,stats,_=cv2.connectedComponentsWithStats(alpha,8)
    if count>1:
        main_label=1+np.argmax(stats[1:,cv2.CC_STAT_AREA])
        alpha[labels!=main_label]=0
    feather=blur(alpha.astype(np.float32)/255,.55)
    feather[envelope==0]=0
    return feather,envelope

def prepare_animal(base,name):
    cache=OUT/f'{name}-object-cache.npz'
    if cache.exists():
        print('cached',name,flush=True)
        with np.load(cache) as z:return {k:z[k] for k in z.files}
    box=JOBS[name]['crop'];x0,y0,x1,y1=box
    reference=base[y0:y1,x0:x1].astype(np.float32)
    original_matte,envelope=object_matte(reference,name,box)
    source=read_registered(name,'run-dynamic-v2')
    matched,coeff=exposure_match(source,reference,envelope)
    alphas=[]
    for f in matched:
        a,_=object_matte(f,name,box);alphas.append(a)
    # Smooth matte values without moving the silhouette over the background.
    aa=np.array(alphas,np.float32)
    aa=(np.pad(aa,((1,1),(0,0),(0,0)),mode='edge')[:-2]+2*aa+np.pad(aa,((1,1),(0,0),(0,0)),mode='edge')[2:])/4
    rgb=time_filter(matched,.65)
    removal=cv2.dilate(np.uint8(original_matte>.12)*255,np.ones((3,3),np.uint8))
    clean=cv2.inpaint(np.uint8(reference),removal,4,cv2.INPAINT_TELEA).astype(np.float32)
    # The clean plate is introduced only under the original bird, never over a
    # whole rectangular tile. Its perimeter cannot breathe with model exposure.
    ra=blur(removal.astype(np.float32)/255,.55)
    plate=blend(reference,clean,ra)
    Image.fromarray(np.uint8(plate)).save(OUT/f'{name}-clean-plate.png')
    for i in (0,len(aa)//2,len(aa)-1):
        Image.fromarray(np.uint8(aa[i]*255)).save(OUT/f'{name}-alpha-{i}.png')
    print('matted',name,flush=True)
    result=dict(box=box,rgb=rgb,alpha=aa,plate=plate,original=reference,envelope=envelope,coeff=coeff)
    np.savez_compressed(cache,**result)
    return result

def make_trees(base):
    h,w=base.shape[:2]
    # Pixel polygons isolate only tree silhouettes against sky. All architecture
    # is excluded before transforming anything. The two trees above the shell
    # are separate objects with separate branch anchors.
    specs=[
        dict(name='shell-right',box=(1074,185,1142,288),poly=[(1081,209),(1090,193),(1119,190),(1134,205),(1137,237),(1123,257),(1100,285),(1096,274),(1100,246),(1080,230)],pivot=(1100,282),angle=2.6,phase=0),
        dict(name='shell-left',box=(1004,233,1071,294),poly=[(1010,255),(1021,241),(1043,239),(1056,250),(1067,288),(1058,290),(1043,274),(1020,284),(1010,275)],pivot=(1065,291),angle=2.8,phase=.8),
        dict(name='left-tower',box=(269,137,374,273),poly=[(274,174),(285,149),(319,140),(350,150),(369,176),(365,208),(338,229),(315,268),(308,261),(313,224),(286,210)],pivot=(314,265),angle=1.8,phase=1.5),
        dict(name='far-left',box=(107,109,178,190),poly=[(113,136),(119,118),(143,112),(167,124),(172,150),(159,176),(147,186),(147,158),(119,153)],pivot=(147,185),angle=2.0,phase=2.5),
    ]
    objects=[];plate=base.astype(np.float32).copy();support=np.zeros((h,w),np.uint8)
    for s in specs:
        x0,y0,x1,y1=s['box'];rgb=base[y0:y1,x0:x1]
        env=polygon(rgb.shape,[(x-x0,y-y0) for x,y in s['poly']])
        hsv=cv2.cvtColor(rgb,cv2.COLOR_RGB2HSV)
        colors=(hsv[...,0]<62)&(hsv[...,1]>43)&(hsv[...,2]<210)
        matte=(env>0)&colors
        # Include the fine connecting branch with a hand-defined stem.
        stem=np.zeros_like(env)
        if s['name']=='shell-right':cv2.line(stem,(1100-x0,282-y0),(1110-x0,225-y0),255,2)
        if s['name']=='shell-left':cv2.line(stem,(1065-x0,291-y0),(1038-x0,262-y0),255,2)
        matte=np.maximum(np.uint8(matte)*255,stem)
        matte=cv2.morphologyEx(matte,cv2.MORPH_CLOSE,np.ones((2,2),np.uint8))
        alpha=blur(matte.astype(np.float32)/255,.45)
        remove=cv2.dilate(matte,np.ones((3,3),np.uint8))
        clean=cv2.inpaint(rgb,remove,4,cv2.INPAINT_TELEA)
        plate[y0:y1,x0:x1]=blend(plate[y0:y1,x0:x1],clean,blur(remove.astype(np.float32)/255,.45))
        s.update(rgb=rgb.astype(np.float32),alpha=alpha)
        objects.append(s)
        support[y0:y1,x0:x1]=255
        Image.fromarray(np.uint8(alpha*255)).save(OUT/(s['name']+'-matte.png'))
    return objects,plate,support

def water_setup(base):
    h,w=base.shape[:2]
    pts=[(0,603),(130,603),(235,595),(325,564),(414,545),(532,523),(637,492),(725,446),(760,434),(819,434),(829,492),(971,494),(983,456),(1054,436),(1131,443),(1195,462),(1303,462),(1338,481),(1394,500),(1430,532),(1496,551),(1573,552),(1644,535),(1773,514),(1773,631),(1662,640),(1580,657),(1497,654),(1373,666),(1254,673),(1107,668),(1018,673),(894,669),(810,675),(736,687),(650,684),(552,679),(443,674),(332,657),(245,662),(127,645),(0,664)]
    hsv=cv2.cvtColor(base,cv2.COLOR_RGB2HSV)
    m=(polygon(base.shape,pts)>0)&(hsv[...,0]>76)&(hsv[...,0]<122)&(hsv[...,1]>19)&(hsv[...,2]>50)
    # Shoreline, islands, people and architectural reflections stay anchored.
    m=cv2.morphologyEx(np.uint8(m)*255,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
    m=cv2.erode(m,np.ones((3,3),np.uint8))
    # Blue paint also occurs on buildings and animals. Color selection alone is
    # insufficient: explicitly occlude the central fountain, right shell and ducks.
    for points in [
        [(806,208),(970,208),(986,576),(800,576)],
        [(1398,411),(1572,411),(1593,568),(1412,571)],
        [(1030,468),(1116,468),(1116,562),(1030,562)],
        [(617,511),(751,511),(751,561),(617,561)],
        [(545,533),(611,533),(616,605),(549,605)],
    ]:m[polygon(base.shape,points)>0]=0
    alpha=blur(m.astype(np.float32)/255,.8)
    Image.fromarray(np.uint8(alpha*255)).save(OUT/'whole-river-matte.png')
    return alpha

def prepare_fire(base):
    cache=OUT/'fire-object-cache.npz'
    if cache.exists():
        print('cached fire',flush=True)
        with np.load(cache) as z:return {k:z[k] for k in z.files}
    box=JOBS['fire']['crop'];x0,y0,x1,y1=box
    ref=base[y0:y1,x0:x1].astype(np.float32)
    # Include flame tips and smoke; exclude the two foreground shell buildings.
    env=polygon(ref.shape,[(x-x0,y-y0) for x,y in [(1198,315),(1208,270),(1255,220),(1329,201),(1404,221),(1471,272),(1488,324),(1415,335),(1280,335)]])
    source=read_registered('fire','run-stable-01')
    matched,coeff=exposure_match(source,ref,env)
    matched=time_filter(matched,1.4)
    hsv=cv2.cvtColor(np.uint8(ref),cv2.COLOR_RGB2HSV)
    # Static dark city/roof geometry is an occluder in FRONT of the fire layer.
    yy,xx=np.mgrid[y0:y1,x0:x1]
    building=(hsv[...,2]<70)&(yy>270)&(xx>1203)&(xx<1480)
    building=cv2.dilate(np.uint8(building)*255,np.ones((2,2),np.uint8)).astype(np.float32)/255
    layers=[];alphas=[]
    for f in matched:
        r,g,b=f[...,0],f[...,1],f[...,2]
        # Emissive color key, not a rectangular luminance residual. It retains
        # actual licking flame shapes and never deforms the skyline.
        emission=np.clip((r-g*1.12-12)/30,0,1)*np.clip((r-65)/65,0,1)
        a=blur(emission,1.0)*(env/255)*(1-building)
        a=np.clip(a*.9,0,.92)
        layers.append(f);alphas.append(a)
    result=dict(box=box,rgb=np.array(layers,np.float32),alpha=np.array(alphas,np.float32),building=building,coeff=coeff)
    np.savez_compressed(cache,**result)
    return result

def horse_head_setup(base):
    """One fixed painted head, articulated as a rigid cutout: no changing mouth RGB."""
    box=(105,496,162,550);x0,y0,x1,y1=box
    rgb=base[y0:y1,x0:x1].astype(np.float32)
    points=[(112,502),(119,506),(121,512),(126,518),(129,523),
            (133,522),(135,520),(135,525),(132,528),(156,539),
            (156,541),(133,532),(133,540),(130,543),(125,542),
            (124,535),(124,527),(119,522),(114,519),(112,512)]
    env=polygon(rgb.shape,[(x-x0,y-y0) for x,y in points])
    hsv=cv2.cvtColor(np.uint8(rgb),cv2.COLOR_RGB2HSV)
    foreground=(hsv[...,1]<107)|(hsv[...,2]<86)
    mask=np.uint8((env>0)&foreground)*255
    alpha=blur(mask.astype(np.float32)/255,.45)
    removal=cv2.dilate(mask,np.ones((3,3),np.uint8))
    clean=cv2.inpaint(np.uint8(rgb),removal,3,cv2.INPAINT_TELEA).astype(np.float32)
    ra=blur(removal.astype(np.float32)/255,.6)
    Image.fromarray(np.uint8(alpha*255)).save(OUT/'horse-fixed-head-alpha.png')
    Image.fromarray(np.uint8(rgb)).save(OUT/'horse-fixed-head-rgb.png')
    return dict(box=box,rgb=rgb,alpha=alpha,clean=clean,removal=ra,pivot=(114-x0,508-y0))

def main():
    garden=source_rgb('garden');hell=source_rgb('hell');h,w=garden.shape[:2]
    animals={'bird':prepare_animal(garden,'bird')}
    head=horse_head_setup(garden)
    trees,treeplate,treesupport=make_trees(garden)
    for tr in trees:
        if tr['name']=='far-left':
            x0,y0,x1,y1=tr['box'];treeplate[y0:y1,x0:x1]=garden[y0:y1,x0:x1]
    trees=[tr for tr in trees if tr['name']!='far-left']
    marked=MarkedMotion(garden,hell)
    water=water_setup(garden);fire=prepare_fire(hell)
    wy0,wy1=420,694
    yy,xx=np.mgrid[wy0:wy1,0:w].astype(np.float32)
    water_base=garden[wy0:wy1]
    strips=[];hellstrips=[];metrics={'method':'fixed painted horse head; object mattes; stronger whole-river texture flow; keyed generated fire','new_model_calls':0,'frames':N,'fps':FPS,'duration_seconds':N/FPS,'notes':'Bird/fire reuse actual Orbis recordings. Horse head, trees and water are authored 2D motion. The horse mouth is a single fixed painted texture, with a fixed alpha, rotated about the neck anchor. No whole-environment optical flow or dynamic rectangular backgrounds.','headset_verified':False,'horse_mouth_rgb_regenerated_per_frame':False}
    protected=polygon(garden.shape,[(1080,300),(1146,279),(1206,330),(1197,402),(1088,401),(1035,342)])>0
    # Also preserve the mast, finial and shell roof under the two new cutouts.
    protected|=polygon(garden.shape,[(1065,242),(1084,240),(1083,298),(1064,298)])>0
    building_changes=0;fire_city_changes=0;bird_outside_changes=0
    for i in range(N):
        t=i/FPS;phase=2*np.pi*t/8;u=(1-np.cos(phase))/2
        frame=treeplate.copy()
        # Larger travelling ripples remain restricted to the water silhouette.
        dx=4.8*np.sin(.11*yy+.012*xx-phase)+1.9*np.sin(.19*yy-.013*xx+2*phase)
        dy=1.65*np.sin(.14*yy+.016*xx+phase)
        rippled=cv2.remap(water_base,xx+dx,yy-wy0+dy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101).astype(np.float32)
        highlights=6.8*np.sin(.24*yy+.013*xx-phase)+2.6*np.sin(.39*yy-.018*xx+2*phase)
        # Painted elliptical rings make motion legible beside the bird's feet.
        radius=np.sqrt((xx-221)**2+((yy-623)*2.7)**2)
        rings=5.0*np.sin(radius*.32-2*phase)*np.exp(-radius/85)
        frame[wy0:wy1]=blend(frame[wy0:wy1],np.clip(rippled+(highlights+rings)[...,None],0,255),water[wy0:wy1])
        for tree in trees:
            x0,y0,x1,y1=tree['box'];cw,ch=x1-x0,y1-y0
            angle=tree['angle']*(.78*np.sin(phase+tree['phase'])+.22*np.sin(2*phase+tree['phase']))
            pivot=(tree['pivot'][0]-x0,tree['pivot'][1]-y0)
            mat=cv2.getRotationMatrix2D(pivot,angle,1)
            a=cv2.warpAffine(tree['alpha'],mat,(cw,ch),flags=cv2.INTER_LINEAR)
            premul=cv2.warpAffine(tree['rgb']*tree['alpha'][...,None],mat,(cw,ch),flags=cv2.INTER_LINEAR)
            target=frame[y0:y1,x0:x1]
            target[:]=target*(1-a[...,None])+premul
        # Architectural occluder wins over any tree pixel, at every frame.
        frame[protected]=garden[protected]
        building_changes+=int(np.count_nonzero(np.any(np.uint8(np.clip(frame,0,255))[protected]!=garden[protected],axis=1)))
        for name,obj in animals.items():
            x0,y0,x1,y1=obj['box']
            a=sample(obj['alpha'],u);rgb=sample(obj['rgb'],u)
            # Introduce the static clean plate only underneath the removed pose.
            orig,_=object_matte(obj['original'],name,obj['box']) if i==0 else (None,None)
            if i==0:
                obj['removal']=blur(cv2.dilate(np.uint8(orig>.12)*255,np.ones((3,3),np.uint8)).astype(np.float32)/255,.55)
            patch=frame[y0:y1,x0:x1]
            patch=blend(patch,obj['plate'],obj['removal'])
            patch=blend(patch,rgb,a)
            if name=='horse':
                # Hooves are planted. Preserve the original thin legs rather
                # than allowing a color matte to intermittently lose a leg.
                hy,hx=np.mgrid[y0:y1,x0:x1]
                hsv=cv2.cvtColor(np.uint8(obj['original']),cv2.COLOR_RGB2HSV)
                legs=(hy>518)&(hy<544)&(hx<114)&(hsv[...,1]<84)&(hsv[...,2]>128)
                patch[legs]=obj['original'][legs]
            if name=='bird':
                exterior=(obj['envelope']==0)&(obj['removal']<.001)
                before=frame[y0:y1,x0:x1]
                bird_outside_changes+=int(np.count_nonzero(np.abs(patch-before)[exterior]>.01))
            frame[y0:y1,x0:x1]=patch
        # Original painted mouth and horn are one constant-color cutout. The
        # neck joint stays anchored; planted hooves and the horse body stay fixed.
        x0,y0,x1,y1=head['box'];cw,ch=x1-x0,y1-y0
        patch=frame[y0:y1,x0:x1]
        patch=blend(patch,head['clean'],head['removal'])
        mat=cv2.getRotationMatrix2D(head['pivot'],2.8*np.sin(phase),1)
        a=cv2.warpAffine(head['alpha'],mat,(cw,ch),flags=cv2.INTER_LINEAR)
        rgb=cv2.warpAffine(head['rgb']*head['alpha'][...,None],mat,(cw,ch),flags=cv2.INTER_LINEAR)
        frame[y0:y1,x0:x1]=patch*(1-a[...,None])+rgb
        frame=marked.render(frame,'garden',phase)
        frame[protected]=garden[protected]
        strips.append(np.uint8(np.clip(np.round(frame),0,255)))
        f=hell.astype(np.float32).copy();x0,y0,x1,y1=fire['box']
        # Smooth ping-pong source playback: a post-production loop, not a model
        # loop guarantee. Flame RGB and alpha are interpolated at 30 fps.
        a=sample(fire['alpha'],u);rgb=sample(fire['rgb'],u)
        p=blend(f[y0:y1,x0:x1],rgb,a)
        city=fire['building']>.99
        p[city]=hell[y0:y1,x0:x1][city]
        fire_city_changes+=int(np.count_nonzero(np.uint8(np.clip(p,0,255))[city]!=hell[y0:y1,x0:x1][city]))
        f[y0:y1,x0:x1]=p
        f=marked.render(f,'hell',phase)
        hellstrips.append(np.uint8(np.clip(np.round(f),0,255)))
    metrics['marked_motion_catalog']='art-lab/motion-v9/motion-catalog.json'
    metrics['intentionally_static']=['G03']
    metrics['revision']='r4 complete silhouettes, downward falling water, stronger rising fire/smoke'
    metrics['new_marked_regions']=51
    review=json.loads((ROOT/'motion-v8/generation-review.json').read_text())
    metrics['new_model_calls']=0
    metrics['prior_model_captures_reused']=len(review)
    metrics['new_model_rgb_layers_accepted']=0
    metrics['new_model_flow_layers_accepted']=[]
    metrics['prior_model_flow_layers_used']=['herd','stag','bathers']
    metrics['method']='complete hand-polygon original-paint sky objects; joined bird-wing articulation; original G03 held static; downward advected water and falling droplets; stronger rising fire and smoke; retained v7 horse and accepted prior motion outside corrected regions'
    metrics['notes']='User-reviewed correction. Complete object polygons intentionally include narrow safe background margins. No color-key holes through figures, mounts, fish tails, ornament wings or feet. Corrected regions use original paint with coherent articulation; G03 is intentionally static. Water falls down, smoke rises up. No camera movement. Not a physical fluid simulation or model-native loop.'
    metrics.update(architecture_changed_pixels_before_encoding=building_changes,fire_city_changed_values_before_encoding=fire_city_changes,bird_pixels_changed_outside_matte_envelope=bird_outside_changes,water_mask_pixels=int(np.count_nonzero(water>.1)))
    # Inspect native working-space clips before judging the compressed panorama.
    crops={'horse':(91,491,165,550),'bird':(122,510,310,637),'water':(757,584,1118,688),'fire':(1195,226,1492,340)}
    sheet=Image.new('RGB',(1440,980),(19,23,18))
    from PIL import ImageDraw
    draw=ImageDraw.Draw(sheet)
    for row,index in enumerate((0,60,120,180)):
        for col,(name,box) in enumerate(crops.items()):
            array=(hellstrips if name=='fire' else strips)[index]
            im=Image.fromarray(array).crop(box);im.thumbnail((350,210))
            sheet.paste(im,(col*360,row*245+28));draw.text((col*360+5,row*245+7),f'{name} {index/FPS:.1f}s',fill='white')
    sheet.save(OUT/'object-review.jpg',quality=94)
    if building_changes or fire_city_changes or bird_outside_changes:raise ValueError(metrics)
    for layer,frames,base in [('garden',strips,garden),('hell',hellstrips,hell)]:
        if os.environ.get('BOSCH_RENDER_LAYER') and layer!=os.environ['BOSCH_RENDER_LAYER']:continue
        encode_frames(frames,OUT/f'{layer}-source-motion.mp4',width=1776,crf=17)
        projector=Panorama(layer);projected=[projector.render(f) for f in frames]
        poster=projector.render(base)
        expected=np.asarray(Image.open(ROOT/'bosch-world-assets'/f'{layer}-equirect-2048.jpg').convert('RGB'))
        error=float(np.abs(expected.astype(np.float32)-poster).mean())
        if error>8:raise ValueError(f'{layer} projection error {error}')
        Image.fromarray(poster).save(OUT/f'{layer}-poster.jpg',quality=88)
        encode_frames(projected,OUT/f'{layer}-equirect-2048.mp4',crf=18)
        encode_frames(projected,OUT/f'{layer}-preview.mp4',width=2048,crf=31)
        metrics[layer]=dict(projection_difference=error,loop_difference=float(np.abs(frames[-1].astype(np.float32)-frames[0]).mean()))
        print('encoded',layer,flush=True)
        del projected
    previous=json.loads((OUT/'report.json').read_text()) if os.environ.get('BOSCH_RENDER_LAYER') and (OUT/'report.json').exists() else {}
    previous.update(metrics)
    (OUT/'report.json').write_text(json.dumps(previous,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(metrics,indent=2),flush=True)

if __name__=='__main__':main()
