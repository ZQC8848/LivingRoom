"""Prepare tightly scoped 16:9 Orbis micro-motion tests from the approved scene."""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFilter

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'orbis-test'
OUT.mkdir(exist_ok=True)

# Supports use normalized coordinates in the generated garden/hell source strip,
# not coordinates in the exported equirectangular frame. Context surrounds each.
JOBS=[
 dict(id='water',layer='garden',label='水面',support=[.34,.675,.585,.742],
      action='Only the blue pond surface makes fine, shallow ripples that settle in place.',
      description='The blue pond beneath the distant blue fountain, between painted grassy banks.',
      polygon=[[.34,.69],[.40,.68],[.47,.675],[.575,.68],[.585,.715],[.55,.742],[.42,.738],[.34,.725]]),
 dict(id='horse',layer='garden',label='白马低头',support=[.013,.545,.081,.624],
      action='The small white horse keeps all four hooves planted and makes two tiny grazing nibbles, then holds its original lowered head position.',
      description='A small white horse grazes on the left grassy bank beside a narrow blue stream and a pink painted building.',
      polygon=[[.013,.565],[.025,.546],[.049,.545],[.071,.559],[.080,.588],[.081,.620],[.065,.624],[.047,.618],[.023,.618],[.013,.595]]),
 dict(id='bird',layer='garden',label='鸟翼轻动',support=[.096,.596,.151,.718],
      action='The blue long-legged bird keeps both feet planted and makes one small folded-wing ruffle, then settles into the same pose.',
      description='One small blue long-legged bird stands at the edge of the blue pond with a curved neck and folded wings, a pink building behind it.',
      polygon=[[.096,.643],[.112,.626],[.126,.600],[.140,.596],[.151,.610],[.143,.637],[.134,.662],[.132,.718],[.114,.718],[.107,.681],[.096,.665]]),
 dict(id='leaves',layer='garden',label='枝叶微风',support=[.576,.211,.648,.338],
      action='Only the green leaf tips at the top of the small tree bend by a tiny amount in a faint breeze and settle back.',
      description='A small green tree canopy stands above a pink shell-shaped garden building against a pale blue painted sky.',
      polygon=[[.583,.23],[.602,.211],[.625,.216],[.643,.239],[.648,.278],[.635,.316],[.614,.338],[.590,.316],[.576,.28]]),
 dict(id='fire',layer='hell',label='地狱远城火光',support=[.68,.294,.83,.374],
      action='Only the distant orange flames make a small in-place flicker behind the fixed dark skyline.',
      description='A distant ruined city glows orange behind a dark ridge, with charred trees and a cracked shell-shaped building in the foreground.',
      polygon=[[.68,.33],[.72,.306],[.77,.294],[.83,.31],[.83,.35],[.77,.369],[.71,.374],[.68,.35]]),
]

for job in JOBS:
    im=Image.open(ROOT/'bosch-world-assets'/f'{job["layer"]}-generated.png').convert('RGB')
    w,h=im.size
    x0,y0,x1,y1=job['support']
    # More static context than active content, and exact 16:9 at export.
    cw=max((x1-x0)*w*1.9,(y1-y0)*h*1.9*16/9, w*.18)
    ch=cw*9/16
    cx=(x0+x1)*w/2;cy=(y0+y1)*h/2
    cx=max(cw/2,min(w-cw/2,cx));cy=max(ch/2,min(h-ch/2,cy))
    crop=[round(cx-cw/2),round(cy-ch/2),round(cx+cw/2),round(cy+ch/2)]
    job['crop']=crop;job['source_pixels']=[w,h]
    folder=OUT/job['id'];folder.mkdir(exist_ok=True)
    ref=im.crop(crop).resize((1024,576),Image.Resampling.LANCZOS)
    ref.save(folder/'reference.png')
    full_mask=Image.new('L',(w,h));draw=ImageDraw.Draw(full_mask)
    draw.polygon([(round(x*w),round(y*h)) for x,y in job['polygon']],fill=255)
    # Feather INSIDE the support. Outside remains exactly zero.
    full_mask=full_mask.filter(ImageFilter.GaussianBlur(1.6))
    guard=Image.new('L',(w,h));ImageDraw.Draw(guard).rectangle([round(x0*w),round(y0*h),round(x1*w),round(y1*h)],fill=255)
    import PIL.ImageChops
    full_mask=PIL.ImageChops.multiply(full_mask,guard)
    full_mask.save(folder/'source-mask.png')
    mask=full_mask.crop(crop).resize((1024,576),Image.Resampling.LANCZOS)
    mask.save(folder/'context-mask.png')
    prompt=('Static camera, locked framing and deep focus throughout. '+job['description']+' '+job['action']+' The original painted brush texture, daylight, banks, buildings, horizon and every other figure remain fixed in their reference positions and shapes. The entire action stays inside the existing silhouette and its immediate surroundings. The opening and ending poses are nearly identical; the composition holds as a painted tableau.')
    job['prompt']=prompt;job['model']='reactor/visko-orbis-dynamic';job['capture_seconds']=6
    (folder/'prompt.txt').write_text(prompt,encoding='utf-8')

(OUT/'jobs.json').write_text(json.dumps(JOBS,ensure_ascii=False,indent=2),encoding='utf-8')
sheet=Image.new('RGB',(1024,5*328),(22,27,20));draw=ImageDraw.Draw(sheet)
for i,job in enumerate(JOBS):
    ref=Image.open(OUT/job['id']/'reference.png').convert('RGB')
    ref.thumbnail((512,288))
    sheet.paste(ref,(0,i*328+30))
    mask=Image.open(OUT/job['id']/'context-mask.png').convert('RGB');mask.thumbnail((512,288))
    sheet.paste(mask,(512,i*328+30))
    draw.text((10,i*328+9),job['id']+' / reference + active support',fill='white')
sheet.save(OUT/'reference-contact.jpg',quality=90)
print(json.dumps({'jobs':[j['id'] for j in JOBS],'reference_size':[1024,576],'camera':'fixed','output':str(OUT)}))
