"""English review VO. Credential goes through hidden stdin, never saved."""
from pathlib import Path
import getpass,json,urllib.request,urllib.error
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'narration';OUT.mkdir(exist_ok=True)
LINES=[
 {'id':'day','start_seconds':0,'text':'Everything seems to be in bloom. As though this moment could last forever.'},
 {'id':'dusk','start_seconds':9,'text':'Let the light fade. Look at what remains.'},
 {'id':'night','start_seconds':18,'text':"Night is not the garden's punishment. Even abundance needs a pause."}
]
(OUT/'script.en.json').write_text(json.dumps({'language':'en','status':'Original interpretive writing; not quotations from Bosch or a scholar.','lines':LINES},indent=2),encoding='utf-8')
key=getpass.getpass('ElevenLabs key (hidden): ')
try:
 voice=json.loads((ROOT.parent/'audio-v1/voice-selection.json').read_text(encoding='utf-8'))
 for it in LINES:
  file=OUT/(it['id']+'.mp3')
  if file.exists():continue
  payload={'text':it['text'],'model_id':'eleven_multilingual_v2','voice_settings':{'stability':.76,'similarity_boost':.78,'style':.04,'use_speaker_boost':False,'speed':.88}}
  req=urllib.request.Request('https://api.elevenlabs.io/v1/text-to-speech/'+voice['voice_id']+'?output_format=mp3_44100_128',data=json.dumps(payload).encode(),headers={'xi-api-key':key,'Content-Type':'application/json','Accept':'audio/mpeg'},method='POST')
  try:
   with urllib.request.urlopen(req,timeout=70) as response:data=response.read()
  except urllib.error.HTTPError as exc:raise RuntimeError('ElevenLabs HTTP '+str(exc.code)) from None
  file.write_bytes(data);print('Generated',it['id'],len(data),'bytes',flush=True)
 (OUT/'voice.json').write_text(json.dumps({'provider':'ElevenLabs','voice_id':voice['voice_id'],'voice_name':voice['voice_name'],'model':'eleven_multilingual_v2','language':'en','key_saved':False},indent=2),encoding='utf-8')
except Exception as exc:print(type(exc).__name__,str(exc).replace(key,'[REDACTED]'),flush=True);raise SystemExit(2)
finally:key=''
