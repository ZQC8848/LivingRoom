from pathlib import Path
from PIL import Image,ImageChops,ImageStat
import json

root=Path(__file__).resolve().parent/'bosch-hd'
out={}
for name in ['garden-equirect-8192.jpg','hell-equirect-8192.jpg']:
    im=Image.open(root/name).convert('RGB')
    w,h=im.size
    seam=ImageStat.Stat(ImageChops.difference(im.crop((0,0,1,h)),im.crop((w-1,0,w,h))))
    left_step=ImageStat.Stat(ImageChops.difference(im.crop((0,0,1,h)),im.crop((1,0,2,h))))
    right_step=ImageStat.Stat(ImageChops.difference(im.crop((w-2,0,w-1,h)),im.crop((w-1,0,w,h))))
    normal=[(a+b)/2 for a,b in zip(left_step.mean,right_step.mean)]
    out[name]={
        'pixels':[w,h],
        'seam_mean_channel_difference':seam.mean,
        'nearby_pixel_step_mean':normal,
        'top_row_extrema':im.crop((0,0,w,1)).getextrema(),
        'bottom_row_extrema':im.crop((0,h-1,w,h)).getextrema(),
    }
    assert (w,h)==(8192,4096)
    # A high-detail painting naturally varies between adjacent pixel columns.
    # Compare the wrap step against its neighbouring steps, not absolute equality.
    assert all(a<b*2.5+3 for a,b in zip(seam.mean,normal)),f'Unexpected wrap jump: {seam.mean} vs {normal}'
ref=Image.open(root/'hell-fire-reference-16x9.png')
out['model_reference']={'pixels':list(ref.size),'aspect':ref.width/ref.height}
assert ref.width*9==ref.height*16
(root/'export-checks.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out))
