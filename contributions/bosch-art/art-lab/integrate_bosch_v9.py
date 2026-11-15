from pathlib import Path
import hashlib,json,shutil,subprocess,zipfile
import imageio_ffmpeg
ROOT=Path(__file__).resolve().parent;SITE=ROOT.parent/'deployment/bosch-demo'
release=ROOT.parent/'handoff/bosch-demo-20261114/r4';record=json.loads((release/'release.json').read_text())
for f in (release/'media').iterdir():shutil.copy2(f,SITE/'public/scenes/bosch-demo/media'/f.name)
audio=SITE/'public/audio';audio.mkdir(exist_ok=True)
shutil.copy2(ROOT/'audio-v1/soundscape-r4.js',ROOT/'audio-v1/delivery/soundscape-r4.js')
for f in (ROOT/'audio-v1/delivery').iterdir():shutil.copy2(f,audio/f.name)
review=SITE/'public/review';review.mkdir(exist_ok=True)
shutil.copy2(ROOT/'motion-v9/review.html',review/'index.html');shutil.copy2(release/'media/motion-catalog.json',review/'motion-catalog.json')
source=ROOT/'orbis-test/delivery-v6'
cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-i',str(source/'garden-source-motion.mp4'),'-i',str(source/'hell-source-motion.mp4'),'-filter_complex','[0:v]scale=in_color_matrix=bt601:out_color_matrix=bt709:in_range=tv:out_range=tv,setpts=PTS-STARTPTS[a];[1:v]scale=in_color_matrix=bt601:out_color_matrix=bt709:in_range=tv:out_range=tv,setpts=PTS-STARTPTS[b];[a][b]vstack=inputs=2[v]','-map','[v]','-an','-r','30','-frames:v','240','-c:v','libx264','-preset','fast','-crf','19','-profile:v','high','-level:v','5.1','-pix_fmt','yuv420p','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-color_range','tv','-movflags','+faststart',str(review/'review.mp4')]
p=subprocess.run(cmd,capture_output=True)
if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace')[-1300:])
# Final media handoff includes the exact sound client/transcript that is shipped.
with zipfile.ZipFile(release/'bosch-demo-media.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in sorted((release/'media').iterdir()):z.write(f,'media/'+f.name)
 for f in sorted((ROOT/'audio-v1/delivery').iterdir()):z.write(f,'audio/'+f.name)
archive=release/'bosch-demo-media.zip';record.update(sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),bytes=archive.stat().st_size)
(release/'release.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
downloads=SITE/'public/downloads';downloads.mkdir(exist_ok=True);shutil.copy2(archive,downloads/'bosch-demo-r4.zip')
prov=json.loads((SITE/'SOURCE_PROVENANCE.json').read_text());prov.update(media_release=record['release'],media_zip_sha256=record['sha256'])
prov['animation_review']='r4 user-requested complete object silhouettes; G03 intentionally static; G20 opens wing; stronger downward water and rising fire/smoke; camera and packed single-decoder reveal retained.'
prov['audio']='One Suno user-exported music source with bright/dark filter branches, ElevenLabs English stock-voice narration, authored environmental synthesis. Explicit opt-in, once-per-visit voice cues, static local files only. No keys in browser.'
(SITE/'SOURCE_PROVENANCE.json').write_text(json.dumps(prov,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(record,indent=2));print('r4 media, English review and static sound layers integrated.')
