from pathlib import Path
import json,hashlib
import cv2
ROOT=Path(__file__).resolve().parent.parent/'handoff/bosch-live-tests-20261114'
m=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
items=m['experiments']+m['longer_season_followup']['tests']
checks=[]
for it in items:
 p=ROOT/it['video']; cap=cv2.VideoCapture(str(p))
 w,h,fps,n=[cap.get(v) for v in (cv2.CAP_PROP_FRAME_WIDTH,cv2.CAP_PROP_FRAME_HEIGHT,cv2.CAP_PROP_FPS,cv2.CAP_PROP_FRAME_COUNT)]
 decoded=[]
 for frame in (0,int(n//2),int(n-2)):
  cap.set(cv2.CAP_PROP_POS_FRAMES,frame);ok,im=cap.read();decoded.append(bool(ok and im.std()>8))
 cap.release()
 check={'video':it['video'],'geometry':[w,h],'fps':fps,'seconds':round(n/fps,3),'first_middle_last_decoded':decoded,
        'expected_duration_seconds':it.get('recorded_seconds',it.get('seconds'))}
 check['pass']=w==960 and h==480 and fps==24 and all(decoded) and abs(n/fps-check['expected_duration_seconds'])<.8
 if 'sha256' in it:check['pass'] &= hashlib.sha256(p.read_bytes()).hexdigest()==it['sha256']
 checks.append(check)
c=cv2.VideoCapture(str(ROOT/m['overview']));ok,im=c.read();overview=bool(ok and im.shape[:2]==(720,1280));c.release()
result={'pass':all(c['pass'] for c in checks) and overview,'media_playback_only':True,
        'artistic_and_fixed_viewpoint_acceptance':False,'clips':checks,'overview_decoded':overview,
        'production_reveal_modified':False}
(ROOT/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
if not result['pass']:raise SystemExit(2)
