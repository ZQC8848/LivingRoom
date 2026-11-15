from pathlib import Path
import sys,json,subprocess
import cv2,numpy as np
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bosch_marked_motion_v9 import *
import imageio_ffmpeg
g=np.asarray(Image.open(ROOT/'bosch-world-assets/garden-generated.png').convert('RGB'));h=np.asarray(Image.open(ROOT/'bosch-world-assets/hell-generated.png').convert('RGB'));m=MarkedMotion(g,h)
specs=[('G01','garden',(45,95,210,252)),('G02','garden',(433,121,580,220)),('G04','garden',(937,114,1268,211)),('G06','garden',(1531,110,1650,225)),('G07','garden',(1630,177,1740,297)),('G14','garden',(399,489,483,553)),('G20','garden',(1022,471,1146,577)),('WATER','garden',(768,370,1047,580)),('FIRE-LEFT','hell',(0,177,125,331)),('FIRE-RIGHT','hell',(1605,140,1763,330)),('PIPE','hell',(1078,168,1214,289))]
base={'garden':g,'hell':h};metrics={}
cw,ch=320,245;sheet=Image.new('RGB',(cw*4,ch*len(specs)),(20,25,21));draw=ImageDraw.Draw(sheet)
for row,(id,layer,box) in enumerate(specs):
 out=[]
 for i in range(64):
  p=i/64*2*np.pi;f=base[layer].astype(np.float32).copy()
  if id=='WATER':m.falling_water(f,p)
  elif id.startswith('FIRE') or id=='PIPE':m.fire(f,p)
  else:next(a for a in m.actors[layer] if a.it['id']==id).render(f,p)
  if not np.isfinite(f).all():raise ValueError('Nonfinite '+id)
  crop=np.uint8(np.clip(f[box[1]:box[3],box[0]:box[2]],0,255));out.append(crop)
  if i in [0,16,32,48]:
   im=Image.fromarray(crop);im.thumbnail((310,205));sheet.paste(im,(i//16*cw,row*ch+27));draw.text((i//16*cw+5,row*ch+6),f'{id} {i/8:.1f}s',fill='white')
 array=np.array(out,np.float32);metrics[id]={'mean_temporal_std':float(array.std(axis=0).mean()),'all_finite':True}
 cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{out[0].shape[1]}x{out[0].shape[0]}','-r','8','-i','-','-vf','scale=640:-2','-an','-c:v','libx264','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/f'{id}-fix.mp4')]
 proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
 for f in out:proc.stdin.write(f.tobytes())
 proc.stdin.close()
 if proc.wait():raise ValueError(id)
 print('Preview',id,flush=True)
sheet.save(OUT/'fix-contact.jpg',quality=96)
(OUT/'preview-metrics.json').write_text(json.dumps(metrics,indent=2))
