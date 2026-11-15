"""30s 9:16 revision: 20s artwork + 10s live study, all picture/voice at 1x."""
from pathlib import Path
import subprocess, json
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output';WORK=ROOT/'work/submission-r2';WORK.mkdir(parents=True,exist_ok=True)
SOURCE=ROOT/'source/Casting_Video_1794721792334.mp4'
FF=imageio_ffmpeg.get_ffmpeg_exe();FONTS=Path('C:/Windows/Fonts')
NAME='garden-of-consequences-30s-portrait-r2'
def run(args):
    r=subprocess.run([FF,'-hide_banner','-loglevel','error','-y',*map(str,args)],capture_output=True,text=True)
    if r.returncode:raise RuntimeError(r.stderr[-6000:])
def font(size,bold=False):return ImageFont.truetype(str(FONTS/('segoeuib.ttf' if bold else 'segoeui.ttf')),size)
def timestamp(t):
    n=round(t*1000);return f'{n//3600000:02d}:{n//60000%60:02d}:{n//1000%60:02d},{n%1000:03d}'

segments=[
 dict(id='intro',source_start=4.498,source_duration=4.2,frames=126),
 dict(id='reveal',source_start=14.6,source_duration=8,frames=240),
 dict(id='return',source_start=23.428625,source_duration=5,frames=150),
 dict(id='garden-daynight',source_start=31.8,source_duration=2.8,frames=84,label='Garden · Day / Night',note='Prepared loop excerpt · 1×'),
 dict(id='meadow',source_start=89.6,source_duration=1.5,frames=45,crop=[350,0,468,832],label='Live Lab · Starting meadow',note='Recorded excerpts · 1× · waits omitted'),
 dict(id='aurora',source_start=113,source_duration=3.5,frames=105,crop=[400,0,468,832],label='Live Lab · Aurora',note='Recorded excerpts · 1× · waits omitted'),
 dict(id='asteroids',source_start=130.2,source_duration=3,frames=90,crop=[268,0,810,1440],label='Live Lab · Asteroids',note='Recorded excerpts · 1× · waits omitted'),
 dict(id='snow',source_start=149.4,source_duration=2,frames=60,crop=[350,0,594,1056],label='Live Lab · Return to snow',note='Recorded excerpts · 1× · waits omitted'),
]
brief=[
 dict(start=0,end=7,heading='THE GARDEN OF CONSEQUENCES / BACKGROUND',lines=[
  'Hieronymus Bosch’s The Garden',
  'of Earthly Delights (c. 1500) is a',
  'Northern Renaissance masterpiece,',
  'now in Madrid’s Prado Museum.']),
 dict(start=7,end=12.2,heading='THE INTERACTION',lines=[
  'With a gesture, visitors reveal image layers',
  'and discover another side of the painting.']),
 dict(start=12.2,end=20,heading='THE PAINTING WORKFLOW',y=185,lines=[
  'Creators author panoramas, masks and layers.',
  'Live AI adds environmental change',
  'only within selected regions.']),
]
for i,b in enumerate(brief):
    im=Image.new('RGBA',(1080,1920));d=ImageDraw.Draw(im);y=b.get('y',78)
    body=font(39)
    for line in b['lines']:assert d.textbbox((0,0),line,font=body)[2]<940,line
    d.rounded_rectangle((42,y,1038,y+83+54*len(b['lines'])),radius=14,fill=(8,13,16,236))
    heading_font=font(23,True);box=d.textbbox((0,0),b['heading'],font=heading_font)
    d.text((540-(box[2]+box[0])/2,y+24),b['heading'],font=heading_font,fill='#d4bd86')
    for j,line in enumerate(b['lines']):
        box=d.textbbox((0,0),line,font=body)
        d.text((540-(box[2]+box[0])/2,y+68+54*j),line,font=body,fill='#f6f2e8')
    im.save(WORK/f'brief-{i}.png')

