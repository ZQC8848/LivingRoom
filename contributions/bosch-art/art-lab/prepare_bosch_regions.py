from pathlib import Path
from PIL import Image,ImageDraw
import json

root=Path(__file__).resolve().parent/'bosch-hd'
regions=json.loads((root/'regions.json').read_text(encoding='utf-8'))
out=root/'regions'
out.mkdir(exist_ok=True)
records=[]
for region in regions:
    im=Image.open(root/f"{region['layer']}-full.jpg").convert('RGB')
    w,h=im.size
    x0,y0,x1,y1=region['active'];active=[x0*w,y0*h,x1*w,y1*h]
    cx=(active[0]+active[2])/2;cy=(active[1]+active[3])/2
    padding=region['padding']
    crop_w=max((active[2]-active[0])*(1+2*padding),(active[3]-active[1])*(1+2*padding)*16/9)
    crop_h=crop_w*9/16
    # Expand with original context, then fit 16:9 without squeezing the painting.
    left=max(0,min(w-crop_w,cx-crop_w/2));top=max(0,min(h-crop_h,cy-crop_h/2))
    crop=[round(left),round(top),round(left+crop_w),round(top+crop_h)]
    ref=im.crop(crop).resize((1024,576),Image.Resampling.LANCZOS)
    ref.save(out/f"{region['id']}-reference-16x9.png")
    ax0=(active[0]-crop[0])/crop_w*1024;ay0=(active[1]-crop[1])/crop_h*576
    ax1=(active[2]-crop[0])/crop_w*1024;ay1=(active[3]-crop[1])/crop_h*576
    mask=Image.new('L',(1024,576));d=ImageDraw.Draw(mask)
    d.rectangle((round(ax0),round(ay0),round(ax1),round(ay1)),fill=255)
    mask.save(out/f"{region['id']}-active-support-mask.png")
    region_record={**region,'reference_crop_in_layer_pixels':crop,'reference_pixels':[1024,576],'active_in_reference_pixels':[ax0,ay0,ax1,ay1],'reference':f"{region['id']}-reference-16x9.png",'support_mask':f"{region['id']}-active-support-mask.png",'generated':False}
    (out/f"{region['id']}-prompt.txt").write_text('Draft; not generated.\n\nLocked-off view of the supplied painting crop. '+region['motion']+' The surrounding paint, camera framing and the outer context hold their original shapes and positions.\n\n'+region['mask_note']+'\n',encoding='utf-8')
    records.append(region_record)
(out/'manifest.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'regions':len(records),'generated':False,'directory':str(out)},ensure_ascii=False))
