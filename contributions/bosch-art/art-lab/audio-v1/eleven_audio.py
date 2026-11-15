"""Read a user-authorized key into process memory; never save it or client headers."""
from pathlib import Path
import argparse,getpass,json,urllib.request,urllib.error
ROOT=Path(__file__).resolve().parent;ROOT.mkdir(exist_ok=True)
NARRATION=[
 {'id':'arrival','trigger':'sound enabled, once per visit','text':'A garden offers everything. Clear water. Ripe fruit. Life without end. Look closely. Nothing here seems to ask a price.'},
 {'id':'reveal','trigger':'first reveal, after arrival speech ends','text':'Is this another world, or the cost of this one?'},
 {'id':'return','trigger':'first return after reveal speech, once per visit','text':'Gone from sight is not the same as gone.'},
]
SFX=[
 {'id':'garden-ambience','text':'Quiet continuous natural soundscape for a tranquil painted garden. Delicate close fountain water trickling and falling into a small pond, gentle ripples, light leaf rustle in a soft breeze, a few tiny distant bird calls far apart. Airy open space, very calm, clean and intimate. No music, no voices, no footsteps, no sudden foreground bird squawks, no ocean waves. Seamless continuous ambience loop.'},
 {'id':'hell-ambience','text':'Continuous environmental sound of distant small fires and dry embers in an empty ruined landscape. Soft detailed wood crackles, slow low airy wind moving through hollow stone, a very quiet deep organic rumble. Restrained and mournful, not a horror jump scare. No music, no voices, no screams, no explosions, no rhythmic beat, no sudden loud transients. Seamless continuous ambience loop.'},
]
ap=argparse.ArgumentParser();ap.add_argument('--generate',action='store_true');args=ap.parse_args()
key=getpass.getpass('ElevenLabs API key (hidden): ')
def request(path,payload=None):
 body=None if payload is None else json.dumps(payload).encode()
 req=urllib.request.Request('https://api.elevenlabs.io'+path,data=body,headers={'xi-api-key':key,'Content-Type':'application/json','Accept':'application/json' if payload is None else 'audio/mpeg'},method='GET' if payload is None else 'POST')
 try:
  with urllib.request.urlopen(req,timeout=90) as r:return r.read(),dict(r.headers)
 except urllib.error.HTTPError as e:
  message=e.read().decode(errors='replace').replace(key,'[REDACTED]')
  raise RuntimeError(f'ElevenLabs HTTP {e.code}: {message[:650]}') from None
try:
 raw,_=request('/v2/voices?page_size=100');voices=json.loads(raw)['voices']
 choices=[v for v in voices if v.get('category') in ('premade','default')]
 voice=next((v for name in ['Rachel','George','Alice','Brian'] for v in choices if v.get('name','').split(' - ')[0]==name),None)
 if voice is None:voice=next((v for v in choices if v.get('labels',{}).get('use_case') in ('narration','narrative_story')),choices[0] if choices else None)
 if voice is None:raise RuntimeError('No default stock narration voice available. No private voice clone will be used.')
 info={'authenticated':True,'voice_id':voice['voice_id'],'voice_name':voice['name'],'voice_category':voice['category'],'speech_model':'eleven_multilingual_v2','language':'en','narration_characters':sum(len(n['text']) for n in NARRATION),'sfx_seconds':24}
 (ROOT/'voice-selection.json').write_text(json.dumps(info,indent=2),encoding='utf-8');print(json.dumps(info),flush=True)
 if args.generate:
  made=[]
  for n in NARRATION:
   file=ROOT/(n['id']+'.mp3')
   if not file.exists():
    data,headers=request('/v1/text-to-speech/'+voice['voice_id']+'?output_format=mp3_44100_128',{'text':n['text'],'model_id':'eleven_multilingual_v2','voice_settings':{'stability':.73,'similarity_boost':.78,'style':.06,'use_speaker_boost':False,'speed':.88}})
    file.write_bytes(data)
   made.append({'id':n['id'],'file':file.name,'bytes':file.stat().st_size,'provider':'ElevenLabs','voice':voice['name'],'text':n['text'],'trigger':n['trigger']});print('Created speech',n['id'],file.stat().st_size,flush=True)
  for s in SFX:
   file=ROOT/(s['id']+'.mp3')
   if not file.exists():
    data,headers=request('/v1/sound-generation?output_format=mp3_44100_128',{'text':s['text'],'duration_seconds':12,'loop':True,'prompt_influence':.5,'model_id':'eleven_text_to_sound_v3'})
    file.write_bytes(data)
   made.append({'id':s['id'],'file':file.name,'bytes':file.stat().st_size,'provider':'ElevenLabs','model':'eleven_text_to_sound_v3','loop_requested':True,'prompt':s['text']});print('Created ambience',s['id'],file.stat().st_size,flush=True)
  (ROOT/'generation-report.json').write_text(json.dumps({'files':made,'key_saved':False},indent=2),encoding='utf-8')
  transcript='# The Garden of Consequences\n\nEnglish narration. Original writing for an interpretive artwork inspired by Bosch; not a historical claim about the original painting.\n\n'+'\n\n'.join('## '+n['id'].title()+'\n\n'+n['text'] for n in NARRATION)+'\n'
  (ROOT/'transcript.en.md').write_text(transcript,encoding='utf-8')
except Exception as e:
 print(str(e).replace(key,'[REDACTED]'),flush=True);raise SystemExit(2)
