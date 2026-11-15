from pathlib import Path
import json,subprocess,shutil
import numpy as np,imageio_ffmpeg
ROOT=Path(__file__).resolve().parent;LAB=ROOT.parent;OUT=LAB.parent/'handoff/garden-daynight-20261114'
FF=imageio_ffmpeg.get_ffmpeg_exe();RATE=48000;N=RATE*30
def decode(p):
 r=subprocess.run([FF,'-v','error','-i',str(p),'-f','f32le','-ar',str(RATE),'-ac','2','pipe:1'],capture_output=True,check=True)
 return np.frombuffer(r.stdout,np.float32).reshape(-1,2).copy()
def rms(x):return float(np.sqrt(np.mean(x*x)))
def cyclic(x,seconds=30,cross=4):
 total=round((seconds+cross)*RATE);x=np.tile(x,(int(np.ceil(total/len(x))),1))[:total]
 n=round(cross*RATE);a=np.linspace(0,1,n,endpoint=False)[:,None];a=a*a*(3-2*a)
 return np.concatenate([x[n:seconds*RATE],x[seconds*RATE:]* (1-a)+x[:n]*a])
def encode(a,p):
 r=subprocess.run([FF,'-y','-v','error','-f','f32le','-ar',str(RATE),'-ac','2','-i','pipe:0','-c:a','libmp3lame','-b:a','192k',str(p)],input=a.astype(np.float32).tobytes(),capture_output=True)
 if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
music=cyclic(decode(LAB/'audio-v1/delivery/music.mp3'));music*=.032/max(rms(music),1e-6)
amb=cyclic(decode(LAB/'audio-v1/delivery/garden-ambience.mp3'));amb*=.013/max(rms(amb),1e-6)
voice=np.zeros((N,2),np.float32);duck=np.ones(N,np.float32)
script=json.loads((ROOT/'narration/script.en.json').read_text(encoding='utf-8'))
for it in script['lines']:
 a=decode(ROOT/'narration'/(it['id']+'.mp3'));a*=.085/max(rms(a),1e-6)
 n=round(.012*RATE);a[:n]*=np.linspace(0,1,n)[:,None];a[-n:]*=np.linspace(1,0,n)[:,None]
 start=round(it['start_seconds']*RATE);end=min(N,start+len(a));voice[start:end]+=a[:end-start]
 lo=max(0,start-round(.25*RATE));hi=min(N,end+round(.4*RATE));duck[lo:hi]=.43
 it['duration_seconds']=round(len(a)/RATE,3)
 if end>=N:raise ValueError('Narration exceeds loop duration')
kernel=np.ones(4801,np.float32)/4801;duck=np.convolve(np.pad(duck,(2400,2400),mode='edge'),kernel,mode='valid')
bed=music+amb;mix=(bed*duck[:,None]+voice)*.9
peak=float(np.max(np.abs(mix)))
if peak>.95:mix*=.95/peak
encode(bed,OUT/'ambience-music-loop.mp3');encode(mix,OUT/'review-soundtrack.en.mp3')
for it in script['lines']:shutil.copy2(ROOT/'narration'/(it['id']+'.mp3'),OUT/('vo-'+it['id']+'.mp3'))
(OUT/'narration.en.json').write_text(json.dumps(script,indent=2),encoding='utf-8')
shutil.copy2(ROOT/'narration/voice.json',OUT/'voice.json')
r=subprocess.run([FF,'-y','-v','error','-i',str(OUT/'garden-daynight-30s-flat.mp4'),'-i',str(OUT/'review-soundtrack.en.mp3'),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-t','30','-movflags','+faststart',str(OUT/'garden-daynight-review-with-voice.mp4')],capture_output=True)
if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
result={'language':'en','music':'User-exported Suno score, cyclic edit','ambience':'Existing authored garden sound bed','voice':'ElevenLabs George stock voice','narration':script['lines'],'narration_policy':'Review movie includes narration; production proposal plays it once per encounter, not on every visual loop.','production_audio_modified':False}
(OUT/'audio-manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
