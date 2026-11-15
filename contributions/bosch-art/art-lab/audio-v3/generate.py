"""Generate the approved English art-history narration; credential is hidden stdin only."""
from pathlib import Path
import json,getpass,urllib.request,urllib.error
ROOT=Path(__file__).resolve().parent
key=getpass.getpass('ElevenLabs key (hidden): ')
settings={'stability':.43,'similarity_boost':.73,'style':.12,'use_speaker_boost':True,'speed':1.0}
try:
 script=json.loads((ROOT/'script.en.json').read_text())
 for cue in script['narration']:
  out=ROOT/(cue['id']+'.mp3')
  if out.exists():continue
  body={'text':cue['text'],'model_id':'eleven_multilingual_v2','voice_settings':settings}
  req=urllib.request.Request('https://api.elevenlabs.io/v1/text-to-speech/pFZP5JQG7iQjIQuC4Bku?output_format=mp3_44100_128',data=json.dumps(body).encode(),headers={'xi-api-key':key,'Content-Type':'application/json'},method='POST')
  try:
   with urllib.request.urlopen(req,timeout=90)as r:out.write_bytes(r.read())
  except urllib.error.HTTPError as e:raise RuntimeError('Narration provider returned HTTP '+str(e.code)) from None
  print('Generated',cue['id'],flush=True)
 (ROOT/'generation.json').write_text(json.dumps({'provider':'ElevenLabs','voice':'Lily — Velvety Actress','voice_id':'pFZP5JQG7iQjIQuC4Bku','model':'eleven_multilingual_v2','settings':settings,'key_saved':False},indent=2))
except Exception as e:print(type(e).__name__,str(e).replace(key,'[REDACTED]'));raise SystemExit(2)
finally:key=''
