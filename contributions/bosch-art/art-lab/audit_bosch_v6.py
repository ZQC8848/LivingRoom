"""Measure the specific visual regressions reported by the reviewer."""
from pathlib import Path
import json
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'orbis-test/delivery-v3'

def samples(path):
    cap=cv2.VideoCapture(str(path));frames=[]
    fps=cap.get(cv2.CAP_PROP_FPS)
    for t in np.linspace(.1,5.8,36):
        cap.set(cv2.CAP_PROP_POS_MSEC,float(t*1000));ok,frame=cap.read()
        if not ok:raise ValueError(f'Cannot decode {path} at {t}')
        frames.append(cv2.resize(frame,(1774,887),interpolation=cv2.INTER_AREA))
    cap.release()
    return np.array(frames,np.float32),fps

regions={
    'bird_surrounding_grass':('garden',(280,510,312,529)),
    'architecture_under_tree':('garden',(1095,306,1160,340)),
    'central_blue_architecture':('garden',(845,502,930,540)),
    'water_foreground':('garden',(944,606,1080,652)),
    'distant_flames':('hell',(1270,248,1395,292)),
}
report={'scope':'36 decoded samples per video; encoded working-space strips, resized to native artwork size. Compression can change fixed pixels slightly. These checks accompany visual review; they do not prove all perceptual quality.'}
for version,folder in [('before','delivery-v2'),('after','delivery-v3')]:
    data={}
    for layer in ('garden','hell'):
        data[layer],fps=samples(ROOT/'orbis-test'/folder/f'{layer}-source-motion.mp4')
        report.setdefault(version,{})[layer+'_fps']=fps
    for name,(layer,(x0,y0,x1,y1)) in regions.items():
        f=data[layer][:,y0:y1,x0:x1]
        report[version][name]={
            'mean_pixel_temporal_std':round(float(f.std(axis=0).mean()),4),
            'region_mean_brightness_range':round(float(np.ptp(f.mean(axis=(1,2,3)))),4),
        }
    del data
after=report['after'];before=report['before']
checks={
 'bird_background_exposure_reduced':after['bird_surrounding_grass']['region_mean_brightness_range']<min(1.5,before['bird_surrounding_grass']['region_mean_brightness_range']*.3),
 'architecture_under_tree_stable':after['architecture_under_tree']['mean_pixel_temporal_std']<1.0,
 'blue_architecture_stable':after['central_blue_architecture']['mean_pixel_temporal_std']<1.0,
 'river_has_visible_texture_variation':after['water_foreground']['mean_pixel_temporal_std']>1.3,
 'fire_is_active':after['distant_flames']['mean_pixel_temporal_std']>1.0,
 'thirty_fps':after['garden_fps']==30 and after['hell_fps']==30,
}
report['checks']=checks
(OUT/'regression-audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
if not all(checks.values()):raise SystemExit(1)
