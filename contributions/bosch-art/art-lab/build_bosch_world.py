"""Build a full-surround spatial composition study, separate from original crops.

Generated scenes are composition drafts, not faithful reproductions. The viewer
corrects the painted horizon and creates the final equirectangular projection.
"""
from pathlib import Path
import base64
import io
import json
import math
from PIL import Image, ImageDraw, ImageStat

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'bosch-world-assets'
VIS = Path(r'C:/Users/zoezi/.codex/visualizations/2026/11/14/01a1db35-61bc-73d0-9c2c-3bdd25ec5898')
OUT.mkdir(exist_ok=True)
REGIONS = [
    dict(id='A', layer='garden', label='水面微波', active=[.26,.60,.39,.70], motion='Only tiny water ripples. Lock all birds, figures, buildings and banks.'),
    dict(id='B', layer='garden', label='枝梢轻摆', active=[.585,.19,.635,.31], motion='Only the selected leaf tips move slightly and return. No growth or new objects.'),
    dict(id='C', layer='garden', label='远处人物候选', active=[.706,.50,.755,.55], motion='One tiny head or hand adjustment and return. Bodies stay planted; no walking, no new people.'),
    dict(id='D', layer='hell', label='远城火光', active=[.20,.30,.32,.37], motion='A small distant flame flickers in place. Do not spread the fire or move the camera.'),
    dict(id='E', layer='hell', label='远处烟气', active=[.69,.30,.81,.36], motion='Faint smoke drifts a tiny distance inside the selected area and settles. Keep the ridge fixed.'),
    dict(id='F', layer='hell', label='黑水倒影', active=[.42,.64,.58,.72], motion='A slight fire reflection shivers and settles on the black water. No shoreline change.'),
]

