"""Review package: real generated clips, evidence, and a labelled four-up replay."""
from pathlib import Path
import json,shutil,subprocess,hashlib
import cv2,numpy as np,imageio_ffmpeg
ROOT=Path(__file__).resolve().parent
DEST=ROOT.parent/'handoff/bosch-live-tests-20261114'
DEST.mkdir(exist_ok=True)
ASSESSMENTS={
 'garden-light':{'label':'Garden / Day-Night','result':'Night appears clearly; architectural reshaping and apparent framing drift. Not accepted for fixed-viewpoint production.'},
 'garden-season':{'label':'Garden / Seasons','result':'Falling leaves are visible; convincing winter snow coverage is not achieved. Large white blobs and shape drift are defects.'},
 'aftermath-light':{'label':'Aftermath / Day-Night','result':'Night, fire and smoke are visible; final image is too dark and architecture detail changes. Not accepted for production.'},
 'aftermath-weather':{'label':'Aftermath / Weather-Seasons','result':'Rain, smoke and illumination change are visible; persistent ground snow is not achieved and architecture changes.'}
}
manifest={'title':'The Garden of Consequences — Live Model Tests',
 'status':'Review only; none of these new modes has passed fixed-viewpoint and panorama seam acceptance.',
 'source':'Actual Orbis Dynamic output with mid-run prompt changes. These files are recordings, not a currently connected live stream.',
 'production_reveal':'Unchanged; no deployment modifications.',
 'camera':'All requests specify a fixed viewpoint. The model still causes geometry/framing drift; no post camera movement or stabilization added.',
 'projection':'2:1 review files undo the contain padding around the input. Raw files preserve the delivered composition. Full spherical seam and pole acceptance remains pending.',
 'experiments':[],
 'longer_season_followup':{'status':'Failed to start: provider returned 429 no available capacity. No frames generated.'}}
rows=[]
for job,a in ASSESSMENTS.items():
 src=ROOT/'live-modes-v1'/job/'run-02';dst=DEST/job;dst.mkdir(exist_ok=True)
 for name in ['panorama-review.mp4','raw-received.mp4','stages.jpg','report.json','review.json','reference-contained.png','reference-panorama.jpg']:
  shutil.copy2(src/name,dst/name)
 r=json.loads((dst/'report.json').read_text(encoding='utf-8'));qa=json.loads((dst/'review.json').read_text(encoding='utf-8'))
 stages=[c for c in r['commands'] if c['command']=='set_prompt']
 onset=r['first_frame_t']
 timeline=[{'target':c['stage'],'sent_seconds':round(max(0,c['sent_t']-onset),3),'ack_seconds':round(c['returned_t']-c['sent_t'],3)} for c in stages]
 entry={'id':job,**a,'accepted_for_production':False,'frames':r['frames'],'recorded_seconds':qa['seconds'],'timeline':timeline,
        'prompt_file':f'{job}/report.json','video':f'{job}/panorama-review.mp4','raw_video':f'{job}/raw-received.mp4'}
 entry['sha256']=hashlib.sha256((dst/'panorama-review.mp4').read_bytes()).hexdigest()
 manifest['experiments'].append(entry)
 rows.append((job,a,r,timeline))

# Common playback time compares four independent recordings; final frames hold.
caps=[cv2.VideoCapture(str(DEST/job/'panorama-review.mp4')) for job,_,_,_ in rows]
fps=24;seconds=max(c.get(cv2.CAP_PROP_FRAME_COUNT)/c.get(cv2.CAP_PROP_FPS) for c in caps)
ff=imageio_ffmpeg.get_ffmpeg_exe()
pipe=subprocess.Popen([ff,'-y','-f','rawvideo','-pix_fmt','bgr24','-s','1280x720','-r',str(fps),'-i','-','-an','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(DEST/'four-tests-overview.mp4')],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
last=[None]*4;contact=[]
try:
 for n in range(round(seconds*fps)):
  t=n/fps;canvas=np.full((720,1280,3),(19,25,21),dtype=np.uint8)
  for i,(cap,(job,a,r,timeline)) in enumerate(zip(caps,rows)):
   ok,im=cap.read()
   if ok:last[i]=im
   if last[i] is None:continue
   x=(i%2)*640;y=(i//2)*360
   tile=cv2.resize(last[i],(640,320),interpolation=cv2.INTER_AREA)
   canvas[y+40:y+360,x:x+640]=tile
   target=next((v['target'] for v in reversed(timeline) if t>=v['sent_seconds']),timeline[0]['target'])
   label=f"{a['label']} | target: {target} | REPLAY"
   cv2.putText(canvas,label,(x+10,y+26),cv2.FONT_HERSHEY_SIMPLEX,.49,(225,237,223),1,cv2.LINE_AA)
  pipe.stdin.write(canvas.tobytes())
  if n in (24,round(seconds*fps)-1):contact.append(canvas.copy())
 pipe.stdin.close();err=pipe.stderr.read();code=pipe.wait()
 if code:raise RuntimeError(err.decode(errors='replace')[-800:])
finally:
 for c in caps:c.release()
 if pipe.poll() is None:pipe.kill()
cv2.imwrite(str(DEST/'overview-first-last.jpg'),np.vstack(contact),[cv2.IMWRITE_JPEG_QUALITY,94])
manifest['overview']='four-tests-overview.mp4'
long=[]
for job in ['garden-season','aftermath-weather']:
 src=ROOT/'live-modes-v1'/job/'run-04'
 if not (src/'panorama-review.mp4').exists():continue
 dst=DEST/job/'full-season-cycle';dst.mkdir(exist_ok=True)
 for name in ['panorama-review.mp4','raw-received.mp4','stages.jpg','report.json','review.json']:
  shutil.copy2(src/name,dst/name)
 qa=json.loads((src/'review.json').read_text(encoding='utf-8'))
 long.append({'id':job,'seconds':qa['seconds'],'video':f'{job}/full-season-cycle/panorama-review.mp4',
              'accepted_for_production':False,'result':'Long spring-summer-autumn-winter steering. Severe geometry/framing drift; winter remains unreliable.'})
if long:
 manifest['longer_season_followup']={'status':'Capacity retry succeeded. Both full-season runs captured and rejected for geometric instability.','tests':long}
manifest['next_technical_candidate']='Validated same-layout seasonal reference images, re-anchor/reset within one session, freeze last valid frame while priming, then deliberate visual transition. Not implemented or validated by this test.'
(DEST/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'folder':str(DEST),'overview_seconds':seconds,'clips':len(rows),'production_unchanged':True},indent=2))
