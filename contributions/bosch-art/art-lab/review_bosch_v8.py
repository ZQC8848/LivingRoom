"""Evidence for the rendered loop: marked-region coverage, stable paint, seam."""
from pathlib import Path
import json,cv2,numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'motion-v8';SOURCE=ROOT/'orbis-test/delivery-v5'
catalog=json.loads((OUT/'motion-catalog.json').read_text())['items']
frames={};report={'headset_verified':False,'regions':[],'stable_controls':{}}
for layer in ['garden','hell']:
    cap=cv2.VideoCapture(str(SOURCE/f'{layer}-source-motion.mp4'));fs=[]
    for n in range(0,240,12):
        cap.set(cv2.CAP_PROP_POS_FRAMES,n);ok,f=cap.read()
        if not ok:raise ValueError((layer,n))
        fs.append(cv2.resize(cv2.cvtColor(f,cv2.COLOR_BGR2RGB),(1774,887)))
    frames[layer]=np.array(fs,np.float32);cap.release()
for it in catalog:
    x0,y0,x1,y1=it['box'];patch=frames[it['layer']][:,y0:y1,x0:x1]
    std=np.std(patch,axis=0).max(axis=-1)
    report['regions'].append({'id':it['id'],'layer':it['layer'],'pixels_with_temporal_std_above_2':int((std>2).sum()),'mean_temporal_std':float(std.mean()),'note':'Temporal difference is a coverage diagnostic, not a claim of human-approved gesture quality.'})
for name,layer,box in [('pink-shell','garden',(1089,320,1142,377)),('blue-fountain','garden',(855,438,900,475)),('hell-left-building','hell',(261,409,297,448)),('hell-skyline','hell',(1304,295,1330,309))]:
    x0,y0,x1,y1=box;p=frames[layer][:,y0:y1,x0:x1]
    report['stable_controls'][name]={'mean_rgb_temporal_std':float(p.std(axis=0).mean()),'mean_frame_exposure_std':float(p.mean(axis=(1,2)).std(axis=0).mean())}
ids=['G01','G02','G07','G08','G11','G13','G14','G16','G19','G20','G21','G22','G23','G25','G27','G29','H01','H03','H04','H05','H07','H11','H12']
sheet=Image.new('RGB',(4*330,len(ids)*190),(18,22,20));draw=ImageDraw.Draw(sheet)
for row,id in enumerate(ids):
    it=next(i for i in catalog if i['id']==id);x0,y0,x1,y1=it['box'];pad=10
    for col,index in enumerate([0,5,10,15]):
        im=Image.fromarray(np.uint8(frames[it['layer']][index])).crop((max(0,x0-pad),max(0,y0-pad),min(1774,x1+pad),min(887,y1+pad)))
        im.thumbnail((322,160));sheet.paste(im,(col*330,row*190+28));draw.text((col*330+4,row*190+7),f'{id} {index*.4:.1f}s',fill='white')
sheet.save(OUT/'expanded-motion-contact.jpg',quality=95)
(OUT/'render-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'regions':len(report['regions']),'regions_without_measurable_motion':[r['id'] for r in report['regions'] if r['pixels_with_temporal_std_above_2']<3],'stable_controls':report['stable_controls']},indent=2))
