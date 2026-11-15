from pathlib import Path
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parent;src=R.parent/'bosch-world-assets'
boxes={'G01':(55,95,205,248),'G02':(433,119,576,217),'G06':(1547,103,1648,222),'G07':(1632,184,1738,302),'G14':(396,482,492,557),'G20':(1025,494,1124,573),'Fountain':(744,348,1040,590),'G04':(945,118,1249,207)}
for id,box in boxes.items():
 im=Image.open(src/'garden-generated.png').convert('RGB').crop(box).resize(((box[2]-box[0])*5,(box[3]-box[1])*5))
 d=ImageDraw.Draw(im)
 for x in range((box[0]//10+1)*10,box[2],10):
  u=(x-box[0])*5;d.line((u,0,u,im.height),fill=(150,110,90),width=1);d.text((u+1,2),str(x),fill='black')
 for y in range((box[1]//10+1)*10,box[3],10):
  v=(y-box[1])*5;d.line((0,v,im.width,v),fill=(150,110,90),width=1);d.text((1,v+1),str(y),fill='black')
 im.save(R/(id+'-source-grid.png'))
print('Saved source coordinate crops.')
