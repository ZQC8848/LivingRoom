"""Immutable r4 visual correction; compatible with the single packed decoder."""
from pathlib import Path
import hashlib,json,subprocess,zipfile
import cv2,imageio_ffmpeg
ROOT=Path(__file__).resolve().parent;SOURCE=ROOT/'orbis-test/delivery-v6'
TARGET=ROOT.parent/'handoff/bosch-demo-20261114/r4';MEDIA=TARGET/'media';MEDIA.mkdir(parents=True,exist_ok=True)
ff=imageio_ffmpeg.get_ffmpeg_exe()
def run(args):
 p=subprocess.run([ff,'-y',*args],capture_output=True)
 if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace')[-1500:])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for layer,name,poster in [('garden','heaven','poster'),('hell','hell','hell-poster')]:
 run(['-i',str(SOURCE/f'{layer}-equirect-2048.mp4'),'-an','-vf','scale=in_color_matrix=bt601:out_color_matrix=bt709:in_range=tv:out_range=tv','-c:v','libx264','-preset','fast','-crf','19','-profile:v','high','-level:v','4.0','-g','60','-keyint_min','60','-sc_threshold','0','-pix_fmt','yuv420p','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-color_range','tv','-movflags','+faststart',str(MEDIA/f'{name}.mp4')])
 run(['-i',str(MEDIA/f'{name}.mp4'),'-frames:v','1','-q:v','2',str(MEDIA/f'{poster}.jpg')])
run(['-i',str(MEDIA/'heaven.mp4'),'-i',str(MEDIA/'hell.mp4'),'-filter_complex','[0:v]setpts=PTS-STARTPTS[a];[1:v]setpts=PTS-STARTPTS[b];[a][b]vstack=inputs=2[v]','-map','[v]','-an','-r','30','-frames:v','240','-c:v','libx264','-preset','fast','-crf','20','-profile:v','high','-level:v','5.1','-pix_fmt','yuv420p','-g','60','-keyint_min','60','-sc_threshold','0','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-color_range','tv','-movflags','+faststart',str(MEDIA/'paired.mp4')])
cap=cv2.VideoCapture(str(MEDIA/'paired.mp4'));actual=[cap.get(k) for k in [cv2.CAP_PROP_FRAME_WIDTH,cv2.CAP_PROP_FRAME_HEIGHT,cv2.CAP_PROP_FPS,cv2.CAP_PROP_FRAME_COUNT]];cap.release()
if actual!=[2048,2048,30,240]:raise ValueError(actual)
m=json.loads((TARGET.parent/'r3/media/manifest.json').read_text(encoding='utf-8'))
m.update(release='2026-11-14-r4',title='The Garden of Consequences',subtitle='A garden. A gesture. A consequence.')
catalog=json.loads((ROOT/'motion-v9/motion-catalog.json').read_text())
for it in catalog['items']:
 it['status']='intentionally static at user request' if it['id']=='G03' else 'included in r4 review loop'
 if it['id'] in ['G01','G02','G04','G06','G07','G14','G20','H01','H02','H03']:it['delivered_method']='Complete original-paint polygon/card; coherent articulation; safe background margin'
(MEDIA/'motion-catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
m['production'].update(new_model_calls=0,prior_model_captures_reused=8,new_generated_rgb_layers_accepted=0,new_generated_flow_layers_accepted=[],prior_model_flow_layers_used=['herd','stag','bathers'],intentionally_static=['G03'],method='User-reviewed complete silhouettes; joined wing articulation; downward water/droplets; stronger rising flames, smoke and roof pipe smoke. Fixed camera. No environment warp.',headset_verified=False)
m['audio']={'manifest':'/audio/manifest-r4.json','opt_in':True,'language':'en','separate_from_visual_loop':True,'one_music_clock':True,'music':'Suno user export','narration':'ElevenLabs stock voice','environmental_beds':'Authored procedural synthesis; unexported Suno SFX are not shipped'}
m['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(MEDIA.iterdir()) if p.name!='manifest.json'}
(MEDIA/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
archive=TARGET/'bosch-demo-media.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(MEDIA.iterdir()):z.write(p,'media/'+p.name)
 for p in sorted((ROOT/'audio-v1/delivery').iterdir()):z.write(p,'audio/'+p.name)
result={'release':m['release'],'archive':str(archive),'sha256':sha(archive),'bytes':archive.stat().st_size,'packed':m['files']['paired.mp4']}
(TARGET/'release.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
