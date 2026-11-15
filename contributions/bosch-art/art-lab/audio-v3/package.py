from pathlib import Path
import json,subprocess,hashlib,html,shutil
import imageio_ffmpeg,numpy as np
ROOT=Path(__file__).resolve().parent;PUB=ROOT.parent.parent/'deployment/bosch-demo/public';AUDIO=PUB/'audio';FF=imageio_ffmpeg.get_ffmpeg_exe()
script=json.loads((ROOT/'script.en.json').read_text(encoding='utf-8'));manifest=json.loads((AUDIO/'manifest-r5.json').read_text(encoding='utf-8'))
def run(args):
 p=subprocess.run([FF,'-y','-v','error',*args],capture_output=True)
 if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace')[-500:])
 return p.stdout
assets={k:v for k,v in manifest['audio_assets'].items()if k in ('music','garden-ambience','hell-ambience')}
for cue in script['narration']:
 name='r7-'+cue['id']+'.mp3';target=AUDIO/name
 run(['-i',str(ROOT/(cue['id']+'.mp3')),'-af','loudnorm=I=-18:TP=-2:LRA=7','-ar','48000','-ac','2','-c:a','libmp3lame','-b:a','128k',str(target)])
 pcm=np.frombuffer(run(['-i',str(target),'-f','f32le','-ar','48000','-ac','2','pipe:1']),dtype=np.float32)
 duration=len(pcm)/96000;cue.update(file=name,seconds=duration)
 assets[cue['id']]={'seconds':duration,'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'peak_dbfs':float(20*np.log10(max(np.abs(pcm).max(),1e-8))),'decoded_all_finite':bool(np.isfinite(pcm).all()),'target_lufs':-18}
manifest.update(release='2026-11-14-r7',narration=script['narration'],audio_assets=assets,interpretive_boundary=script['interpretive_boundary'])
work={'artist':'Hieronymus Bosch','artist_dates':'c.1450–1516','title':'The Garden of Earthly Delights','date_display':'c.1500','date_range':'1490–1500 (Prado/CODART)','period':'Early Netherlandish painting / Northern Renaissance','medium':'Oil on oak panels, triptych','current_location':'Museo Nacional del Prado, Madrid, Spain','panels':['Eden','Earthly pleasure','Hell'],'adaptation':'Aligned panoramic layers, gesture reveal and optional controlled generative environments; not an exact scan of the original panels.'}
manifest['source_work']=work
(AUDIO/'manifest-r7.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
sound=(AUDIO/'soundscape-r5.js').read_text(encoding='utf-8').replace('manifest-r5.json','manifest-r7.json');(AUDIO/'soundscape-r7.js').write_text(sound,encoding='utf-8')
text='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bosch — English Audio Guide</title><style>body{max-width:820px;margin:40px auto;padding:0 22px;font:18px/1.65 Georgia,serif;color:#26372e;background:#f8f5eb}h1,h2{font-family:system-ui}a{color:#355c44}audio{display:block;width:100%;margin:12px 0}.label{font:14px/1.6 system-ui}</style><h1>Inside Bosch’s Garden</h1><p><strong>After Hieronymus Bosch, The Garden of Earthly Delights, c.1500.</strong><br>Early Netherlandish painting / Northern Renaissance. Original: Prado Museum, Madrid.</p><p>Our adaptation makes the relationship between the original’s garden and Hell something you reveal with your hand. The full <a href="/guide/artwork.html">project brief</a> separates artwork context, interaction and bounded generation.</p><p class="label">English narration · Lily, ElevenLabs stock voice. Text below is our guide, not a quotation from Bosch or a museum.</p><p><a href="/">Open experience</a> · <a href="/guide/">Controls</a></p>'
for cue in script['narration']:text+='<h2>'+html.escape(cue['id'].replace('mode-','').replace('-',' ').title())+'</h2><p>'+html.escape(cue['text'])+'</p><audio controls preload="none" src="'+cue['file']+'"></audio>'
text+='<details><summary>Sources and adaptation credits</summary><p>'+html.escape(script['interpretive_boundary'])+'</p>'
for url,label in [('https://canon.codart.nl/artwork/garden-of-earthly-delights/','CODART / Prado object record'),('https://www.afpradomuseum.org/the-garden-of-earthly-delights-bosch/history','Prado picture history'),('https://www.nationalgallery.org.uk/artists/hieronymus-bosch','National Gallery artist biography'),('https://yalebooks.yale.edu/2022/08/09/time-and-transformation-hieronymus-boschs-process/','Margaret D. Carroll on time and transformation')]:text+='<p><a href="'+url+'">'+label+'</a></p>'
text+='</details></html>'
(AUDIO/'transcript.en.html').write_text(text,encoding='utf-8');(AUDIO/'transcript.en.md').write_text('# Inside Bosch’s Garden\n\nAfter Hieronymus Bosch, The Garden of Earthly Delights, c.1500. Original: Prado Museum, Madrid.\n\n'+'\n\n'.join('## '+c['id']+'\n\n'+c['text'] for c in script['narration']),encoding='utf-8')
main=PUB/'scenes/bosch-demo/media/manifest.json';m=json.loads(main.read_text(encoding='utf-8'));m['source_work']=work;m['release']='2026-11-14-r7';m['audio'].update(manifest='/audio/manifest-r7.json',narration='Eight brief English cues, beginning with Bosch and the original artwork, followed by the interaction');main.write_text(json.dumps(m,indent=2,ensure_ascii=False),encoding='utf-8')
for file in [PUB.parent/'src/demo.js',PUB/'review/index.html']:
 s=file.read_text(encoding='utf-8').replace('soundscape-r5.js','soundscape-r7.js');file.write_text(s,encoding='utf-8')
run(['-i',str(PUB/'review/overview-19s-r5.mp4'),'-i',str(AUDIO/'r7-arrival.mp3'),'-i',str(AUDIO/'music.mp3'),'-filter_complex','[1:a]apad=whole_dur=19[v];[2:a]atrim=duration=19,volume=0.22,afade=t=out:st=18:d=1[m];[v][m]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.89[a]','-map','0:v','-map','[a]','-c:v','copy','-c:a','aac','-b:a','160k','-t','19',str(PUB/'review/overview-19s-r7.mp4')])
p=PUB/'guide/index.html';s=p.read_text(encoding='utf-8').replace('overview-19s-r5.mp4','overview-19s-r7.mp4');p.write_text(s,encoding='utf-8')
print(json.dumps({'release':'r7','cues':[{k:c[k]for k in ('id','seconds')}for c in script['narration']]},indent=2))
