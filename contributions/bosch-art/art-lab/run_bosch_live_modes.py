"""Four bounded, image-anchored LIVE prompt-steering experiments.

Owns its session, never attaches to or alters a keeper. Secrets only in memory.
Stores actual received frames and command timing; no fabricated tween/filter.
"""
from pathlib import Path
import argparse, asyncio, json, logging, os, time, threading
import cv2
import numpy as np
from reactor_sdk import Reactor

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'live-modes-v1'
SECRETS = []
LOCK = (' Fixed panoramic painted tableau, camera bolted in place. Identical framing and field of view throughout. '
        'All five architectural landmarks remain at exactly the same screen coordinates and size; shorelines and horizon stay fixed. '
        'Preserve the wide rectangular painting and its plain upper and lower margins. '
        'Only environmental light, weather, water and foliage change. No camera movement, pan, tilt, zoom, dolly, orbit, '
        'rotation, reframing, cuts, parallax, or perspective change. No new buildings. Preserve the painted art style.')
GARDEN = ('The same Bosch-inspired early Netherlandish painted garden, with the pink shell house at left, '
          'blue flower tower, central blue fountain, pink shell house right of centre and blue orb house at right, '
          'a river and green banks, holds the exact reference composition.')
HELL = ('The same Bosch-inspired ruined painted garden, with the cracked pink shell house at left, '
        'broken flower tower, central face fountain, cracked shell house right of centre and ruined orb house at right, '
        'dark river and charred trees, holds the exact reference composition.')
JOBS = [
 {'id':'garden-light','world':'garden','label':'Garden · Day / Night', 'stages':[
  ('Day', 'It is bright late afternoon. Tree crowns sway in the breeze and the river flows with visible ripples.'),
  ('Dusk', 'The whole sky becomes rose and violet dusk; sunlight dims visibly across the whole garden. Clouds move, tree crowns sway and water reflections change. Gradual environmental illumination change, not a scene transition.'),
  ('Night', 'The same garden is now visibly deep blue NIGHT. A dark moonlit sky, soft luminous flowers and moonlight reflected in the moving river. All buildings and figures keep their outlines. The scene remains legible, with a quiet breeze.') ]},
 {'id':'garden-season','world':'garden','label':'Garden · Seasons','stages':[
  ('Summer', 'It is green summer. The broad tree crowns sway visibly, clouds move and water ripples.'),
  ('Autumn', 'AUTUMN arrives visibly across the whole garden: green tree crowns become ochre and amber; complete leaves detach and fall in the wind; grass becomes pale gold. Water flows. The same architecture stays unchanged.'),
  ('Winter', 'WINTER arrives in the same garden. Fine visible snow falls vertically and settles on the banks, grass, roofs and tree branches. Trees have sparse leaves. The same river remains partly unfrozen with visible ripples. Cold pale daylight.') ]},
 {'id':'aftermath-light','world':'hell','label':'Aftermath · Day / Night','stages':[
  ('Day', 'Ashen DAYLIGHT makes all ruins clearly visible. Distant flames rise behind the fixed city silhouette; broad smoke plumes visibly climb and drift. The dark river ripples.'),
  ('Dusk', 'Ashen daylight fades visibly into copper dusk in the same ruined garden. Whole clouds of smoke drift upward, distant fire tongues rise, and their moving reflections spread across the dark river.'),
  ('Night', 'It is now NIGHT in the same ruined garden. The sky becomes charcoal dark, making distant orange flames and scattered embers clearly visible. Smoke billows upward and moving orange reflections shimmer across the dark water. Buildings stay in place and do not flicker or melt.') ]},
 {'id':'aftermath-weather','world':'hell','label':'Aftermath · Weather / Seasons','stages':[
  ('Dry heat', 'Dry heat over the ruined garden. Visible ash drifts gently, smoke rises and distant fires burn behind the fixed skyline. No optical heat distortion of buildings.'),
  ('Rain', 'Steady RAIN now visibly falls across the same ruined garden. Raindrops make expanding ripples across the dark river; smoke becomes softer and the distant flames diminish into embers. The banks become wet and dark. All ruins stay still.'),
  ('Wet winter', 'Cold wet WINTER in the same ruined garden. Clearly visible snow falls and thin pale snow collects on dark banks, roofs and charred branches. Fires have retreated into a few embers. Dark unfrozen water ripples. The same ruins remain recognizable.') ]}
]
STRONG_STAGES = {
 'garden-light': [('Day','Sunny daylight over a painted fantasy garden. Trees sway and river water ripples.'),
                  ('Dusk','SUNSET. The entire painted garden becomes orange and violet twilight. The sky changes to purple and the water reflects orange clouds. Ambient light visibly dims everywhere.'),
                  ('Night','DARK BLUE NIGHT. The whole painted garden is now illuminated only by moonlight. A deep midnight-blue sky and silver moon reflections in the flowing river. Daylight is gone. Dark blue ground and pale moonlit buildings.')],
 'garden-season': [('Summer','Green summer in a painted fantasy garden. Green grass and leafy trees, moving river.'),
                   ('Autumn','AUTUMN. All tree leaves turn orange and yellow, many whole leaves fall in the wind. Golden grass, grey sky, moving river, the same painted buildings.'),
                   ('Winter','SNOWY WINTER. Thick WHITE SNOW covers the grass, banks and roofs of the same painted garden. Bare trees, falling white snowflakes, cold grey sky. The river ripples between snow-covered banks.')],
 'aftermath-light': [('Day','BRIGHT ASHEN DAYLIGHT illuminates a ruined painted garden and dark river. Fixed distant flames and rising smoke.'),
                     ('Dusk','SUNSET over the same ruined painted garden. Orange sky fades to purple. Fire glows more visibly and smoke rises, reflections ripple in the river.'),
                     ('Night','DARK NIGHT. The entire ruined painted garden becomes charcoal black and deep blue, lit by bright orange flames and glowing embers. Large smoke plumes rise and drifting fire reflections move in dark water.')],
 'aftermath-weather': [('Dry heat','A dry ruined painted garden, charred banks, distant flames and rising smoke.'),
                       ('Rain','HEAVY RAIN visibly falls across the same ruined painted garden. Many raindrops create spreading rings on the river. Grey rain clouds, wet dark banks; distant fires shrink to embers.'),
                       ('Wet winter','SNOWY WINTER in the same ruined painted garden. WHITE SNOW visibly covers the charred banks and ruined roofs. Many white snowflakes fall through cold grey air. Dark water ripples; only a few embers remain.')]
}

