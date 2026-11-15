"""Suno music + ElevenLabs speech + explicitly authored environmental synthesis.

The user's Suno download allowance is exhausted. Never label synthesized beds as
Suno/ElevenLabs output. One source music clock feeds two tonal perspectives.
"""
from pathlib import Path
import hashlib,json,math,re,subprocess,wave
import numpy as np
import imageio_ffmpeg
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'delivery';OUT.mkdir(exist_ok=True)
FF=imageio_ffmpeg.get_ffmpeg_exe();SR=48000
def run(args):
 p=subprocess.run([FF,'-y',*args],capture_output=True)
 if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace')[-1300:])
 return p
def decode(path):
 p=run(['-i',str(path),'-vn','-ac','2','-ar',str(SR),'-f','f32le','pipe:1'])
 return np.frombuffer(p.stdout,np.float32).reshape(-1,2).copy()
def wav(path,data):
 with wave.open(str(path),'wb') as f:
  f.setnchannels(2);f.setsampwidth(2);f.setframerate(SR);f.writeframes(np.int16(np.clip(data,-.999,.999)*32767).tobytes())
def loop(data,seconds=1):
 n=min(int(SR*seconds),len(data)//4);theta=np.linspace(0,np.pi/2,n)[:,None]
 blend=data[-n:]*np.cos(theta)+data[:n]*np.sin(theta)
 return np.concatenate([data[n:-n],blend],axis=0).astype(np.float32)
def noise(seconds,rng,low,high,slope=0):
 n=int(SR*seconds);freq=np.fft.rfftfreq(n,1/SR)
 spec=rng.normal(size=len(freq))+1j*rng.normal(size=len(freq))
 filt=(1-np.exp(-(freq/max(low,1))**4))*np.exp(-(freq/high)**4)
 filt*=np.maximum(freq,low)**(-slope)
 arr=np.fft.irfft(spec*filt,n=n);arr/=np.std(arr)+1e-9
 return arr.astype(np.float32)
def synth(kind):
 seconds=24;rng=np.random.default_rng(920 if kind=='garden' else 1211);n=int(SR*seconds);t=np.arange(n)/SR
 out=np.zeros((n,2),np.float32)
 for c in range(2):
  if kind=='garden':
   water=noise(seconds,rng,170,5300,.32);mod=.045+.012*np.sin(2*np.pi*.17*t+c)+.008*np.sin(2*np.pi*.43*t+c*.3)
   wind=noise(seconds,rng,80,1300,.25)*(.009+.004*np.sin(2*np.pi*.09*t+c))
   out[:,c]=water*mod+wind
  else:
   hiss=noise(seconds,rng,220,5800,.3)*(.017+.007*np.sin(2*np.pi*.13*t+c))
   wind=noise(seconds,rng,65,900,.6)*(.013+.006*np.sin(2*np.pi*.08*t+c))
   rumble=noise(seconds,rng,38,165,.15)*.009
   out[:,c]=hiss+wind+rumble
 if kind=='garden':
  # Damped, falling-resonance bubbles with irregular spatial distribution.
  for _ in range(180):
   start=int(rng.uniform(0,seconds-.12)*SR);length=int(rng.uniform(.022,.095)*SR);u=np.arange(length)/SR
   f0=rng.uniform(650,2600);phase=2*np.pi*f0*(u-.30*u*u/max(u[-1],.001));env=np.exp(-u/rng.uniform(.008,.022))
   sound=np.sin(phase)*env*rng.uniform(.005,.018);pan=rng.uniform(.15,.85)
   out[start:start+length,0]+=sound*np.sqrt(1-pan);out[start:start+length,1]+=sound*np.sqrt(pan)
  for start,pan in [(4.1,.18),(16.4,.82)]:
   for j in range(2):
    length=int(.105*SR);u=np.arange(length)/SR;f0=2100+j*500
    chirp=np.sin(2*np.pi*(f0*u+900*u*u/.21))*np.sin(np.pi*u/.105)**2*.008
    pos=int((start+j*.18)*SR);out[pos:pos+length,0]+=chirp*np.sqrt(1-pan);out[pos:pos+length,1]+=chirp*np.sqrt(pan)
 else:
  # Soft aperiodic ember crackles, filtered and limited instead of sharp clicks.
  for _ in range(105):
   start=int(rng.uniform(0,seconds-.15)*SR);length=int(rng.uniform(.018,.11)*SR);u=np.arange(length)/SR
   sound=rng.normal(size=length).astype(np.float32);sound=np.convolve(sound,np.array([.15,.30,.30,.15]),mode='same')
   sound*=np.exp(-u/rng.uniform(.009,.031))*(1-np.exp(-u/.002))*rng.uniform(.012,.045)
   pan=rng.uniform(.05,.95);out[start:start+length,0]+=sound*np.sqrt(1-pan);out[start:start+length,1]+=sound*np.sqrt(pan)
 return loop(out,2)
def normalize(source,target,lufs):
 measure=run(['-i',str(source),'-af',f'loudnorm=I={lufs}:TP=-3:LRA=8:print_format=json','-f','null','-'])
 logs=measure.stderr.decode(errors='replace');info=json.loads(re.findall(r'\{\s*"input_i".*?\}',logs,re.S)[-1])
 filt=f'loudnorm=I={lufs}:TP=-3:LRA=8:measured_I={info["input_i"]}:measured_TP={info["input_tp"]}:measured_LRA={info["input_lra"]}:measured_thresh={info["input_thresh"]}:offset={info["target_offset"]}:linear=true'
 run(['-i',str(source),'-vn','-af',filt,'-ar',str(SR),'-ac','2','-c:a','libmp3lame','-b:a','128k',str(target)])
 pcm=decode(target)
 return {'seconds':len(pcm)/SR,'peak_dbfs':float(20*np.log10(max(1e-9,np.abs(pcm).max()))),'target_lufs':lufs,'decoded_all_finite':bool(np.isfinite(pcm).all()),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}

workspace=ROOT.parents[1];source=workspace/'audio/A Garden Without a Price.m4a'
if not source.exists():source=workspace/'audio/A Garden Without a Price.mp3'
music=decode(source);music=loop(music,4);wav(ROOT/'music-loop.wav',music)
for kind in ['garden','hell']:wav(ROOT/f'{kind}-authored.wav',synth(kind))
metadata={}
for name,src,lufs in [('music',ROOT/'music-loop.wav',-22),('garden-ambience',ROOT/'garden-authored.wav',-25),('hell-ambience',ROOT/'hell-authored.wav',-25),('arrival',ROOT/'arrival.mp3',-18),('reveal',ROOT/'reveal.mp3',-18),('return',ROOT/'return.mp3',-18)]:
 metadata[name]=normalize(src,OUT/f'{name}.mp3',lufs);print('Prepared',name,round(metadata[name]['seconds'],2),'s',flush=True)
narration=json.loads((ROOT/'narration.json').read_text())
for n in narration:n.update(file=n['id']+'.mp3',seconds=metadata[n['id']]['seconds'])
manifest={'schema_version':1,'release':'2026-11-14-r4','language':'en','music':{'file':'music.mp3','title':'A Garden Without a Price','provider':'Suno','source':'User-exported original music; one continuous source feeds bright and dark filter branches.','loop_crossfade_seconds':4},'ambience':{'garden':{'file':'garden-ambience.mp3','provider':'Authored procedural sound design','description':'Falling fountain water, sparse distant chirps and light wind'},'hell':{'file':'hell-ambience.mp3','provider':'Authored procedural sound design','description':'Quiet ember crackles, low wind and hollow resonance'}},'narration':narration,'voice':{'provider':'ElevenLabs','stock_voice':'George - Warm, Captivating Storyteller','model':'eleven_multilingual_v2','no_voice_cloning':True},'attribution':'Music created in Suno. Narration generated with ElevenLabs. Environmental beds synthesized specifically for this prototype.','audio_assets':metadata,'key_present':False,'notes':'One continuous score, independently looping authored environmental beds, and once-per-encounter English narration.'}
(OUT/'manifest-r4.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
for f in ['transcript.en.md']: (OUT/f).write_text((ROOT/f).read_text(encoding='utf-8'),encoding='utf-8')
print('Audio prepared; no API credentials copied.',flush=True)
