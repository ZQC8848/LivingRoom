"""Export authored project work; omit credentials, installed dependencies and regenerable frame caches."""
from pathlib import Path
import os, shutil, re, json, hashlib
ROOT=Path(__file__).resolve().parent.parent
REPO=ROOT/'LivingRoom-delivery'
DEST=REPO/'contributions/bosch-art'
DEST.mkdir(parents=True,exist_ok=True)
SKIP_DIR={'.git','node_modules','.venv-orbis','.venv','venv','__pycache__','.a2a','.sites-runtime','.openai-runtime','.vite','dist','npm-cache','_cacache'}
SKIP_EXT={'.pyc','.pyd','.npz','.npy','.exe','.dll','.pem','.key','.p12','.pfx','.log','.pid','.tmp','.bak'}
selected=['art-lab','audio','ConceptEditforME','LivingRoom-concept-review','LivingRoom-sphere-review','handoff','tools']
excluded={};copied=[]
def omit(reason):excluded[reason]=excluded.get(reason,0)+1
def copy_file(src,relative):
    name=src.name.lower()
    if (name.startswith('.env') and name!='.env.example') or src.suffix.lower() in SKIP_EXT or src.is_symlink():omit('secrets, runtime files or generated numerical caches');return
    if re.fullmatch(r'\d{4,}(?:[-_]\d+)?\.(jpg|jpeg|png)',name):omit('regenerable numbered frame images');return
    if name.endswith('.ffconcat'):omit('local absolute frame-cache playlists');return
    target=DEST/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target);copied.append(str(relative).replace('\\','/'))
def tree(src,relative):
    for folder,dirs,names in os.walk(src):
        keep=[]
        for name in dirs:
            if name in SKIP_DIR or name=='frames' or name.endswith('-frames'):omit('installed dependencies, runtime state or frame directories')
            else:keep.append(name)
        dirs[:]=keep
        for name in names:
            p=Path(folder)/name;copy_file(p,relative/p.relative_to(src))
for top in selected:tree(ROOT/top,Path(top))
tree(ROOT/'deployment/bosch-demo',Path('deployment/bosch-demo'))
tree(ROOT/'deployment/review',Path('deployment/review'))
for p in (ROOT/'deployment').iterdir():
    if p.is_file() and p.suffix in {'.json','.md'}:copy_file(p,Path('deployment')/p.name)
visual=Path(r'C:/Users/zoezi/.codex/visualizations/2026/11/14/01a1db35-61bc-73d0-9c2c-3bdd25ec5898')
for p in visual.glob('*.html'):copy_file(p,Path('conversation-previews')/p.name)
summary={'files':len(copied),'bytes':sum((DEST/p).stat().st_size for p in copied),'export_root':'contributions/bosch-art','source_public_site_commit':'3c6a986025292f807773d50878eb442b0fc3d269','exclusions':excluded,'scope':'Authored prototypes, source art, concepts/deck, final and historical video/audio deliverables, production scripts, research, manifests and QA evidence. Excludes unrelated Raven starter, upstream duplicate clones, chat/session exports, installed dependencies, local tokens and frame/numerical caches.'}
(DEST/'EXPORT-REPORT.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
