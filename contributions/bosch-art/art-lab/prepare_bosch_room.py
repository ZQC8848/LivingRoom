from pathlib import Path
from PIL import Image,ImageFilter
import base64
import io
import json

ROOT=Path(__file__).resolve().parent/'bosch-hd'
im=Image.open(ROOT/'bosch-master-8533.jpg').convert('RGB')
boxes={'garden':(2285,32,6275,4290),'hell':(6785,32,8495,1960)}
meta={}
for name,box in boxes.items():
    crop=im.crop(box)
    crop.save(ROOT/f'{name}-full.jpg',quality=94,optimize=True)
    preview=crop.copy();preview.thumbnail((1536,1536))
    preview.save(ROOT/f'{name}-preview.jpg',quality=66,optimize=True)
    meta[name]={'crop':box,'pixels':list(crop.size),'aspect':crop.width/crop.height,'preview_pixels':list(preview.size)}
    for quality,path in [('full',ROOT/f'{name}-full.jpg'),('preview',ROOT/f'{name}-preview.jpg')]:
        meta[name][quality]='data:image/jpeg;base64,'+base64.b64encode(path.read_bytes()).decode()
reference=im.copy();reference.thumbnail((850,500))
reference.save(ROOT/'original-reference.jpg',quality=56,optimize=True)
reference_src='data:image/jpeg;base64,'+base64.b64encode((ROOT/'original-reference.jpg').read_bytes()).decode()
meta['reference']={'crop':[0,0,im.width,im.height],'pixels':list(reference.size),'aspect':reference.width/reference.height,'preview_pixels':list(reference.size),'full':reference_src,'preview':reference_src}
# Keep the complete right panel as the source reference, rather than silently discarding it.
im.crop((6785,32,8495,4290)).save(ROOT/'hell-complete-reference.jpg',quality=94,optimize=True)
(ROOT/'room-assets.json').write_text(json.dumps(meta,separators=(',',':')),encoding='utf-8')
print(json.dumps({k:{p:q for p,q in v.items() if p not in ('preview','full')} for k,v in meta.items()}))
print(json.dumps({p.name:p.stat().st_size for p in ROOT.glob('*.jpg')}))

full_hell=im.crop((6785,32,8495,4290))
ref_box=(80,100,1616,964)
ref=full_hell.crop(ref_box)
ref.save(ROOT/'hell-fire-reference-16x9.png')
px=ref.load();mask=Image.new('L',ref.size);mp=mask.load()
for y in range(ref.height):
    for x in range(ref.width):
        r,g,b=px[x,y]
        if r>50 and r>g*1.35 and r>b*1.7 and g>18:mp[x,y]=255
mask=mask.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(3))
mask.save(ROOT/'hell-fire-support-mask.png')
contract={'projection':'equirectangular','mapping':'single-occurrence cylinder sector','source_instances':1,'horizontal_span_formula_radians':'2 * tan(band_half_height) * original_aspect','final_reference_resolution':[8192,4096],'painting_band_latitude_deg':[-30,30],'soft_transition_deg':5,'observer_translation':[0,0,0],'model_reference_resolution':list(ref.size),'model_reference_aspect':'16:9','model_reference_crop_in_right_panel':list(ref_box),'model_generation_resolution':[832,480],'final_output_tracks':1,'static_base':'garden-equirect-8192.jpg','alternate_reference':'hell-equirect-8192.jpg','model_reference':'hell-fire-reference-16x9.png','post_support_mask':'hell-fire-support-mask.png','region_manifest':'regions/manifest.json','mask_status':'support areas only; subject segmentation and manual cleanup required; not an Orbis input','motion_prompt_status':'draft, not generated or evaluated','headset_performance':'not tested','surround_composition':'one occurrence of the original front sector; remaining azimuth is ambient and explicitly pending authored extension'}
(ROOT/'integration.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
