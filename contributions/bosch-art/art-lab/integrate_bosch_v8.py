from pathlib import Path
import json,shutil,subprocess
import imageio_ffmpeg
ROOT=Path(__file__).resolve().parent;SITE=ROOT.parent/'deployment/bosch-demo'
release=ROOT.parent/'handoff/bosch-demo-20261114/r3';record=json.loads((release/'release.json').read_text())
for f in (release/'media').iterdir():shutil.copy2(f,SITE/'public/scenes/bosch-demo/media'/f.name)
review=SITE/'public/review';review.mkdir(exist_ok=True)
shutil.copy2(ROOT/'motion-v8/review.html',review/'index.html')
shutil.copy2(release/'media/motion-catalog.json',review/'motion-catalog.json')
source=ROOT/'orbis-test/delivery-v5'
cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-i',str(source/'garden-source-motion.mp4'),'-i',str(source/'hell-source-motion.mp4'),
     '-filter_complex','[0:v]scale=in_color_matrix=bt601:out_color_matrix=bt709:in_range=tv:out_range=tv,setpts=PTS-STARTPTS[a];[1:v]scale=in_color_matrix=bt601:out_color_matrix=bt709:in_range=tv:out_range=tv,setpts=PTS-STARTPTS[b];[a][b]vstack=inputs=2[v]',
     '-map','[v]','-an','-r','30','-frames:v','240','-c:v','libx264','-preset','fast','-crf','19','-profile:v','high','-level:v','5.1','-pix_fmt','yuv420p',
     '-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-color_range','tv','-movflags','+faststart',str(review/'review.mp4')]
p=subprocess.run(cmd,capture_output=True)
if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace')[-1300:])
downloads=SITE/'public/downloads';downloads.mkdir(exist_ok=True);shutil.copy2(release/'bosch-demo-media.zip',downloads/'bosch-demo-r3.zip')
prov=json.loads((SITE/'SOURCE_PROVENANCE.json').read_text())
prov.update(media_release=record['release'],media_zip_sha256=record['sha256'])
prov['animation_review']='51 annotated regions; eight local Orbis captures; four bounded original-paint motion fields retained; new generated RGB discarded for exposure drift. Original fixed camera and packed single-decoder reveal pipeline retained.'
(SITE/'SOURCE_PROVENANCE.json').write_text(json.dumps(prov,ensure_ascii=False,indent=2),encoding='utf-8')
print('Integrated r3 media and separate flat-painting review page. Existing reveal/player code unchanged.')
