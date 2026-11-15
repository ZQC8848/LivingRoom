from pathlib import Path
from PIL import Image,ImageFilter,ImageDraw,ImageChops
import json,os,urllib.request
root=Path(__file__).resolve().parent.parent
out=root/'deployment/bosch-demo/public/scenes/bosch-demo/live';out.mkdir(exist_ok=True)
for world,file in [('garden','poster.jpg'),('hell','hell-poster.jpg')]:
    im=Image.open(root/'deployment/bosch-demo/public/scenes/bosch-demo/media'/file).convert('RGB')
    # The approved 2:1 plate is contained, never stretched, inside the model's native 640:368 raster.
    im=im.resize((1280,640),Image.Resampling.LANCZOS)
    ref=Image.new('RGB',(1280,736));ref.paste(im,(0,48));ref.paste(im.crop((0,0,1280,1)).resize((1280,48)),(0,0));ref.paste(im.crop((0,639,1280,640)).resize((1280,48)),(0,688));ref.save(out/(world+'-reference.jpg'),quality=95)
    # A conservative, smooth environmental mask: no painted subject extends into these polar caps.
    mask=Image.new('L',(2048,1024));pixels=mask.load()
    for y in range(1024):
        # top 20% / bottom 16%, soft edges entirely outside subjects
        top=max(0,min(1,(194-y)/42));bottom=max(0,min(1,(y-850)/55));a=max(top,bottom);a=a*a*(3-2*a)
        for x in range(2048):pixels[x,y]=round(255*a)
    mask.save(out/(world+'-environment-mask.png'))
    # Broader open sky, with conservative exclusion around every painted aerial subject.
    sky=Image.new('L',(2048,1024));d=ImageDraw.Draw(sky);d.rectangle((0,0,2047,425),fill=255)
    protected=Image.new('L',sky.size);pd=ImageDraw.Draw(protected)
    polygons=[[(230,215),(450,215),(480,440),(210,440)],[(740,265),(830,265),(855,330),(925,380),(925,440),(610,440),(655,345),(715,315)],[(965,205),(1090,205),(1120,440),(935,440)],[(1220,270),(1365,270),(1365,340),(1430,355),(1460,440),(1145,440),(1175,345)],[(1640,280),(1755,280),(1815,440),(1575,440)]]
    for poly in polygons:pd.polygon(poly,fill=255)
    for box in [(45,190,235,350),(505,225,665,345),(1090,215,1430,310),(1770,195,1880,320),(1865,285,2030,455)]:pd.rectangle(box,fill=255)
    protected=protected.filter(ImageFilter.MaxFilter(25)).filter(ImageFilter.GaussianBlur(4))
    sky=ImageChops.subtract(sky.filter(ImageFilter.GaussianBlur(9)),protected)
    # Original aerial figures and structural silhouettes remain fully outside the live layer.
    expanded=ImageChops.lighter(mask,sky);expanded.save(out/(world+'-environment-mask.png'))
    original=Image.open(root/'deployment/bosch-demo/public/scenes/bosch-demo/media'/file).convert('RGB')
    # Orbis receives environmental materials only, never architecture to hallucinate into the sky.
    environmental=Image.new('RGB',(1280,640))
    environmental.paste(original.crop((0,0,2048,185)).resize((1280,335),Image.Resampling.LANCZOS),(0,0))
    environmental.paste(original.crop((0,870,2048,1024)).resize((1280,305),Image.Resampling.LANCZOS),(0,335))
    environmental=environmental.filter(ImageFilter.GaussianBlur(1))
    envref=Image.new('RGB',(1280,736));envref.paste(environmental,(0,48));envref.paste(environmental.crop((0,0,1280,1)).resize((1280,48)),(0,0));envref.paste(environmental.crop((0,639,1280,640)).resize((1280,48)),(0,688));envref.save(out/(world+'-environment-reference.jpg'),quality=95)
print('Prepared contained references and conservative sky/floor masks; painted subjects excluded.')
# Reuse the existing generated hillside world. Read-only API request, no generation.
env={}
for f in [root/'.env',Path(r'C:/Users/zoezi/Documents/xwechat_files/wxid_1zsuc44q76c221_75aa/msg/file/2026-11/.env')]:
    if f.exists():
        for line in f.read_text(encoding='utf-8-sig').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                k,v=line.split('=',1);env.setdefault(k.strip(),v.strip().strip('"').strip("'"))
key=env.get('WORLDLABS_API_KEY')
if key:
    try:
        request=urllib.request.Request('https://api.worldlabs.ai/marble/v1/worlds/e60f6310-08a9-4e1a-84ab-044b02844ffe',headers={'WLT-Api-Key':key})
        with urllib.request.urlopen(request,timeout=25) as r:data=json.load(r)
        world=data.get('world',data);url=world['assets']['imagery']['pano_url']
        with urllib.request.urlopen(url,timeout=40) as r:raw=r.read()
        import io
        im=Image.open(io.BytesIO(raw)).convert('RGB');im=im.resize((2048,1024),Image.Resampling.LANCZOS)
        # Rotate the existing panorama so longitude 12 degrees is front.
        shift=round(im.width*12/360);im=Image.frombytes('RGB',im.size,im.tobytes())
        from PIL import ImageChops
        im=ImageChops.offset(im,-shift,0);im.save(out/'hillside.jpg',quality=94)
        ref=Image.new('RGB',(1280,736));small=im.resize((1280,640));ref.paste(small,(0,48));ref.paste(small.crop((0,0,1280,1)).resize((1280,48)),(0,0));ref.paste(small.crop((0,639,1280,640)).resize((1280,48)),(0,688));ref.save(out/'hillside-reference.jpg',quality=94)
        print('Reused existing hillside panorama; no new World Labs generation.')
    except Exception as e:print('Existing hillside asset unavailable:',type(e).__name__)
