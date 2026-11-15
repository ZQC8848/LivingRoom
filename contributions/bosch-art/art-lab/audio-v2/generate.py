"""Narration update. User's credential enters hidden stdin and stays in memory."""
from pathlib import Path
import argparse,getpass,json,urllib.request,urllib.error
ROOT=Path(__file__).resolve().parent;ROOT.mkdir(exist_ok=True)
ap=argparse.ArgumentParser();ap.add_argument('--catalog',action='store_true');ap.add_argument('--voice');a=ap.parse_args()
key=getpass.getpass('ElevenLabs key (hidden): ')
def request(path,payload=None):
 req=urllib.request.Request('https://api.elevenlabs.io'+path,data=json.dumps(payload).encode() if payload else None,headers={'xi-api-key':key,'Content-Type':'application/json'},method='POST' if payload else 'GET')
 try:
  with urllib.request.urlopen(req,timeout=80) as r:return r.read()
 except urllib.error.HTTPError as e:raise RuntimeError('ElevenLabs HTTP '+str(e.code)) from None
try:
 if a.catalog:
  voices=json.loads(request('/v2/voices?page_size=100'))['voices']
  stock=[{k:v.get(k) for k in ('voice_id','name','category','description','labels','preview_url')} for v in voices if v.get('category') in ('premade','default')]
  (ROOT/'voice-candidates.json').write_text(json.dumps(stock,indent=2),encoding='utf-8')
  print(json.dumps(stock,indent=2),flush=True)
 else:
  if not a.voice:raise ValueError('Choose a stock narration voice')
  script=json.loads((ROOT/'script.en.json').read_text(encoding='utf-8'))
  for cue in script['narration']:
   out=ROOT/(cue['id']+'.mp3')
   if out.exists():continue
   body={'text':cue['text'],'model_id':'eleven_multilingual_v2','voice_settings':{'stability':.43,'similarity_boost':.73,'style':.12,'use_speaker_boost':True,'speed':1.0}}
   out.write_bytes(request('/v1/text-to-speech/'+a.voice+'?output_format=mp3_44100_128',body));print('Generated',cue['id'],out.stat().st_size,flush=True)
  (ROOT/'generation.json').write_text(json.dumps({'provider':'ElevenLabs','voice_id':a.voice,'model':'eleven_multilingual_v2','settings':body['voice_settings'],'language':'en','key_saved':False},indent=2),encoding='utf-8')
except Exception as e:print(type(e).__name__,str(e).replace(key,'[REDACTED]'),flush=True);raise SystemExit(2)
finally:key=''
