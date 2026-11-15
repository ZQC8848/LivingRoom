"""Self-contained model-test viewer. No API credentials or browser model calls."""
from pathlib import Path
import base64,io,json
from PIL import Image

ROOT=Path(__file__).resolve().parent
DELIVERY=ROOT/'orbis-test/delivery'
VIS=Path(r'C:/Users/zoezi/.codex/visualizations/2026/11/14/01a1db35-61bc-73d0-9c2c-3bdd25ec5898')
TEMPLATE=(ROOT/'bosch-orbis.fragment.html').read_text(encoding='utf-8')

def media_uri(path,mime):return 'data:'+mime+';base64,'+base64.b64encode(path.read_bytes()).decode()
def image_uri(path,width,quality):
    im=Image.open(path).convert('RGB');im.thumbnail((width,width))
    stream=io.BytesIO();im.save(stream,'JPEG',quality=quality,optimize=True)
    return 'data:image/jpeg;base64,'+base64.b64encode(stream.getvalue()).decode()

statuses={
 'water':'原始场景保持未通过；合成版只提取模型的水面亮度波动。',
 'leaves':'原始输出有缩放与漂移；经稳像后，只把小幅光流转移到原画枝叶。',
 'fire':'原始结构较接近，仍有漂移；合成版只保留稳像后的局部火光亮度。',
 'horse':'未通过：白马被放大、改形，并出现走动。全景中保持原画静止。',
 'bird':'未通过：鸟和背景被重构。全景中保持原画静止。',
}
for edition in ('preview','full'):
    payload={'edition':edition,'raw':{}}
    for name in ('garden','hell'):
        payload[name]={'poster':image_uri(DELIVERY/f'{name}-poster.jpg',1024 if edition=='preview' else 2048,48 if edition=='preview' else 88),'video':media_uri(DELIVERY/f'{name}-{"preview" if edition=="preview" else "equirect-2048"}.mp4','video/mp4')}
    for name,status in statuses.items():
        run='run-stable-02' if name=='water' else 'run-stable-01'
        video=DELIVERY/f'{name}-raw-preview.mp4' if edition=='preview' else ROOT/'orbis-test'/name/run/'raw-orbis.mp4'
        payload['raw'][name]={'video':media_uri(video,'video/mp4'),'reference':image_uri(ROOT/'orbis-test'/name/'reference.png',512 if edition=='preview' else 1024,54 if edition=='preview' else 88),'status':status}
    fragment=TEMPLATE.replace('/*__MEDIA__*/',json.dumps(payload,ensure_ascii=False,separators=(',',':')))
    if edition=='preview':
        size=len(fragment.encode('utf-8'))
        if size>=1_000_000:raise ValueError(f'Inline preview exceeds 1 MB: {size}')
        target=VIS/'bosch-orbis-test.html';target.write_text(fragment,encoding='utf-8')
    else:
        target=ROOT/'bosch-orbis.html'
        wrapper='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>人间乐园 · Orbis 微动实测</title><style>html,body{margin:0;background:#141913}body{max-width:1400px;margin:auto}</style>'+fragment+'</html>'
        target.write_text(wrapper,encoding='utf-8')
    print(json.dumps({'edition':edition,'bytes':len(fragment.encode()),'path':str(target)}))