def safe(x):
    s = str(x)
    for key in SECRETS:
        if key: s = s.replace(key, '[REDACTED]')
    return s

def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def load_key():
    candidates = [ROOT.parent/'.env', Path(r'C:/Users/zoezi/Documents/xwechat_files/wxid_1zsuc44q76c221_75aa/msg/file/2026-11/.env')]
    for p in candidates:
        if not p.exists(): continue
        for line in p.read_text(encoding='utf-8-sig').splitlines():
            if '=' not in line or line.lstrip().startswith('#'): continue
            k,v = line.split('=',1); k=k.strip(); v=v.strip().strip('"').strip("'")
            if k in ('REACTOR_API_KEY','REACTOR_API_KEY_2'):
                os.environ.setdefault(k,v); SECRETS.append(v)
    return os.environ['REACTOR_API_KEY']

def prepare_reference(world, folder):
    image = cv2.imread(str(ROOT/'bosch-world-assets'/f'{world}-generated.png'))
    if image is None: raise FileNotFoundError(world)
    # 2:1 art contained in native 640:368 aspect. No cropping or anisotropic resize.
    art = cv2.resize(image, (1280,640), interpolation=cv2.INTER_AREA)
    ref = np.empty((736,1280,3), dtype=np.uint8)
    ref[:48] = np.median(art[:12],axis=(0,1)).astype(np.uint8)
    ref[48:688] = art
    ref[688:] = np.median(art[-12:],axis=(0,1)).astype(np.uint8)
    cv2.imwrite(str(folder/'reference-contained.png'),ref)
    cv2.imwrite(str(folder/'reference-panorama.jpg'),art,[cv2.IMWRITE_JPEG_QUALITY,97])
    return folder/'reference-contained.png'

