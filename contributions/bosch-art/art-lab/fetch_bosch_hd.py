from pathlib import Path
import hashlib
import json
import urllib.parse
import urllib.request
from PIL import Image

ROOT=Path(__file__).resolve().parent/'bosch-hd'
ROOT.mkdir(exist_ok=True)
filename='Jheronimus Bosch 023.jpg'
normalized=filename.replace(' ','_')
digest=hashlib.md5(normalized.encode()).hexdigest()
url=f'https://upload.wikimedia.org/wikipedia/commons/{digest[0]}/{digest[:2]}/{urllib.parse.quote(normalized)}'
target=ROOT/'bosch-master-8533.jpg'
if not target.exists():
    req=urllib.request.Request(url,headers={'User-Agent':'LivingRoomAcademicPrototype/1.0 (public-domain art study)'})
    with urllib.request.urlopen(req,timeout=60) as response,target.open('wb') as out:
        while chunk:=response.read(1024*1024):out.write(chunk)
im=Image.open(target)
small=im.copy();small.thumbnail((1700,1000));small.save(ROOT/'master-inspection.jpg',quality=90)
info={'file':filename,'source':'https://commons.wikimedia.org/wiki/File:Jheronimus_Bosch_023.jpg','download':url,'pixels':list(im.size),'master':str(target),'master_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'rights_status':'Wikimedia Commons labels the artwork reproduction public domain; source page and jurisdiction must be checked for release.','larger_reference':'https://commons.wikimedia.org/wiki/File:The_Garden_of_earthly_delights.jpg'}
(ROOT/'provenance.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(info,ensure_ascii=False))
