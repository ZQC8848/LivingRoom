"""Reproducible 30-second edit from the user's Quest casting recording."""
from pathlib import Path
import subprocess, json, sys
from PIL import Image, ImageDraw, ImageFont, ImageOps
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'source/Casting_Video_1794721792334.mp4'
WORK = ROOT / 'work'
OUT = ROOT / 'output'
FF = imageio_ffmpeg.get_ffmpeg_exe()
WORK.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
W, H, FPS = 1920, 1080, 30
INK = '#101c21'; WHITE = '#f2eee4'; GOLD = '#d4bd86'; MUTED = '#a7b8ba'
FONT = Path('C:/Windows/Fonts')
def font(size, bold=False, serif=False):
    return ImageFont.truetype(str(FONT / ('georgia.ttf' if serif else 'segoeuib.ttf' if bold else 'segoeui.ttf')), size)
def write(d, xy, text, size=32, color=WHITE, bold=False, spacing=12):
    d.multiline_text(xy, text, font=font(size,bold), fill=color, spacing=spacing)
def run(args):
    p = subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', *map(str,args)], capture_output=True, text=True)
    if p.returncode: raise RuntimeError(p.stderr[-6000:])

segments = [
 dict(id='intro', start=4.498, frames=126, speed=1, label='QUEST CAPTURE · 1×', eyebrow='A CLASSIC PAINTING, RECONSIDERED', title='The Garden of\nConsequences'),
 dict(id='reveal', start=14.6, frames=240, speed=1, label='QUEST CAPTURE · 1×', eyebrow='01 / REVEAL', title='One place.\nTwo possibilities.', body='Point and pinch to reveal\nthe other side of the garden.', tech='Aligned panoramic layers\n+ a gesture-controlled mask'),
 dict(id='return', start=23.428625, frames=150, speed=1, label='QUEST CAPTURE · 1×', eyebrow='02 / RETURN', title='Let go.\nLook again.', body='The garden returns.\nWhat you saw remains.', tech='The interaction carries the story.\nThe composition stays aligned.'),
 dict(id='garden-daynight', start=31.8, frames=56, speed=3, label='PREPARED LOOP · 3× PLAYBACK', eyebrow='OPTIONAL MODE / 1 OF 4', title='Garden\nDay / Night', body='Time changes.\nThe painted world stays anchored.', tech='Prepared day / night loop'),
 dict(id='hell-daynight', start=46.5, frames=56, speed=3, label='PREPARED LOOP · 3× PLAYBACK', eyebrow='OPTIONAL MODE / 2 OF 4', title='Aftermath\nDay / Night', body='A different light\non the same consequences.', tech='Prepared day / night loop'),
 dict(id='garden-seasons', start=57.0, frames=56, speed=3, label='PREPARED LOOP · 3× PLAYBACK', eyebrow='OPTIONAL MODE / 3 OF 4', title='Garden\nSeasons', body='Abundance changes\nwith the passing seasons.', tech='Prepared seasonal loop'),
 dict(id='hell-seasons', start=69.5, frames=56, speed=3, label='PREPARED LOOP · 3× PLAYBACK', eyebrow='OPTIONAL MODE / 4 OF 4', title='Aftermath\nSeasons', body='Weather changes.\nThe ruined world remains.', tech='Prepared seasonal loop'),
 dict(id='live', start=124.5, frames=160, speed=1, label='RECORDED LIVE LAB SESSION · 1×', eyebrow='SECOND SCENARIO / LIVE LAB', title='Prompt a\ndifferent world.', body='Orbis Dynamic\nPrompt-steered generation', tech='A separate, realistic scenario.\nRecorded session; waits omitted.'),
]
original = Image.open(ROOT.parent/'deployment/bosch-demo/public/artwork/bosch-original-triptych.jpg').convert('RGB')

