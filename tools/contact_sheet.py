"""Contact sheet for one orbis_test.py run: reference + first frame + timed snapshots.

    tools/.venv/bin/python tools/contact_sheet.py <test-folder> [<test-folder> ...]

Writes <test-folder>/contact.jpg. Labels come from the frame file names.
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

W, H, BAR = 640, 360, 24


def sheet(test_dir: Path):
    ref = test_dir.parent.parent / "reference.png"
    frames = sorted((test_dir / "frames").glob("*.png"))
    items = [(ref, "reference")] + [(f, f.stem.lstrip("t").replace("-first", " first") + "s") for f in frames]
    items = items[:15]
    cols = 3
    rows = (len(items) + cols - 1) // cols
    out = Image.new("RGB", (W * cols, (H + BAR) * rows), "black")
    d = ImageDraw.Draw(out)
    for i, (path, label) in enumerate(items):
        x, y = (i % cols) * W, (i // cols) * (H + BAR)
        out.paste(Image.open(path).convert("RGB").resize((W, H)), (x, y + BAR))
        d.text((x + 6, y + 5), label, fill="white")
    report = test_dir / "report.json"
    if report.exists():
        r = json.loads(report.read_text())
        title = f"{r.get('model', '')}  passthrough={r.get('passthrough')}"
        d.text((W * cols - 8 - 7 * len(title), 5), title, fill="yellow")
    out.save(test_dir / "contact.jpg", quality=88)
    return test_dir / "contact.jpg"


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        print(sheet(Path(arg)))
