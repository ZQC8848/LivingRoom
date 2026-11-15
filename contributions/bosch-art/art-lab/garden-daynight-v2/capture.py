"""Owned, bounded re-anchor test. No keeper or public deployment changes."""
from pathlib import Path
import sys,asyncio,time,json,threading,logging
import cv2,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from run_bosch_live_modes import load_key,safe
from reactor_sdk import Reactor
ROOT=Path(__file__).resolve().parent
def save(p,v):p.write_text(json.dumps(v,indent=2),encoding='utf-8')
async def main():
    r=Reactor(model_name='reactor/visko-orbis-dynamic',api_key=load_key(),max_session_duration_seconds=180)
    loop=asyncio.get_running_loop();lock=threading.RLock();first=asyncio.Event();now0=time.monotonic()
    current=None;accept_after=float('inf');closed=False;frames=[];state={}
    report={'model':'reactor/visko-orbis-dynamic','session_owned':True,'max_session_seconds':180,'phases':[],
            'method':'Actual reset/set_image/set_prompt/start in one owned session; day, night, day again.',
            'note':'Raw recordings are model evidence. The authored loop will be labelled separately.'}
    @r.on_message
    def message(msg):
        nonlocal state
        if not isinstance(msg,dict):return
        kind=msg.get('type');data=msg.get('data') or {}
        if kind=='state' and isinstance(data,dict):state=data.get('state',data)
        if current is not None and kind in ('generation_started','image_accepted','prompt_accepted','chunk_complete','command_error'):
            e={'t':round(time.monotonic()-now0,4),'type':kind}
            if kind in ('command_error','chunk_complete'):e['data']=json.loads(safe(json.dumps(data,default=str)))
            current['events'].append(e)
    @r.on_error
    def error(e):
        if current is not None:current['errors'].append(safe(e))
    def frame(rgb):
        with lock:
            if closed or current is None or time.monotonic()<accept_after:return
            t=time.monotonic()-now0
            if not frames:
                current['first_frame_t']=round(t,6);current['delivered_pixels']=[int(rgb.shape[1]),int(rgb.shape[0])]
                loop.call_soon_threadsafe(first.set)
            im=cv2.resize(np.asarray(rgb),(1280,round(rgb.shape[0]*1280/rgb.shape[1])),interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(Path(current['folder'])/'frames'/f'{len(frames):05d}.jpg'),cv2.cvtColor(im,cv2.COLOR_RGB2BGR),[cv2.IMWRITE_JPEG_QUALITY,96])
            frames.append(round(t,6))
    async def command(name,data):
        e={'command':name,'sent_t':round(time.monotonic()-now0,5)}
        if name=='set_prompt':e['prompt']=data['prompt']
        if current is not None:current['commands'].append(e)
        res=await asyncio.wait_for(r.send_command(name,data),15)
        e.update(returned_t=round(time.monotonic()-now0,5),reply_type=res.get('type') if isinstance(res,dict) else None)
        return res
    try:
        print('Connecting bounded owned Dynamic reanchor test',flush=True)
        await asyncio.wait_for(r.connect(),70)
        save(ROOT/'runtime-schema.json',await asyncio.wait_for(r.request_schema(),10))
        r.track('main_video').on_frame(frame)
        refs={label:await r.upload_file(ROOT/'references'/f'{label}-contained.png') for label in ('day','night')}
        for label,ref_label,seconds in [('day','day',12),('night','night',12),('day-return','day',8)]:
            folder=ROOT/'captures'/label;(folder/'frames').mkdir(parents=True,exist_ok=True)
            with lock:
                accept_after=float('inf');frames=[];first.clear()
                current={'id':label,'reference':ref_label,'folder':str(folder),'request_t':round(time.monotonic()-now0,5),'commands':[],'events':[],'errors':[],'status':'working'}
            report['phases'].append(current)
            await command('reset',{})
            if '1080p' in state.get('available_resolutions',[]):await command('set_resolution',{'resolution':'1080p'})
            await command('set_image',{'image':refs[ref_label]})
            prompt=('A painted garden in clear daylight. Fine water ripples flow across the existing river, with a soft breeze in the leaves. The painted architecture remains still.' if ref_label=='day' else
                    'The same painted garden at blue moonlit night. Existing warm windows glow steadily, fine silver ripples flow across the existing river, leaves stir gently. The painted architecture remains still.')
            await command('set_prompt',{'prompt':prompt,'passthrough':True})
            await command('start',{})
            with lock:accept_after=time.monotonic()+4
            print('Reanchored',label,flush=True)
            await asyncio.wait_for(first.wait(),40)
            print(label,'fresh picture after',round(current['first_frame_t']-current['request_t'],2),'s',flush=True)
            await asyncio.sleep(seconds)
            with lock:
                accept_after=float('inf');current['frame_timestamps']=list(frames);current['frames']=len(frames)
                current['status']='captured';current['first_frame_latency_seconds']=round(current['first_frame_t']-current['request_t'],3)
            await command('pause',{})
            save(folder/'report.json',current);save(ROOT/'capture-report.json',report)
            print(label,'captured',current['frames'],flush=True)
            with lock:current=None
    except Exception as e:
        report['error']=safe(f'{type(e).__name__}: {e}');print(report['error'][:300],flush=True)
    finally:
        with lock:
            closed=True
            if current is not None and current.get('status')=='working':
                current.update(status='failed',frame_timestamps=list(frames),frames=len(frames));save(Path(current['folder'])/'report.json',current)
        try:
            await asyncio.wait_for(r.disconnect(),15);report['owned_session_disconnected']=True
        except Exception as e:report['cleanup_note']=safe(type(e).__name__)
        report['elapsed_seconds']=round(time.monotonic()-now0,3);save(ROOT/'capture-report.json',report)
        print('Owned reanchor test finished',flush=True)
if __name__=='__main__':
    logging.basicConfig(level=logging.CRITICAL);asyncio.run(main())
