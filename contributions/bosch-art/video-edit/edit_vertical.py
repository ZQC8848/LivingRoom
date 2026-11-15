"""Full-screen 9:16 revision: fixed crop of the original recording, no side panel."""
from pathlib import Path
import json, subprocess, shutil
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent
WORK = ROOT/'work/vertical'
OUT = ROOT/'output'
WORK.mkdir(parents=True, exist_ok=True)
FF = imageio_ffmpeg.get_ffmpeg_exe()
edl = json.loads((OUT/'edit-decision-list.json').read_text(encoding='utf-8'))
source = ROOT/'source/Casting_Video_1794721792334.mp4'
fonts = Path('C:/Windows/Fonts')
def run(args):
    r = subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', *map(str,args)], capture_output=True, text=True)
    if r.returncode: raise RuntimeError(r.stderr[-4000:])

labels = {
 'intro': ('THE GARDEN OF CONSEQUENCES', 'After Hieronymus Bosch · c. 1500', 'The Garden of Earthly Delights · Prado, Madrid'),
 'garden-daynight': ('Garden · Day / Night', 'Prepared loop · 3× playback'),
 'hell-daynight': ('Aftermath · Day / Night', 'Prepared loop · 3× playback'),
 'garden-seasons': ('Garden · Seasons', 'Prepared loop · 3× playback'),
 'hell-seasons': ('Aftermath · Seasons', 'Prepared loop · 3× playback'),
 'live': ('Live Lab · Orbis Dynamic', 'Recorded session · 1×'),
}
segments = edl['segments']
for i,s in enumerate(segments):
    # Keep the central 810 x 1440 pixels: exactly 9:16. No moving crop.
    vf = f'setpts=(PTS-STARTPTS)/{s["speed"]},fps=30,crop=810:1440:268:0,scale=1080:1920:flags=lanczos,setsar=1'
    args = ['-ss',s['start'],'-t',s['frames']/30*s['speed']+.25,'-i',source]
    if s['id'] in labels:
        lines = labels[s['id']]
        overlay = Image.new('RGBA',(1080,1920));d=ImageDraw.Draw(overlay)
        sizes = [36,30,28] if s['id']=='intro' else [38,29]
        y=79
        for j,line in enumerate(lines):
            f=ImageFont.truetype(str(fonts/('segoeuib.ttf' if j==0 else 'segoeui.ttf')),sizes[j])
            box=d.textbbox((0,0),line,font=f);w=box[2]-box[0]
            x=(1080-w)//2
            d.rounded_rectangle((x-19,y-5,x+w+19,y+sizes[j]+17),radius=9,fill=(12,22,25,185))
            d.text((x,y),line,font=f,fill='#f5f1e7')
            y+=sizes[j]+24
        labelpath=WORK/f"{s['id']}-label.png";overlay.save(labelpath)
        args += ['-loop','1','-framerate','30','-i',labelpath,
                 '-filter_complex',f'[0:v]{vf}[v];[v][1:v]overlay=0:0:shortest=1,format=yuv420p[out]','-map','[out]']
    else:
        args += ['-vf',vf+',format=yuv420p','-map','0:v']
    args += ['-an','-frames:v',s['frames'],'-c:v','libx264','-crf','18','-preset','fast','-color_range','tv','-colorspace','bt709',WORK/f'{i:02d}.mp4']
    run(args)
    print('Rendered vertical '+s['id'],flush=True)

concat=WORK/'concat.txt'
concat.write_text('\n'.join(f"file '{(WORK/f'{i:02d}.mp4').as_posix()}'" for i in range(len(segments))),encoding='utf-8')
run(['-f','concat','-safe','0','-i',concat,'-c','copy',WORK/'picture.mp4'])
audio=ROOT/'work/mix-30s.wav'
audio_args = ['-i',audio] if audio.exists() else ['-i',OUT/'garden-of-consequences-30s.mp4']
run(['-i',WORK/'picture.mp4',*audio_args,'-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-b:a','192k','-t','30','-movflags','+faststart',OUT/'garden-of-consequences-30s-vertical.mp4'])
shutil.copy2(OUT/'garden-of-consequences-30s.en.srt',OUT/'garden-of-consequences-30s-vertical.en.srt')
edl['source']='source/Casting_Video_1794721792334.mp4'
edl['canvas']=[1080,1920]
edl['crop']={'width':810,'height':1440,'x':268,'y':0,'fixed':True}
edl['presentation']='Full-screen 9:16 headset recording; no editorial side panel. Brief artwork credit only at opening, mode/speed labels during optional studies and recorded Live Lab.'
(OUT/'edit-decision-list-vertical.json').write_text(json.dumps(edl,indent=2,ensure_ascii=False),encoding='utf-8')
print('Finished vertical 30-second demo.',flush=True)