def make_cards(s, index):
    im=Image.new('RGB',(W,H),INK);d=ImageDraw.Draw(im)
    d.line((60,78,796,78),fill=GOLD,width=2)
    write(d,(60,38),'IMMERSE THE BAY 2026',22,GOLD,True)
    if s['id']=='intro':
        write(d,(60,113),s['eyebrow'],22,MUTED,True)
        write(d,(56,165),s['title'],66,WHITE,True,8)
        art=ImageOps.contain(original,(736,374));im.paste(art,(60,383+(374-art.height)//2))
        write(d,(60,797),'An interactive adaptation of',25,MUTED)
        write(d,(60,841),'The Garden of Earthly Delights',32,WHITE,True)
        write(d,(60,894),'Hieronymus Bosch · c. 1500',29,GOLD)
        write(d,(60,942),'Northern Renaissance · Prado Museum, Madrid',24,MUTED)
    else:
        write(d,(60,114),'THE GARDEN OF CONSEQUENCES',25,WHITE,True)
        write(d,(60,230),s['eyebrow'],23,GOLD,True)
        write(d,(56,292),s['title'],70,WHITE,True,12)
        write(d,(60,511),s['body'],34,WHITE,False,16)
        d.line((60,708,796,708),fill='#3a4b50',width=2)
        write(d,(60,752),'HOW IT WORKS',21,GOLD,True)
        write(d,(60,801),s['tech'],28,MUTED,False,16)
        write(d,(60,956),'HEADSET RECORDING / EDITED FOR BREVITY',20,MUTED)
    # A compact editorial progress index, outside the recorded viewport.
    for j in range(len(segments)):
        x=60+j*93
        d.rounded_rectangle((x,1030,x+79,1035),radius=2,fill=GOLD if j==index else '#33434a')
    im.save(WORK/f"{s['id']}-card.png")
    overlay=Image.new('RGBA',(W,H));od=ImageDraw.Draw(overlay)
    label=s['label'];f=font(22,True);box=od.textbbox((0,0),label,font=f)
    od.rounded_rectangle((902,25,936+box[2],72),radius=8,fill=(12,24,29,220))
    od.text((919,34),label,font=f,fill=WHITE)
    overlay.save(WORK/f"{s['id']}-overlay.png")

cursor=0
for i,s in enumerate(segments):
    s['output_start']=cursor;dur=s['frames']/FPS;s['output_duration']=dur;cursor+=dur
    make_cards(s,i)
    target=WORK/f"{i:02d}-{s['id']}.mp4"
    if '--audio-only' in sys.argv and target.exists():
        continue
    graph=(f'[0:v]setpts=(PTS-STARTPTS)/{s["speed"]},fps={FPS},scale=1008:1080:flags=lanczos,setsar=1[v];'
           '[1:v][v]overlay=876:0:shortest=1[base];[base][2:v]overlay=0:0:shortest=1,format=yuv420p[out]')
    run(['-ss',s['start'],'-t',dur*s['speed']+.25,'-i',SOURCE,
         '-loop','1','-framerate',FPS,'-i',WORK/f"{s['id']}-card.png",
         '-loop','1','-framerate',FPS,'-i',WORK/f"{s['id']}-overlay.png",
         '-filter_complex',graph,'-map','[out]','-an','-frames:v',s['frames'],
         '-c:v','libx264','-preset','fast','-crf','19','-color_range','tv','-colorspace','bt709',target])
    print(f"Rendered {s['id']}: {dur:.3f}s",flush=True)

concat=WORK/'concat.txt'
concat.write_text('\n'.join(f"file '{(WORK/f'{i:02d}-{s['id']}.mp4').as_posix()}'" for i,s in enumerate(segments)),encoding='utf-8')
run(['-f','concat','-safe','0','-i',concat,'-c','copy',WORK/'picture-30s.mp4'])

# Preserve the user's recorded narration. Cut complete sentences at natural pauses.
# Cue identification is waveform correlation against the previously generated originals.
# The Reveal voice excerpt is shifted under an adjacent take of the same interaction.
music=ROOT.parent/'deployment/bosch-demo/public/audio/music.mp3'
audio_graph=(
 '[0:a]atrim=start=4.498:duration=4.2,asetpts=PTS-STARTPTS,afade=t=out:st=4.1:d=0.1[a0];'
 '[0:a]atrim=start=15.962:duration=7.3375,asetpts=PTS-STARTPTS,afade=t=in:d=0.025,afade=t=out:st=7.23:d=0.1,adelay=4400|4400[a1];'
 '[0:a]atrim=start=23.428625:duration=4.922625,asetpts=PTS-STARTPTS,afade=t=in:d=0.025,afade=t=out:st=4.82:d=0.1,adelay=12200|12200[a2];'
 '[1:a]atrim=start=12:duration=30,asetpts=PTS-STARTPTS,volume=\'if(lt(t,17.2),0.13,0.13+0.37*min((t-17.2)/0.5,1))\':eval=frame,afade=t=in:d=0.25,afade=t=out:st=29:d=1[bed];'
 '[a0][a1][a2][bed]amix=inputs=4:duration=longest:normalize=0,volume=5.5dB,alimiter=limit=0.89:level=false,apad=whole_dur=30,atrim=duration=30[out]')
run(['-i',SOURCE,'-i',music,'-filter_complex',audio_graph,'-map','[out]','-ar','48000','-ac','2','-c:a','pcm_s16le',WORK/'mix-30s.wav'])
run(['-i',WORK/'picture-30s.mp4','-i',WORK/'mix-30s.wav','-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-b:a','192k','-t','30','-movflags','+faststart',OUT/'garden-of-consequences-30s.mp4'])

subtitles=[
 (0,4.2,'Five hundred years ago, Bosch painted a garden overflowing with pleasure.'),
 (4.4,8.3,'You are looking at the same place through another possibility.'),
 (8.3,11.7375,'Is this a punishment, or a consequence we prefer not to see?'),
 (12.2,17.122625,'The garden returns. What you have seen remains part of it, even when it disappears.'),
]
def stamp(t):
    n=round(t*1000);return f'{n//3600000:02d}:{n//60000%60:02d}:{n//1000%60:02d},{n%1000:03d}'
(OUT/'garden-of-consequences-30s.en.srt').write_text('\n\n'.join(f'{i+1}\n{stamp(a)} --> {stamp(b)}\n{text}' for i,(a,b,text) in enumerate(subtitles))+'\n',encoding='utf-8')
(OUT/'edit-decision-list.json').write_text(json.dumps({'source':str(SOURCE),'fps':FPS,'total_frames':900,'duration':30,'canvas':[W,H],'camera_note':'No artificial camera motion or digital zoom added. Original head tracking retained.','segments':segments,'audio':'Original recorded narration excerpts plus user-provided Suno music. Reveal voice shifted under an adjacent interaction excerpt.','subtitle_timing':'Sentence-level boundaries manually estimated after waveform alignment.'},indent=2,ensure_ascii=False),encoding='utf-8')
print('Finished: '+str(OUT/'garden-of-consequences-30s.mp4'),flush=True)