async def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--jobs', nargs='*'); ap.add_argument('--attempt',default='01'); ap.add_argument('--strong',action='store_true'); ap.add_argument('--season-cycle',action='store_true');ap.add_argument('--stage-seconds',type=float,default=12)
    args=ap.parse_args(); OUT.mkdir(exist_ok=True)
    jobs=[j for j in JOBS if not args.jobs or j['id'] in args.jobs]
    if args.strong:jobs=[{**j,'stages':STRONG_STAGES[j['id']]} for j in jobs]
    if args.season_cycle:
        for j in jobs:
            if j['id']=='garden-season':
                j['stages']=[('Spring','SPRING. Fresh green grass and small flowers in a painted fantasy garden, moving river and a soft breeze.'),
                             ('Summer','SUMMER. Warm bright sunshine over the same painted garden. Rich green leafy trees sway and blue water flows. Same architecture and shorelines.'),
                             ('Autumn','AUTUMN. Orange and yellow leaves cover the same trees. Whole leaves detach and visibly fall, golden grass and overcast sky. Same architecture and shorelines.'),
                             ('Winter','WINTER. White snow blankets the entire ground and all roofs. Bare branches, many small falling snowflakes, cold pale grey sky, dark flowing river between snow-covered banks. The same painted buildings remain.')]
            if j['id']=='aftermath-weather':
                j['stages']=[('Spring','SPRING in the same ruined painted garden. Grey daylight, a few sparse green shoots near damp river banks, drifting smoke and rippling dark water.'),
                             ('Summer','SUMMER HEAT in the same ruined painted garden. Dry ochre banks and vivid distant orange fires. Tall plumes of dark smoke rise through a copper sky. The dark river shimmers.'),
                             ('Autumn','AUTUMN RAIN in the same ruined painted garden. Steady rain visibly falls, raindrops form many expanding circles in the river, distant fire diminishes and grey smoke drifts. Wet dark banks.'),
                             ('Winter','WINTER. The same ruined painted garden is covered with WHITE SNOW on banks, roofs and charred branches. Many small falling snowflakes in cold grey air. A few embers and rippling dark water remain.')]
    batchdir=OUT/f'batch-{args.attempt}'; batchdir.mkdir(exist_ok=True)
    report={'kind':'actual-received-live-generation','model':'reactor/visko-orbis-dynamic',
            'session_owned':True,'hard_session_limit_seconds':240,'jobs':[],
            'note':'Recordings of live hot prompt changes, not a currently connected live viewer. No generated-frame interpolation or post color animation.'}
    r=Reactor(model_name=report['model'],api_key=load_key(),max_session_duration_seconds=240)
    current=None; state={}; t0=time.monotonic(); first=asyncio.Event(); frame_times=[]
    closed=False; accept_after=float('inf'); media_lock=threading.RLock(); loop=asyncio.get_running_loop()
    @r.on_message
    def message(msg):
        nonlocal state
        if not isinstance(msg,dict):return
        kind=msg.get('type'); data=msg.get('data') or {}
        if kind=='state' and isinstance(data,dict): state=data.get('state',data)
        if current is not None and kind=='state' and isinstance(state,dict):
            current['states'].append({'t':round(time.monotonic()-t0,3), **{k:state[k] for k in ('current_prompt','state','resolution','available_resolutions','live_resolution_switching') if k in state}})
        if current is not None and kind in ('prompt_accepted','generation_started','generation_complete','chunk_complete','command_error','image_accepted'):
            event={'t':round(time.monotonic()-t0,4),'type':kind}
            if kind in ('chunk_complete','command_error'):event['data']=json.loads(safe(json.dumps(data,default=str)))
            current['events'].append(event)
    @r.on_error
    def error(e):
        if current is not None:current['errors'].append(safe(e))
        print('Model error:',safe(e)[:160],flush=True)
    def frame(rgb):
        # The SDK invokes media on its FFI thread, not the asyncio loop.
        with media_lock:
            if closed or current is None or time.monotonic()<accept_after:return
            now=time.monotonic(); rgb=np.asarray(rgb)
            if not frame_times:
                current['first_frame_t']=round(now-t0,4)
                current['delivered_pixels']=[int(rgb.shape[1]),int(rgb.shape[0])]
                loop.call_soon_threadsafe(first.set)
            # Preserve delivered geometry. Native files are evidence; review crop is later.
            n=len(frame_times)
            im=cv2.resize(rgb,(960,round(rgb.shape[0]*960/rgb.shape[1])),interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(Path(current['folder'])/'frames'/f'{n:05d}.jpg'),cv2.cvtColor(im,cv2.COLOR_RGB2BGR),[cv2.IMWRITE_JPEG_QUALITY,94])
            frame_times.append(round(now-t0,6))
    async def command(name,data,stage=None):
        entry={'command':name,'stage':stage,'sent_t':round(time.monotonic()-t0,4)}
        if name=='set_prompt':entry['prompt']=data['prompt']
        if current is not None:current['commands'].append(entry)
        reply=await asyncio.wait_for(r.send_command(name,data),15)
        entry['returned_t']=round(time.monotonic()-t0,4)
        entry['reply_type']=reply.get('type') if isinstance(reply,dict) else None
        return reply
    try:
        print('Connecting owned bounded Dynamic session',flush=True)
        await asyncio.wait_for(r.connect(),90)
        report['connect_seconds']=round(time.monotonic()-t0,3)
        schema=await asyncio.wait_for(r.request_schema(),12)
        save(batchdir/'runtime-schema.json',schema)
        r.track('main_video').on_frame(frame)
        print('Connected; available resolutions:',state.get('available_resolutions'),flush=True)
        for j in jobs:
            if time.monotonic()-t0>210:
                report['stopped']='near session limit';break
            with media_lock:current=None;accept_after=float('inf')
            await command('reset',{})
            folder=OUT/j['id']/f'run-{args.attempt}';(folder/'frames').mkdir(parents=True,exist_ok=True)
            refpath=prepare_reference(j['world'],folder)
            current={'id':j['id'],'label':j['label'],'folder':str(folder),'commands':[],'events':[],'states':[],'errors':[],
                     'status':'working','source_fraction':[0,48/736,1,688/736]}
            report['jobs'].append(current); frame_times=[];first.clear()
            resolutions=state.get('available_resolutions',[])
            if '1080p' in resolutions:await command('set_resolution',{'resolution':'1080p'})
            ref=await asyncio.wait_for(r.upload_file(refpath),20)
            await command('set_image',{'image':ref})
            base=GARDEN if j['world']=='garden' else HELL
            def prompt(action):
                if args.strong:return action+' Keep the exact wide reference painting composition and all buildings in the same positions. Locked tripod camera, no pan, tilt, zoom, dolly, rotation, parallax or reframing. Only the weather and light change.'
                return base+' '+action+LOCK
            await command('set_prompt',{'prompt':prompt(j['stages'][0][1]),'passthrough':not args.strong},j['stages'][0][0])
            await command('start',{})
            accept_after=time.monotonic()+4.0
            print(j['id'],'started',flush=True)
            try:
                await asyncio.wait_for(first.wait(),55)
                await asyncio.sleep(3)
                for stage,action in j['stages'][1:]:
                    await command('set_prompt',{'prompt':prompt(action),'passthrough':not args.strong},stage)
                    print(j['id'],'HOT PROMPT',stage,'frames',len(frame_times),flush=True)
                    await asyncio.sleep(args.stage_seconds if args.strong else 9)
                await command('pause',{})
                current['status']='captured' if len(frame_times)>30 else 'insufficient_frames'
            except Exception as e:
                current['status']='failed'; current['errors'].append(safe(f'{type(e).__name__}: {e}'))
            with media_lock:
                accept_after=float('inf')
                current['frame_timestamps']=list(frame_times);current['frames']=len(frame_times)
            current['recorded_wall_seconds']=round(frame_times[-1]-frame_times[0],3) if frame_times else 0
            save(folder/'report.json',current); save(batchdir/'report.json',report)
            print(j['id'],current['status'],current['frames'],'frames',flush=True)
            current=None
    except Exception as e:
        report['error']=safe(f'{type(e).__name__}: {e}')
        print('Batch failed:',report['error'][:350],flush=True)
    finally:
        with media_lock:closed=True
        if current is not None and 'frame_timestamps' not in current:
            current['frame_timestamps']=list(frame_times);current['frames']=len(frame_times)
            current['status']='interrupted';save(Path(current['folder'])/'report.json',current)
        try:await asyncio.wait_for(r.disconnect(),15)
        except Exception as e: report['cleanup_note']=safe(type(e).__name__)
        report['elapsed_seconds']=round(time.monotonic()-t0,3)
        save(batchdir/'report.json',report)
        print('Owned session ended. Report:',str(batchdir/'report.json'),flush=True)

if __name__=='__main__':
    logging.basicConfig(level=logging.CRITICAL)
    asyncio.run(main())
