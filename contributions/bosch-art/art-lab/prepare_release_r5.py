from pathlib import Path
import json,hashlib,shutil,subprocess,html
import cv2,imageio_ffmpeg
ROOT=Path(__file__).resolve().parent;SITE=ROOT.parent/'deployment/bosch-demo';PUB=SITE/'public';FF=imageio_ffmpeg.get_ffmpeg_exe()
MODE=PUB/'scenes/bosch-demo/modes';MODE.mkdir(exist_ok=True)
fast=ROOT.parent/'handoff/garden-daynight-20261114/fast-study'
specs=[]
for world,kind,label,short in [('garden','light','Garden · Day / Night','Garden: Day/Night'),('hell','light','Aftermath · Day / Night','Aftermath: Night'),('garden','season','Garden · Seasons','Garden: Seasons'),('hell','season','Aftermath · Seasons','Aftermath: Seasons')]:
 id=world+'-'+kind;target=MODE/(id+'.mp4');shutil.copy2(fast/(id+'-panorama.mp4'),target)
 c=cv2.VideoCapture(str(target));fps=c.get(cv2.CAP_PROP_FPS);n=c.get(cv2.CAP_PROP_FRAME_COUNT);w=c.get(cv2.CAP_PROP_FRAME_WIDTH);h=c.get(cv2.CAP_PROP_FRAME_HEIGHT);ok,im=c.read();c.release()
 if not ok:raise RuntimeError(id)
 cv2.imwrite(str(MODE/(id+'.jpg')),im,[cv2.IMWRITE_JPEG_QUALITY,92])
 specs.append({'id':id,'label':label,'shortLabel':short,'world':world,'packed':False,'file':id+'.mp4','bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'video':{'width':int(w),'height':int(h),'fps':fps,'frame_count':int(n),'duration_seconds':n/fps},'description':'6 seconds per light change · 12-second loop' if kind=='light' else 'Four seasons · 8-second loop'})
(MODE/'manifest.json').write_text(json.dumps({'release':'2026-11-14-r5','modes':specs,'method':'Authored fixed-viewpoint hybrid playback; r4 object motion retained. No live model calls in this public demo.'},indent=2),encoding='utf-8')
shutil.copy2(fast/'overview-19s.mp4',PUB/'review/overview-19s.mp4')
audio=PUB/'audio';script=json.loads((ROOT/'audio-v2/script.en.json').read_text(encoding='utf-8'))
def run(args):
 p=subprocess.run([FF,'-y','-v','error',*args],capture_output=True)
 if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace')[-500:])
for cue in script['narration']:
 file='r5-'+cue['id']+'.mp3';run(['-i',str(ROOT/'audio-v2'/(cue['id']+'.mp3')),'-af','loudnorm=I=-18:TP=-2:LRA=7','-ar','48000','-ac','2','-c:a','libmp3lame','-b:a','128k',str(audio/file)])
 raw=subprocess.run([FF,'-v','error','-i',str(audio/file),'-f','f32le','-ar','48000','-ac','2','pipe:1'],capture_output=True,check=True).stdout
 cue.update(file=file,seconds=len(raw)/(4*2*48000))
manifest=json.loads((audio/'manifest-r4.json').read_text(encoding='utf-8'));manifest.update(release='2026-11-14-r5',narration=script['narration'],voice={'name':'Lily — Velvety Actress','id':'pFZP5JQG7iQjIQuC4Bku','provider':'ElevenLabs stock voice','model':'eleven_multilingual_v2','settings':json.loads((ROOT/'audio-v2/generation.json').read_text())['settings']},research=script['research'],interpretive_boundary=script['interpretive_boundary'])
(audio/'manifest-r5.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');shutil.copy2(ROOT/'audio-v2/soundscape-r5.js',audio/'soundscape-r5.js')
content='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>The Garden of Consequences — Narration and Research</title><style>body{max-width:820px;margin:40px auto;padding:0 22px;font:18px/1.65 Georgia,serif;color:#26372e;background:#f8f5eb}h1,h2{font-family:system-ui}a{color:#355c44}audio{display:block;width:100%;margin:12px 0}</style><h1>The Garden of Consequences</h1><p>English narration · Lily, ElevenLabs stock voice. Original interpretive writing, not quotations from Bosch or Carroll.</p><p><a href="/">Open experience</a> · <a href="/guide/">Desktop and headset controls</a></p>'
for cue in script['narration']:
 content+='<h2>'+html.escape(cue['id'].replace('mode-','').replace('-',' ').title())+'</h2><p>'+html.escape(cue['text'])+'</p><audio controls preload="none" src="'+cue['file']+'"></audio>'
content+='<h2>Research and interpretation</h2>'
for source in script['research']:content+='<p><a href="'+source['url']+'">'+html.escape(source['title'])+'</a>: '+html.escape(source['scope'])+'</p>'
content+='<p>'+html.escape(script['interpretive_boundary'])+'</p></html>'; (audio/'transcript.en.html').write_text(content,encoding='utf-8')
(audio/'transcript.en.md').write_text('# The Garden of Consequences\n\n'+'\n\n'.join('## '+c['id']+'\n\n'+c['text'] for c in script['narration']),encoding='utf-8')
main=PUB/'scenes/bosch-demo/media/manifest.json';m=json.loads(main.read_text(encoding='utf-8'));m['release']='2026-11-14-r5';m['optional_modes_manifest']='../modes/manifest.json';m['audio'].update(manifest='/audio/manifest-r5.json',narration='Eight mode-aware English cues; Lily stock voice; research integrated into narration');main.write_text(json.dumps(m,indent=2),encoding='utf-8')
print(json.dumps({'modes':[{k:s[k] for k in ('id','bytes')} for s in specs],'voice':'Lily','cues':[{k:c[k] for k in ('id','seconds')} for c in script['narration']]}))