def uri(im, size, quality):
    p = im.copy()
    p.thumbnail(size, Image.Resampling.LANCZOS)
    b = io.BytesIO()
    p.save(b, 'JPEG', quality=quality, optimize=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode(), list(p.size)

assets = {}
colors = {}
for name in ('garden', 'hell'):
    im = Image.open(OUT / f'{name}-generated.png').convert('RGB')
    full, pixels = uri(im, im.size, 94)
    preview, preview_pixels = uri(im, (1536,768), 60)
    assets[name] = dict(full=full, preview=preview, pixels=pixels, preview_pixels=preview_pixels, aspect=im.width/im.height)
    for label, crop in [('SKY',(0,0,im.width,round(im.height*.04))), ('GROUND',(0,round(im.height*.96),im.width,im.height))]:
        rgb = ImageStat.Stat(im.crop(crop)).mean[:3]
        colors[f'__{"DAY" if name=="garden" else "HELL"}_{label}__'] = 'vec3(' + ','.join(f'{x/255:.6f}' for x in rgb) + ')'

reference = Image.open(ROOT/'bosch-hd/original-reference.jpg').convert('RGB')
ref, ref_pixels = uri(reference, (850,431), 70)
assets['reference'] = dict(full=ref, preview=ref, pixels=ref_pixels, preview_pixels=ref_pixels, aspect=reference.width/reference.height)

constants = []
manifest = []
regions_dir = OUT/'regions'
regions_dir.mkdir(exist_ok=True)
for r in REGIONS:
    im = Image.open(OUT/f'{r["layer"]}-generated.png').convert('RGB')
    w,h = im.size
    x0,y0,x1,y1 = r['active']
    cx,cy = (x0+x1)*w/2,(y0+y1)*h/2
    cw = max((x1-x0)*w*1.75, (y1-y0)*h*1.75*16/9)
    ch = cw*9/16
    cx = max(cw/2,min(w-cw/2,cx))
    cy = max(ch/2,min(h-ch/2,cy))
    crop = [round(cx-cw/2),round(cy-ch/2),round(cx+cw/2),round(cy+ch/2)]
    context = [crop[0]/w,crop[1]/h,crop[2]/w,crop[3]/h]
    active = ','.join(f'{v:.8f}' for v in r['active'])
    context_gl = ','.join(f'{v:.8f}' for v in context)
    constants.append(f'const vec4 {r["id"]}=vec4({active});const vec4 C{r["id"]}=vec4({context_gl});')
    ref = im.crop(crop).resize((1024,576),Image.Resampling.LANCZOS)
    ref.save(regions_dir/f'{r["id"]}-reference-16x9.png')
    box = [(x0*w-crop[0])*1024/(crop[2]-crop[0]), (y0*h-crop[1])*576/(crop[3]-crop[1]), (x1*w-crop[0])*1024/(crop[2]-crop[0]), (y1*h-crop[1])*576/(crop[3]-crop[1])]
    mask = Image.new('L',(1024,576));ImageDraw.Draw(mask).rectangle(box,fill=255)
    mask.save(regions_dir/f'{r["id"]}-support-mask.png')
    prompt = 'Locked camera, unchanged composition and identities. A restrained 3-second painted tableau. '+r['motion']+' End close to the starting pose. Nothing crosses the active support boundary. No zoom, pan, dolly, parallax, morphing, new objects or scene cut. The reference context stays still. A seamless loop is desired but must be inspected and repaired in post.'
    (regions_dir/f'{r["id"]}-prompt.txt').write_text(prompt,encoding='utf-8')
    manifest.append({**r,'context':context,'reference_crop':crop,'reference_pixels':[1024,576],'mask_type':'rectangular support, requires semantic tracing','prompt':prompt,'video_generated':False})

(OUT/'regions.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
template = (ROOT/'bosch-world.fragment.html').read_text(encoding='utf-8')
for key,val in colors.items():
    template = template.replace('/*'+key+'*/',val)
for edition in ('preview','full'):
    payload = {k:dict(src=v[edition],pixels=v['preview_pixels'] if edition=='preview' else v['pixels'],aspect=v['aspect']) for k,v in assets.items()}
    fragment = template.replace('/*__ROOM_ASSETS__*/',json.dumps(payload,separators=(',',':'))).replace('/*__EDITION__*/',json.dumps(edition)).replace('/*__REGIONS__*/',json.dumps(manifest,ensure_ascii=False,separators=(',',':'))).replace('/*__REGION_CONSTANTS__*/','\n'.join(constants))
    if '/*__' in fragment:
        raise ValueError('Unresolved build marker')
    if edition=='preview':
        assert len(fragment.encode())<1_000_000, 'Preview exceeds inline size limit'
        VIS.mkdir(parents=True,exist_ok=True)
        target = VIS/'bosch-world.html'
        target.write_text(fragment,encoding='utf-8')
    else:
        target = ROOT/'bosch-world.html'
        wrapper = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>欲望的两面 · 空间改编样片</title><style>html,body{margin:0;background:#141913}body{max-width:1400px;margin:auto}</style>'+fragment+'</html>'
        target.write_text(wrapper,encoding='utf-8')
    print(json.dumps(dict(edition=edition,path=str(target),fragment_bytes=len(fragment.encode()),source_pixels=payload['garden']['pixels'])))

provenance = dict(kind='AI-assisted spatial composition study after Bosch',tool='built-in image_gen.imagegen, not CLI',date='2026-11-14',source_reference='https://commons.wikimedia.org/wiki/File:Jheronimus_Bosch_023.jpg',garden=dict(file='garden-generated.png',native_pixels=assets['garden']['pixels'],reference='../bosch-hd/garden-preview.jpg',generated_original='exec-ffe010d1-e190-4cd1-9d00-b9d0cdff0675.png'),hell=dict(file='hell-generated.png',native_pixels=assets['hell']['pixels'],reference=['garden-generated.png','../bosch-hd/hell-preview.jpg'],generated_original='exec-5e94425a-cb46-43c6-b4db-bc29e652609a.png'),reproduction=False,video_model_run=False,mapping=dict(horizontal_coverage_degrees=360,instances=1,painted_horizon_v=.36,band_half_height_degrees=64,seam_blend_total_degrees=10.8,export='2:1 equirectangular RGB; output size does not increase native image detail'))
(OUT/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
