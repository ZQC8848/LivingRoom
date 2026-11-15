"""User-approved temporary use of an idle keeper, never its lifecycle APIs.

Python SDK disconnect() ENDS a session, unlike the peer's JS example. Therefore
we pause generation, flush all reports, and exit the isolated client process
without disconnect()/close()/destructors. Only the WebRTC connection disappears.
No JWT is printed, written to disk, or embedded in public demo assets.
"""
import asyncio,json,os,time,logging,urllib.request
from pathlib import Path
import cv2,numpy as np
from reactor_sdk import Reactor
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'motion-v8/generation'

def env_values():
    result={}
    for line in (ROOT.parent/'.env').read_text(encoding='utf-8-sig').splitlines():
        if '=' not in line or line.lstrip().startswith('#'):continue
        k,v=line.split('=',1);result[k.strip()]=v.strip().strip('"').strip("'")
    return result
def keeper(path,post=False):
    env=env_values();url=env['A2A_PEER_URL'].rstrip('/')+path
    req=urllib.request.Request(url,method='POST' if post else 'GET',headers={'Authorization':'Bearer '+env['A2A_PEER_TOKEN']})
    return json.loads(urllib.request.urlopen(req,timeout=15).read())

async def main():
    held=await asyncio.to_thread(keeper,'/keeper/token',True)
    r=Reactor(model_name=held['model'],jwt=held['jwt'])
    # Never leave session credentials in output or exception messages.
    current=None;event=asyncio.Event();done=asyncio.Event();first_at=None;started=0
    reports=[];commands=[]
    @r.on_error
    def error(err):
        if current is not None:current['errors'].append(type(err).__name__)
    def frame(rgb):
        nonlocal first_at
        if current is None or done.is_set() or time.monotonic()-started<.5:return
        now=time.monotonic()
        if first_at is None:first_at=now;event.set()
        im=cv2.resize(np.asarray(rgb),(1024,576),interpolation=cv2.INTER_AREA)
        path=OUT/current['job']/'run-v8/frames'/f'{current["frames"]:04d}.jpg'
        cv2.imwrite(str(path),cv2.cvtColor(im,cv2.COLOR_RGB2BGR),[cv2.IMWRITE_JPEG_QUALITY,96])
        current['frames']+=1
        if now-first_at>=6 or current['frames']>=120:done.set()
    async def command(name,data):
        commands.append({'command':name,'job':current['job'] if current else None,'t':time.time()})
        await asyncio.wait_for(r.send_command(name,data),12)
    try:
        await asyncio.wait_for(r.connect(session_id=held['sessionId']),35)
        r.track('main_video').on_frame(frame)
        jobs=json.loads((OUT/'jobs.json').read_text(encoding='utf-8'))
        # Prioritize clearly articulated silhouettes; tiny deer can use puppetry.
        order=['sky-birds','waterbird-large','waterbird-small','aerial-creature','bathers','stag','herd','bank-bird']
        jobs.sort(key=lambda j:order.index(j['id']))
        for job in jobs:
            if (OUT/'stop-after-current').exists():
                print('Stopping after current capture for quality review.',flush=True)
                break
            folder=OUT/job['id']/'run-v8';reportpath=folder/'report.json'
            if reportpath.exists() and json.loads(reportpath.read_text()).get('status')=='captured':continue
            current=None
            await command('pause',{});await command('reset',{})
            folder.mkdir(exist_ok=True);(folder/'frames').mkdir(exist_ok=True)
            (folder/'effective-prompt.txt').write_text(job['prompt'],encoding='utf-8')
            ref=await asyncio.wait_for(r.upload_file(OUT/job['id']/'reference.png'),15)
            await command('set_image',{'image':ref})
            await command('set_prompt',{'prompt':job['prompt'],'passthrough':True})
            first_at=None;event.clear();done.clear()
            current=dict(job=job['id'],model=held['model'],adopted_keeper=True,frames=0,errors=[],status='working')
            started=time.monotonic();await command('start',{})
            print('Generating',job['id'],flush=True)
            try:
                await asyncio.wait_for(event.wait(),20);await asyncio.wait_for(done.wait(),18)
                current['status']='captured';current['captured_seconds']=round(time.monotonic()-first_at,3)
            except Exception as exc:current.update(status='failed',failure=type(exc).__name__)
            done.set();reportpath.write_text(json.dumps(current,indent=2),encoding='utf-8');reports.append(current)
            print(json.dumps(current),flush=True)
            await command('pause',{})
            if current['status']!='captured':break
    except Exception as exc:
        print('Held-session client stopped:',type(exc).__name__,flush=True)
    finally:
        done.set();current=None
        try:await command('pause',{})
        except Exception:pass
        (OUT/'held-batch-report.json').write_text(json.dumps({'reports':reports,'commands':commands,'lifecycle':'No disconnect, end, stop-session, extension or release calls. Paused then terminated only this isolated WebRTC client process.'},indent=2),encoding='utf-8')
        print('Local client finished; keeper lifecycle unchanged.',flush=True)
        os._exit(0)
if __name__=='__main__':
    logging.basicConfig(level=logging.CRITICAL)
    asyncio.run(main())
