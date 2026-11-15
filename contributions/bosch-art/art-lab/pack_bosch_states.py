"""Pack two 2:1 states into one video clock; keep each state a full panorama.

Run after package_bosch_demo.py. Masters are preserved. The upper half is heaven,
the lower half hell. The viewer samples the appropriate half by spherical mask.
"""
from pathlib import Path
import hashlib,json,shutil,subprocess,zipfile
import cv2
import imageio_ffmpeg

root=Path(__file__).resolve().parent.parent/'handoff/bosch-demo-20261114'
source=root/'media';release=root/'r2';media=release/'media'
media.mkdir(parents=True,exist_ok=True)
for file in source.iterdir():
    if file.is_file():shutil.copy2(file,media/file.name)
target=media/'paired.mp4'
cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-i',str(media/'heaven.mp4'),'-i',str(media/'hell.mp4'),
 '-filter_complex','[0:v]setpts=PTS-STARTPTS[a];[1:v]setpts=PTS-STARTPTS[b];[a][b]vstack=inputs=2[v]',
 '-map','[v]','-an','-r','30','-frames:v','240','-c:v','libx264','-preset','fast','-crf','20',
 '-profile:v','high','-level:v','5.1','-pix_fmt','yuv420p','-g','60','-keyint_min','60','-sc_threshold','0',
 '-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-color_range','tv',
 '-movflags','+faststart',str(target)]
p=subprocess.run(cmd,capture_output=True)
if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace')[-1500:])
cap=cv2.VideoCapture(str(target))
actual=[cap.get(k) for k in (cv2.CAP_PROP_FRAME_WIDTH,cv2.CAP_PROP_FRAME_HEIGHT,cv2.CAP_PROP_FPS,cv2.CAP_PROP_FRAME_COUNT)]
cap.release()
if actual!=[2048,2048,30,240]:raise ValueError(actual)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((media/'manifest.json').read_text(encoding='utf-8'))
m['release']='2026-11-14-r2'
m['media'].update(packed='paired.mp4',packedLayout='heaven-top-hell-bottom')
m['packed_video']={**m['video'],'height':2048,'aspect_ratio':'1:1 packed container; each plane remains 2:1',
 'level':'5.1','rows':2,'columns':1,'order':['heaven','hell'],'pane_width':2048,'pane_height':1024,
 'decoder_count':1,'shared_clock':True}
m['files']['paired.mp4']={'bytes':target.stat().st_size,'sha256':sha(target)}
(media/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
archive=release/'bosch-demo-media.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for file in sorted(media.iterdir()):z.write(file,'media/'+file.name)
result={'archive':str(archive),'sha256':sha(archive),'bytes':archive.stat().st_size,'packed':m['files']['paired.mp4']}
(release/'release.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
