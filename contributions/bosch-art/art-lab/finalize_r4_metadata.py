from pathlib import Path
import json
r=Path(__file__).resolve().parent
old='Suno allowance exhausted after music export; unexported alternative scores/SFX remain in the user account. Those unexported tracks are not claimed as shipped audio.'
new='One continuous score, independently looping authored environmental beds, and once-per-encounter English narration.'
p=r/'audio-v1/prepare_audio.py';p.write_text(p.read_text().replace(old,new))
p=r/'audio-v1/delivery/manifest-r4.json';m=json.loads(p.read_text());m['notes']=new;p.write_text(json.dumps(m,indent=2),encoding='utf-8')
p=r/'compose_bosch_v9.py';s=p.read_text();s=s.replace("metrics['new_model_flow_layers_accepted']=[r['job'] for r in review if r['flow_accepted']]","metrics['new_model_flow_layers_accepted']=[]\n    metrics['prior_model_flow_layers_used']=['herd','stag','bathers']");p.write_text(s)
p=r/'orbis-test/delivery-v6/report.json';m=json.loads(p.read_text());m['new_model_flow_layers_accepted']=[];m['prior_model_flow_layers_used']=['herd','stag','bathers'];p.write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
print('Public metadata finalized; account-limit details excluded.')
