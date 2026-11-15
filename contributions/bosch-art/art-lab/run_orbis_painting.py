"""Bounded Orbis test. Credentials are read locally and never written to outputs.

Run with the task-local venv. Uses local received frames, so a recorder failure
cannot discard the model test. Every created session is ended in finally.
"""
from pathlib import Path
import argparse
import asyncio
import json
import logging
import os
import time
import traceback
import cv2
import numpy as np
from reactor_sdk import Reactor

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'orbis-test'
ENV=Path(r'C:/Users/zoezi/Documents/xwechat_files/wxid_1zsuc44q76c221_75aa/msg/file/2026-11/.env')
SECRETS=[]

def load_keys():
    for line in ENV.read_text(encoding='utf-8-sig').splitlines():
        if '=' not in line or line.lstrip().startswith('#'):continue
        k,v=line.split('=',1);k=k.strip();v=v.strip().strip('\"').strip("'")
        if k in ('REACTOR_API_KEY','REACTOR_API_KEY_2'):
            os.environ.setdefault(k,v);SECRETS.append(v)

def safe(value):
    text=str(value)
    for s in SECRETS:
        if s:text=text.replace(s,'[REDACTED]')
    return text

def log(value):print(safe(value),flush=True)

async def run_job(job,key_name,seconds,attempt):
    folder=OUT/job['id']/f'run-{attempt}'
    frames_dir=folder/'frames';frames_dir.mkdir(parents=True,exist_ok=True)
    (folder/'effective-prompt.txt').write_text(job['prompt'],encoding='utf-8')
    report=dict(job=job['id'],model=job['model'],prompt=job['prompt'],requested_capture_seconds=seconds,frames=0,events=[],errors=[],attempt=attempt)
    r=Reactor(model_name=job['model'],api_key=os.environ[key_name],max_session_duration_seconds=75)
    first=asyncio.Event();done=asyncio.Event();t0=time.monotonic();first_t=None
    received=[];resolutions=[];start_at=None
    @r.on_message
    def message(msg):
        nonlocal resolutions
        if not isinstance(msg,dict):return
        kind=msg.get('type','unknown');data=msg.get('data') or {}
        if kind in ('state','generation_started','generation_complete','command_error','image_accepted','prompt_accepted'):
            report['events'].append({'t':round(time.monotonic()-t0,3),'type':kind})
            if kind not in ('state',):log(f'{job["id"]}: {kind}')
        if kind=='state' and isinstance(data,dict):
            state=data.get('state',data)
            if isinstance(state,dict) and state.get('available_resolutions'):resolutions=state['available_resolutions']
        if kind=='command_error':report['errors'].append(safe(data))
    @r.on_error
    def error(err):
        report['errors'].append(safe(err));log(f'{job["id"]}: model error {safe(err)[:250]}')
    def frame(rgb):
        nonlocal first_t
        if done.is_set():return
        now=time.monotonic()
        if first_t is None:
            first_t=now;report['first_frame_latency_seconds']=round(now-start_at,3) if start_at else None
            report['delivered_pixels']=[int(rgb.shape[1]),int(rgb.shape[0])]
            log(f'{job["id"]}: first frame {report["delivered_pixels"]}, latency {report["first_frame_latency_seconds"]}s')
            first.set()
        # Keep the full received composition, store at reference size for analysis.
        im=cv2.resize(np.asarray(rgb),(1024,576),interpolation=cv2.INTER_AREA)
        n=report['frames'];cv2.imwrite(str(frames_dir/f'{n:04d}.jpg'),cv2.cvtColor(im,cv2.COLOR_RGB2BGR),[cv2.IMWRITE_JPEG_QUALITY,96])
        received.append(round(now-first_t,6));report['frames']+=1
        if now-first_t>=seconds or report['frames']>=round(seconds*20):done.set()
    try:
        log(f'{job["id"]}: connecting, capture {seconds}s, hard session limit 75s')
        await asyncio.wait_for(r.connect(),45)
        report['connect_seconds']=round(time.monotonic()-t0,3)
        schema=await asyncio.wait_for(r.request_schema(),10)
        (folder/'runtime-schema.json').write_text(json.dumps(schema,indent=2),encoding='utf-8')
        if '1080p' in resolutions:await r.send_command('set_resolution',{'resolution':'1080p'})
        # Runtime state is authoritative; the SDK's track API is documented.
        r.track('main_video').on_frame(frame)
        ref=await asyncio.wait_for(r.upload_file(OUT/job['id']/'reference.png'),15)
        await r.send_command('set_image',{'image':ref})
        await r.send_command('set_prompt',{'prompt':job['prompt'],'passthrough':True})
        start_at=time.monotonic()
        await r.send_command('start',{})
        await asyncio.wait_for(first.wait(),25)
        await asyncio.wait_for(done.wait(),seconds+12)
        report['captured_seconds']=received[-1] if received else 0
        report['available_resolutions']=resolutions
        report['status']='captured'
        try:await asyncio.wait_for(r.send_command('pause',{}),5)
        except Exception as exc:report['pause_note']=safe(exc)
    except Exception as exc:
        report['status']='failed';report['errors'].append(safe(f'{type(exc).__name__}: {exc}'))
        log(f'{job["id"]}: {report["errors"][-1][:500]}')
    finally:
        done.set()
        try:await asyncio.wait_for(r.disconnect(),12)
        except Exception as exc:report['cleanup_note']=safe(exc);r.close()
        report['client_elapsed_seconds']=round(time.monotonic()-t0,3)
        report['received_timestamps_seconds']=received
        (folder/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        log(json.dumps({k:report.get(k) for k in ('job','status','frames','first_frame_latency_seconds','captured_seconds','client_elapsed_seconds','errors')},ensure_ascii=False))
    return report

async def main():
    ap=argparse.ArgumentParser();ap.add_argument('jobs',nargs='+');ap.add_argument('--seconds',type=float,default=6);ap.add_argument('--attempt',default='01');ap.add_argument('--key',default='REACTOR_API_KEY');ap.add_argument('--model',choices=['dynamic','stable'],default='dynamic');ap.add_argument('--painterly',action='store_true');a=ap.parse_args()
    if not 2<=a.seconds<=12:raise ValueError('Capture must be 2–12 seconds')
    load_keys()
    configs={j['id']:j for j in json.loads((OUT/'jobs.json').read_text(encoding='utf-8'))}
    for name in a.jobs:
        job={**configs[name],'model':'reactor/visko-orbis-'+a.model}
        if a.painterly:
            job['prompt']=('A flat early-Netherlandish oil painting holds the exact composition and fine painted brushwork of the reference image. '+job['action']+' Every painted building, figure, animal, bank and branch holds its established shape and position; the painting stays flat, with the original mineral colors. Static camera, locked frame, identical framing throughout. A tiny local painted movement, with the rest of the painting still.')
        report=await run_job(job,a.key,a.seconds,a.attempt)
        if report['status']!='captured':raise SystemExit(2)

if __name__=='__main__':
    logging.basicConfig(level=logging.ERROR)
    asyncio.run(main())
