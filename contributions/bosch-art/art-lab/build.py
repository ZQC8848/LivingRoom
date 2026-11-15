from pathlib import Path
import json

ROOT=Path(__file__).resolve().parent
VIS=Path(r'C:/Users/zoezi/.codex/visualizations/2026/11/14/01a1db35-61bc-73d0-9c2c-3bdd25ec5898')
assets=json.loads((ROOT/'assets.json').read_text(encoding='utf-8'))
missing=[k for k,v in assets.items() if 'src' not in v]
if missing:
    raise SystemExit('Missing artwork: '+', '.join(missing))
fragment=(ROOT/'prototype.fragment.html').read_text(encoding='utf-8')
fragment=fragment.replace('/*__STUDIES__*/',(ROOT/'studies.js').read_text(encoding='utf-8'))
fragment=fragment.replace('/*__ASSETS__*/',json.dumps(assets,ensure_ascii=False,separators=(',',':')))
if len(fragment.encode())>=1_000_000:
    raise SystemExit('Inline source exceeds 1 MB')
VIS.mkdir(parents=True,exist_ok=True)
(VIS/'painting-interaction-lab.html').write_text(fragment,encoding='utf-8')
standalone='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>画外之证 · 14 个互动实验</title><style>html,body{margin:0;background:#151613}body{max-width:1320px;margin:auto}</style>'+fragment+'</html>'
(ROOT/'index.html').write_text(standalone,encoding='utf-8')
manifest={k:{p:q for p,q in v.items() if p!='src'} for k,v in assets.items()}
(ROOT/'sources.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'bytes':len(fragment.encode()),'artworks':len(assets),'inline':str(VIS/'painting-interaction-lab.html'),'browser':str(ROOT/'index.html')},ensure_ascii=False))

gallery=(ROOT/'gallery.fragment.html').read_text(encoding='utf-8')
gallery=gallery.replace('painting-lab','painting-gallery')
gallery=gallery.replace('/*__STUDIES__*/',(ROOT/'studies.js').read_text(encoding='utf-8'))
gallery=gallery.replace('/*__ASSETS__*/',json.dumps(assets,ensure_ascii=False,separators=(',',':')))
if len(gallery.encode())>=1_000_000:
    raise SystemExit('Gallery inline source exceeds 1 MB')
(VIS/'painting-gallery-journey.html').write_text(gallery,encoding='utf-8')
gallery_document='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>画外之证 · 进入画中的画廊</title><style>html,body{margin:0;background:#151613}body{max-width:1320px;margin:auto}</style>'+gallery+'</html>'
(ROOT/'gallery.html').write_text(gallery_document,encoding='utf-8')
print(json.dumps({'gallery_bytes':len(gallery.encode()),'gallery_inline':str(VIS/'painting-gallery-journey.html'),'gallery_browser':str(ROOT/'gallery.html')},ensure_ascii=False))
