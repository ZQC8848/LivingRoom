"""Compile each face's opening Orbis prompt from scenes/<scene>/scene.json.

    tools/.venv/bin/python tools/scene_prompts.py hillside

prompt = camera + scene + motion + look. The prompt guide asks for 1-3 sentences and
under ~100 words; faces over that are flagged. Import compile_prompts() from the relay.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORD_LIMIT = 100
ORDER = ["front", "right", "back", "left", "floor", "ceiling"]


def compile_prompts(scene):
    cfg = json.loads((ROOT / "scenes" / scene / "scene.json").read_text())["orbis"]
    out = {}
    for face in ORDER:
        f = cfg["faces"][face]
        parts = [cfg["camera"][f["camera"]], f["scene"], f["motion"], cfg["look"]]
        out[face] = " ".join(p.strip() for p in parts if p)
    return out


if __name__ == "__main__":
    scene = sys.argv[1] if len(sys.argv) > 1 else "hillside"
    for face, prompt in compile_prompts(scene).items():
        n = len(prompt.split())
        flag = "  <-- over the ~100-word guideline" if n > WORD_LIMIT else ""
        print(f"[{face}] {n} words{flag}\n{prompt}\n")
