"""Create the minimal, checksum-verifiable static media handoff (no secrets)."""
from pathlib import Path
import hashlib,json,subprocess,zipfile,math
import cv2
import imageio_ffmpeg

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'orbis-test/delivery-v4'
TARGET=ROOT.parent/'handoff/bosch-demo-20261114'
MEDIA=TARGET/'media'
MEDIA.mkdir(parents=True,exist_ok=True)
ff=imageio_ffmpeg.get_ffmpeg_exe()

def run(args):
    p=subprocess.run([ff,'-y',*args],capture_output=True)
    if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace')[-1400:])

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

files={}
for layer,name,poster in [('garden','heaven','poster'),('hell','hell','hell-poster')]:
    video=MEDIA/f'{name}.mp4'
    # The working-space exports have untagged BT.601 YUV. Convert the matrix,
    # rather than relabelling its samples, to make both release files BT.709 TV.
    run(['-i',str(SOURCE/f'{layer}-equirect-2048.mp4'),'-an',
         '-vf','scale=in_color_matrix=bt601:out_color_matrix=bt709:in_range=tv:out_range=tv',
         '-c:v','libx264','-preset','fast','-crf','19','-profile:v','high','-level:v','4.0',
         '-g','60','-keyint_min','60','-sc_threshold','0','-pix_fmt','yuv420p',
         '-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-color_range','tv',
         '-movflags','+faststart',str(video)])
    run(['-i',str(video),'-frames:v','1','-q:v','2',str(MEDIA/f'{poster}.jpg')])
    cap=cv2.VideoCapture(str(video))
    info=dict(width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),fps=cap.get(cv2.CAP_PROP_FPS),frames=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
    cap.release()
    if info!={'width':2048,'height':1024,'fps':30.0,'frames':240}:raise ValueError(info)
    for path in (video,MEDIA/f'{poster}.jpg'):
        files[path.name]={'bytes':path.stat().st_size,'sha256':sha(path)}

def focus(x,y):
    v=y/887
    lat=-math.atan((v-.36)*math.tan(math.radians(64))/(.64 if v>=.36 else .36))
    return dict(u=x/1774,v=.5-lat/math.pi,longitude_degrees=(x/1774-.5)*360,latitude_degrees=math.degrees(lat))

manifest={
 'schema_version':1,'scene':'bosch-demo','release':'2026-11-14-r1',
 'title':'欲望的两面','subtitle':'The Garden of Consequences',
 'media':{'heaven':'heaven.mp4','hell':'hell.mp4','poster':'poster.jpg','hellPoster':'hell-poster.jpg','fps':30,'loop':True},
 'video':{'width':2048,'height':1024,'aspect_ratio':'2:1','projection':'equirectangular','fps':30,'frame_count':240,'duration_seconds':8,'codec':'h264','profile':'High','level':'4.0','pixel_format':'yuv420p','color_space':'BT.709','color_primaries':'BT.709','transfer':'BT.709','range':'limited','audio':False,'faststart':True,'gop_frames':60},
 'orientation':{'front_longitude_degrees':0,'front_u':.5,'image_origin':'top-left','zenith_v':0,'nadir_v':1,'right_is_increasing_u':True,'camera_motion':'none','already_projected':True,'geometry':'head-locked sphere; translation removed'},
 'sampling':{'notes':'Direct 2:1 equirect sampling. No 16:9 stretch, model edge crop, or new cylindrical-band projection. The sky/floor and narrow rear blend are already baked in. Apply texture flipY exactly once for Three.js UV convention.','paired_pixels_aligned':True},
 'loop':{'method':'authored periodic motion and eased forward/reverse reuse of generated bird/fire clips','native_model_loop':False},
 'production':{'horse':'Fixed original painted head/closed muzzle and horn, small anchored nod. Mouth texture and alpha are not regenerated.','water':'Whole-river controlled travelling ripples and small elliptical rings, with architecture/islands/figures excluded.','bird':'Retained Orbis Dynamic poses, exposure matched object mattes.','fire':'Retained Orbis Stable flame shapes, keyed behind a fixed skyline.','new_model_calls':0,'headset_verified':False},
 'focus':{'horse':focus(129,533),'bird':focus(221,581),'water':focus(930,628),'leaves':focus(1109,224),'fire':focus(1337,282)},
 'files':files,
}
(MEDIA/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
archive=TARGET/'bosch-demo-media.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(MEDIA.iterdir()):z.write(p,'media/'+p.name)
result={'archive':str(archive),'sha256':sha(archive),'bytes':archive.stat().st_size,'manifest':manifest}
(TARGET/'release.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='manifest'},indent=2))
