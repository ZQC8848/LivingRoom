"""Immutable r3 masters, single-clock packed video, posters and motion catalog."""
from pathlib import Path
import hashlib,json,subprocess,zipfile,shutil
import cv2,imageio_ffmpeg

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'orbis-test/delivery-v5'
TARGET=ROOT.parent/'handoff/bosch-demo-20261114/r3';MEDIA=TARGET/'media';MEDIA.mkdir(parents=True,exist_ok=True)
ff=imageio_ffmpeg.get_ffmpeg_exe()
def run(args):
    p=subprocess.run([ff,'-y',*args],capture_output=True)
    if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace')[-1600:])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for layer,name,poster in [('garden','heaven','poster'),('hell','hell','hell-poster')]:
    run(['-i',str(SOURCE/f'{layer}-equirect-2048.mp4'),'-an','-vf','scale=in_color_matrix=bt601:out_color_matrix=bt709:in_range=tv:out_range=tv',
         '-c:v','libx264','-preset','fast','-crf','19','-profile:v','high','-level:v','4.0','-g','60','-keyint_min','60','-sc_threshold','0','-pix_fmt','yuv420p',
         '-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-color_range','tv','-movflags','+faststart',str(MEDIA/f'{name}.mp4')])
    run(['-i',str(MEDIA/f'{name}.mp4'),'-frames:v','1','-q:v','2',str(MEDIA/f'{poster}.jpg')])
    print('Master',name,flush=True)
run(['-i',str(MEDIA/'heaven.mp4'),'-i',str(MEDIA/'hell.mp4'),'-filter_complex','[0:v]setpts=PTS-STARTPTS[a];[1:v]setpts=PTS-STARTPTS[b];[a][b]vstack=inputs=2[v]',
     '-map','[v]','-an','-r','30','-frames:v','240','-c:v','libx264','-preset','fast','-crf','20','-profile:v','high','-level:v','5.1','-pix_fmt','yuv420p',
     '-g','60','-keyint_min','60','-sc_threshold','0','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-color_range','tv','-movflags','+faststart',str(MEDIA/'paired.mp4')])
for name,dims in [('heaven',(2048,1024)),('hell',(2048,1024)),('paired',(2048,2048))]:
    cap=cv2.VideoCapture(str(MEDIA/f'{name}.mp4'));actual=[cap.get(k) for k in (cv2.CAP_PROP_FRAME_WIDTH,cv2.CAP_PROP_FRAME_HEIGHT,cv2.CAP_PROP_FPS,cv2.CAP_PROP_FRAME_COUNT)];cap.release()
    if actual!=[*dims,30,240]:raise ValueError((name,actual))
m=json.loads((TARGET.parent/'r2/media/manifest.json').read_text(encoding='utf-8'))
m['release']='2026-11-14-r3'
review=json.loads((ROOT/'motion-v8/generation-review.json').read_text())
catalog=json.loads((ROOT/'motion-v8/motion-catalog.json').read_text())
for it in catalog['items']:
    if it.get('job'):
        used=next((r['flow_accepted'] for r in review if r['job']==it['job']),False)
        it['delivered_method']='original-paint cutout articulation'+(' plus registered bounded Orbis motion field' if used else '')
    else:it['delivered_method']=it['method']
    it['status']='included in r3 review loop'
(MEDIA/'motion-catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
m['production'].update(new_model_calls=len(review),new_generated_rgb_layers_accepted=0,new_generated_flow_layers_accepted=[r['job'] for r in review if r['flow_accepted']],marked_regions=51,motion_catalog='motion-catalog.json',method='Original-paint RGBA articulation and bounded registered model motion fields. Generated RGB rejected for exposure drift. Retained prior Orbis foreground bird and keyed fire. Controlled foliage, waterfalls, whole-river ripples, float/flight, fire/smoke. No environment-tile warp.',headset_verified=False)
m['loop']['method']='8-second authored periodic motion; eased forward/reverse generated motion fields and retained bird/fire source clips; model-native seamless looping is not claimed'
m['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(MEDIA.iterdir()) if p.name!='manifest.json'}
(MEDIA/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
archive=TARGET/'bosch-demo-media.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(MEDIA.iterdir()):z.write(p,'media/'+p.name)
result={'release':m['release'],'archive':str(archive),'sha256':sha(archive),'bytes':archive.stat().st_size,'packed':m['files']['paired.mp4']}
(TARGET/'release.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2),flush=True)
