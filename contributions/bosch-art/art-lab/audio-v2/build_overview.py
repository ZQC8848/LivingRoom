from pathlib import Path
import subprocess,numpy as np,imageio_ffmpeg
ROOT=Path(__file__).resolve().parent;LAB=ROOT.parent;PUB=LAB.parent/'deployment/bosch-demo/public';FF=imageio_ffmpeg.get_ffmpeg_exe();RATE=48000
def decode(p):return np.frombuffer(subprocess.run([FF,'-v','error','-i',str(p),'-f','f32le','-ar',str(RATE),'-ac','2','pipe:1'],capture_output=True,check=True).stdout,np.float32).reshape(-1,2).copy()
n=19*RATE;mix=decode(LAB/'audio-v1/delivery/music.mp3')[:n];mix*=.025/max(float(np.sqrt(np.mean(mix*mix))),1e-6)
for cue,start in [('reveal',.6),('mode-garden-light',8.3)]:
 voice=decode(PUB/'audio'/('r5-'+cue+'.mp3'));i=round(start*RATE);end=min(n,i+len(voice));mix[i:end]*=.4;mix[i:end]+=voice[:end-i]*.85
audio=ROOT/'overview-r5.en.mp3';subprocess.run([FF,'-y','-v','error','-f','f32le','-ar',str(RATE),'-ac','2','-i','pipe:0','-c:a','libmp3lame','-b:a','192k',str(audio)],input=mix.astype(np.float32).tobytes(),check=True)
video=LAB.parent/'handoff/garden-daynight-20261114/fast-study/overview-19s-silent.mp4'
subprocess.run([FF,'-y','-v','error','-i',str(video),'-i',str(audio),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-t','19','-movflags','+faststart',str(PUB/'review/overview-19s-r5.mp4')],check=True)
print('Updated 19s review: Lily narration, research included.')
