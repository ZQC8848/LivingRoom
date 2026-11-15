"""Keep bounded generated motion fields, discard changing generated RGB."""
from pathlib import Path
import json,cv2,numpy as np
from PIL import Image,ImageDraw
from analyze_orbis_painting import registration
from bosch_marked_motion import Cutout,CAT,ROOT,OUT

GEN=OUT/'generation';jobs=json.loads((GEN/'jobs.json').read_text(encoding='utf-8'))
report=[];sheet=Image.new('RGB',(1280,len(jobs)*210),(18,23,20));draw=ImageDraw.Draw(sheet)
for row,job in enumerate(jobs):
    folder=GEN/job['id'];paths=sorted((folder/'run-v8/frames').glob('*.jpg'))
    if len(paths)<20:continue
    ref=np.asarray(Image.open(folder/'reference.png').convert('RGB'))
    context=np.asarray(Image.open(folder/'context-mask.png'))
    x0,y0,x1,y1=job['crop'];cw,ch=x1-x0,y1-y0
    it=next(i for i in CAT if i.get('job')==job['id'])
    base=np.asarray(Image.open(ROOT/'bosch-world-assets'/f'{it["layer"]}-generated.png').convert('RGB'))
    obj=Cutout(base,it);a,b,c,d=obj.box
    refsmall=cv2.resize(ref,(cw,ch));gray=cv2.cvtColor(refsmall,cv2.COLOR_RGB2GRAY)
    static=(context==0).astype(np.uint8)*255
    fields=[];errors=[];last=np.array([[1.,0,0],[0,1.,0]])
    indices=np.linspace(2,len(paths)-1,min(36,len(paths)-2)).astype(int)
    selected=[]
    for ix in indices:
        f=np.asarray(Image.open(paths[ix]).convert('RGB'))
        mat,metric=registration(ref,f,static)
        if mat is not None:last=mat
        f=cv2.warpAffine(f,last,(1024,576),borderMode=cv2.BORDER_REFLECT_101)
        fs=cv2.resize(f,(cw,ch)).astype(np.float32)
        # Robust per-channel static-context color fit before measuring motion.
        support=cv2.resize(static,(cw,ch),interpolation=cv2.INTER_NEAREST)>0
        corrected=fs.copy()
        for channel in range(3):
            v=fs[...,channel][support];target=refsmall[...,channel][support]
            gain=np.clip(np.std(target)/(np.std(v)+1e-5),.65,1.5)
            corrected[...,channel]=gain*fs[...,channel]+np.median(target-gain*v)
        corrected=np.uint8(np.clip(corrected,0,255))
        g=cv2.cvtColor(corrected,cv2.COLOR_RGB2GRAY)
        flow=cv2.calcOpticalFlowFarneback(gray,g,None,.5,3,19,3,5,1.2,0)
        field=flow[b-y0:d-y0,a-x0:c-x0]
        fields.append(cv2.GaussianBlur(field,(0,0),2.2));selected.append(corrected)
        errors.append(float(np.abs(corrected.astype(float)-refsmall)[support].mean()))
    fields=np.array(fields,np.float32)
    # Remove fixed reconstruction differences; retain smooth temporal motion.
    fields-=fields[0].copy()
    weights=np.array([1,2,3,4,3,2,1],np.float32)/16
    padded=np.pad(fields,((3,3),(0,0),(0,0),(0,0)),mode='edge')
    fields=sum(w*padded[i:i+len(fields)] for i,w in enumerate(weights))
    fields-=fields[0].copy()
    fields*=2.0
    length=np.maximum(1,np.linalg.norm(fields,axis=-1)/2.5);fields/=length[...,None]
    fields*=obj.alpha[None,...,None]
    magnitude=float(np.mean(np.linalg.norm(fields,axis=-1)[:,obj.alpha>.4])) if (obj.alpha>.4).any() else 0
    accepted=job['id'] in ['bathers','herd','stag','bank-bird'] and np.median(errors)<22 and magnitude>.035
    if accepted:np.savez_compressed(folder/'accepted-flow.npz',flow=fields,box=np.array(obj.box))
    result=dict(job=job['id'],recorded_frames=len(paths),generated_rgb_accepted=False,flow_accepted=bool(accepted),mean_object_displacement_pixels=magnitude,static_context_color_fit_MAE=float(np.median(errors)),method='registered, exposure-normalized, temporally smoothed Orbis flow applied only to original object RGBA; <=2.5 native pixels; source wing/leg articulation supplements motion',reason='Generated RGB changes exposure and does not provide a reliable isolated wingbeat. No generated rectangular background is composited.')
    report.append(result)
    crops=[refsmall,selected[0],selected[len(selected)//2],selected[-1]]
    for col,ar in enumerate(crops):
        im=Image.fromarray(ar);im.thumbnail((315,177));sheet.paste(im,(col*320,row*210+27))
    draw.text((5,row*210+7),job['id']+' / generated RGB rejected; flow '+('retained' if accepted else 'rejected'),fill='white')
    print(json.dumps(result),flush=True)
sheet.save(OUT/'generated-pose-review.jpg',quality=94)
(OUT/'generation-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