cursor=0
for i,s in enumerate(segments):
    s['output_start']=cursor;s['output_duration']=s['frames']/30
    s['speed']=s['source_duration']/s['output_duration'];cursor+=s['output_duration']
    assert abs(s['speed']-1)<1e-9
    s.setdefault('crop',[221,0,810,1440])
    x,y,w,h=s['crop']
    args=['-ss',s['source_start'],'-t',s['source_duration']+.15,'-i',SOURCE]
    graph=[f'[0:v]setpts=PTS-STARTPTS,fps=30,crop={w}:{h}:{x}:{y},scale=1080:1920:flags=lanczos,setsar=1[v0]']
    current='v0';inputs=0
    if s.get('label'):
        im=Image.new('RGBA',(1080,1920));d=ImageDraw.Draw(im)
        for j,(line,size) in enumerate([(s['label'],36),(s['note'],27)]):
            f=font(size,j==0);box=d.textbbox((0,0),line,font=f);w=box[2];y=66+j*59
            d.rounded_rectangle((540-w/2-18,y-5,540+w/2+18,y+size+17),radius=9,fill=(8,13,16,222))
            d.text((540-(box[2]+box[0])/2,y),line,font=f,fill='#f5f1e7')
        path=WORK/f'{s["id"]}-label.png';im.save(path)
        args+=['-loop','1','-framerate','30','-i',path];inputs+=1
        graph.append(f'[{current}][{inputs}:v]overlay=0:0[v{inputs}]');current=f'v{inputs}'
    for j,b in enumerate(brief):
        a=max(0,b['start']-s['output_start']);z=min(s['output_duration'],b['end']-s['output_start'])
        if z<=a:continue
        args+=['-loop','1','-framerate','30','-i',WORK/f'brief-{j}.png'];inputs+=1
        graph.append(f'[{current}][{inputs}:v]overlay=0:0:enable=\'gte(t,{a})*lt(t,{z})\'[v{inputs}]');current=f'v{inputs}'
    graph.append(f'[{current}]format=yuv420p[out]')
    run([*args,'-filter_complex',';'.join(graph),'-map','[out]','-an','-frames:v',s['frames'],'-c:v','libx264','-crf','18','-preset','fast','-color_range','tv','-colorspace','bt709',WORK/f'{i:02d}.mp4'])
    print(f'Rendered {s["id"]}: {s["output_duration"]:.2f}s',flush=True)
assert sum(s['frames'] for s in segments)==900
concat=WORK/'concat.txt';concat.write_text('\n'.join(f"file '{(WORK/f'{i:02d}.mp4').as_posix()}'" for i in range(len(segments))),encoding='utf-8')
run(['-f','concat','-safe','0','-i',concat,'-c','copy',WORK/'picture.mp4'])
music=ROOT.parent/'deployment/bosch-demo/public/audio/music.mp3'
audio=(
 '[0:a]atrim=start=4.498:duration=4.2,asetpts=PTS-STARTPTS,afade=t=out:st=4.1:d=0.1[a0];'
 '[0:a]atrim=start=15.962:duration=7.3375,asetpts=PTS-STARTPTS,afade=t=in:d=0.025,afade=t=out:st=7.23:d=0.1,adelay=4400|4400[a1];'
 '[0:a]atrim=start=23.428625:duration=4.922625,asetpts=PTS-STARTPTS,afade=t=in:d=0.025,afade=t=out:st=4.82:d=0.1,adelay=12200|12200[a2];'
 '[1:a]atrim=start=12:duration=30,asetpts=PTS-STARTPTS,volume=\'if(lt(t,17.2),0.13,0.13+0.37*min((t-17.2)/0.5,1))\':eval=frame,afade=t=in:d=0.25,afade=t=out:st=29:d=1[bed];'
 '[a0][a1][a2][bed]amix=inputs=4:duration=longest:normalize=0,volume=5.5dB,alimiter=limit=0.89:level=false,apad=whole_dur=30,atrim=duration=30[out]')
run(['-i',SOURCE,'-i',music,'-filter_complex',audio,'-map','[out]','-ar','48000','-ac','2','-c:a','pcm_s16le',WORK/'mix.wav'])
run(['-i',WORK/'picture.mp4','-i',WORK/'mix.wav','-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-b:a','192k','-t','30','-movflags','+faststart',OUT/f'{NAME}.mp4'])
subtitles=[
 (0,4.2,'Five hundred years ago, Bosch painted a garden overflowing with pleasure.'),
 (4.4,8.3,'You are looking at the same place through another possibility.'),
 (8.3,11.7375,'Is this a punishment, or a consequence we prefer not to see?'),
 (12.2,17.122625,'The garden returns. What you have seen remains part of it, even when it disappears.'),
]
def srt(cues):return '\n\n'.join(f'{i+1}\n{timestamp(a)} --> {timestamp(z)}\n{text}' for i,(a,z,text) in enumerate(cues))+'\n'
(OUT/f'{NAME}.en.srt').write_text(srt(subtitles),encoding='utf-8')
(OUT/'background-brief.en.srt').write_text(srt([(b['start'],b['end'],' '.join(b['lines'])) for b in brief]),encoding='utf-8')
edl={'source':'source/Casting_Video_1794721792334.mp4','canvas':[1080,1920],'fps':30,'total_frames':900,'duration':30,'artwork_seconds':20,'live_study_seconds':10,'segments':segments,'background_brief':brief,'narration':'All recorded voice excerpts at original speed. No atempo, no new voiceover.','real_time_disclosure':'Four live-study excerpts at 1x, with menu actions omitted and fixed per-shot crops excluding UI. Starting meadow is the stopped baseline, not live generation. No latency measurement.','camera_note':'Fixed crop within each shot. The painting crop is aligned to the original narration-panel center; brief text and boxes are horizontally centered. Meadow, aurora and snow have tighter static crops to exclude baked-in menus. No synthetic camera movement or interpolated frames.'}
(OUT/'edit-decision-list-r2.json').write_text(json.dumps(edl,indent=2,ensure_ascii=False),encoding='utf-8')
print('Finished '+str(OUT/f'{NAME}.mp4'),flush=True)
