from pathlib import Path
import json

ROOT=Path(__file__).resolve().parent
VIS=Path(r'C:/Users/zoezi/.codex/visualizations/2026/11/14/01a1db35-61bc-73d0-9c2c-3bdd25ec5898')
assets=json.loads((ROOT/'bosch-hd/room-assets.json').read_text(encoding='utf-8'))
regions=json.loads((ROOT/'bosch-hd/regions.json').read_text(encoding='utf-8'))
manifest=json.loads((ROOT/'bosch-hd/regions/manifest.json').read_text(encoding='utf-8'))
constants=[]
for region in manifest:
    active=','.join(format(v,'.8f') for v in region['active'])
    width,height=assets[region['layer']]['pixels']
    crop=region['reference_crop_in_layer_pixels']
    context=','.join(format(v,'.8f') for v in [crop[0]/width,crop[1]/height,crop[2]/width,crop[3]/height])
    constants.append(f"const vec4 {region['id']}=vec4({active}); const vec4 C{region['id']}=vec4({context});")
template=(ROOT/'bosch-room.fragment.html').read_text(encoding='utf-8')
for edition in ['preview','full']:
    payload={k:{'src':v[edition],'aspect':v['aspect'],'pixels':v['preview_pixels'] if edition=='preview' else v['pixels']} for k,v in assets.items()}
    fragment=template.replace('/*__ROOM_ASSETS__*/',json.dumps(payload,separators=(',',':'))).replace('/*__EDITION__*/',json.dumps(edition))
    fragment=fragment.replace('/*__REGIONS__*/',json.dumps(regions,ensure_ascii=False,separators=(',',':')))
    fragment=fragment.replace('/*__REGION_CONSTANTS__*/','\n'.join(constants))
    if edition=='preview':
        if len(fragment.encode())>=1_000_000:raise SystemExit('Preview exceeds 1 MB')
        VIS.mkdir(parents=True,exist_ok=True)
        (VIS/'bosch-ring-room.html').write_text(fragment,encoding='utf-8')
    else:
        document='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>人间乐园 · 环形画厅</title><style>html,body{margin:0;background:#141913}body{max-width:1400px;margin:auto}</style>'+fragment+'</html>'
        (ROOT/'bosch-room.html').write_text(document,encoding='utf-8')
    print(json.dumps({'edition':edition,'fragment_bytes':len(fragment.encode())}))
