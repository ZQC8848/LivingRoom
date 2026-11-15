from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import base64
import hashlib
import io
import json
import re
import time
import urllib.parse
import urllib.request
from PIL import Image

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'assets'
ASSETS.mkdir(parents=True, exist_ok=True)
FILES = {
    'levi': 'Paolo Veronese 007.jpg',
    'cards': 'Caravaggio (Michelangelo Merisi) - The Cardsharps - Google Art Project.jpg',
    'repin': 'Ilya Repin Unexpected visitors.jpg',
    'bosch': 'GardenED edit3.jpg',
    'spring': 'Guo Xi - Early Spring (large).jpg',
    'meninas': 'Las Meninas (1656), by Velazquez.jpg',
    'ambassadors': 'Holbein-ambassadors.jpg',
    'arnolfini': 'Van Eyck - Arnolfini Portrait.jpg',
    'bayeux': 'BayeuxTapestryScene57.jpg',
    'harvest': 'The Harvesters.jpg',
    'han': "Gu Hongzhong's Night Revels 1 complete scene.jpg",
    'miser': 'Hieronymus Bosch - Death and the Miser - WGA02625.jpg',
}

def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'LivingRoomAcademicPrototype/1.0 (public-domain artwork study)'})
    with urllib.request.urlopen(req, timeout=35) as r:
        return r.read()

def run(item):
    key, filename = item
    target = ASSETS / f'{key}.jpg'
    page = 'https://commons.wikimedia.org/wiki/File:' + urllib.parse.quote(filename.replace(' ', '_'))
    if not target.exists():
        normalized = filename.replace(' ', '_')
        digest = hashlib.md5(normalized.encode()).hexdigest()
        quoted = urllib.parse.quote(normalized)
        base = f'https://upload.wikimedia.org/wikipedia/commons/{digest[0]}/{digest[:2]}/{quoted}'
        urls = [f'https://thumb.wikimedia.org/wikipedia/commons/thumb/{digest[0]}/{digest[:2]}/{quoted}/960px-{quoted}', f'https://upload.wikimedia.org/wikipedia/commons/thumb/{digest[0]}/{digest[:2]}/{quoted}/1280px-{quoted}', base]
        last = None
        for url in urls:
            try:
                raw = get(url)
                image = Image.open(io.BytesIO(raw)).convert('RGB')
                image.thumbnail((1100, 800))
                image.save(target, quality=65, optimize=True)
                break
            except Exception as e:
                last = f'{type(e).__name__}: {str(e)[:100]}'
        else:
            return key, {'error': last, 'file': filename}
    image = Image.open(target)
    preview = image.copy()
    preview.thumbnail((760, 620))
    b = io.BytesIO()
    preview.save(b, format='JPEG', quality=45, optimize=True)
    return key, {'src': 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode(), 'source': page, 'file': filename, 'width': image.width, 'height': image.height}

if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=1) as pool:
        items = dict(pool.map(run, FILES.items()))
    (ROOT / 'assets.json').write_text(json.dumps(items, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: {x:y for x,y in v.items() if x != 'src'} for k,v in items.items()}, ensure_ascii=False, indent=2))
