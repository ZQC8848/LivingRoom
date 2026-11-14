#!/usr/bin/env python3
"""Validate a paired heaven/hell media folder before it goes into the static build.

  python3 tools/check_media.py <media dir> [--quiet]

Checks (exit 1 on any ERROR): both videos exist, H.264 yuv420p, identical size / fps / frame
count / duration, 2:1 aspect, fps <= 30, moov atom up front (+faststart), poster 2:1,
manifest.json parses and agrees with the files. Needs ffprobe.
"""
import json, subprocess, sys, pathlib, hashlib

errors, warns = [], []
def err(m): errors.append(m)
def warn(m): warns.append(m)

def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format", "-of", "json", str(path)],
                         capture_output=True, text=True)
    if out.returncode: err(f"{path.name}: ffprobe failed: {out.stderr.strip()[:200]}"); return None
    return json.loads(out.stdout)

def fps_of(s):
    n, d = s["avg_frame_rate"].split("/"); return float(n) / float(d) if float(d) else 0.0

def faststart(path):
    with open(path, "rb") as f:
        head = f.read(1 << 20)
    moov, mdat = head.find(b"moov"), head.find(b"mdat")
    return moov != -1 and (mdat == -1 or moov < mdat)

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args: print(__doc__); sys.exit(2)
    d = pathlib.Path(args[0]).expanduser()
    man = {}
    mp = d / "manifest.json"
    if not mp.exists(): err("manifest.json missing")
    else:
        try: man = json.loads(mp.read_text())
        except Exception as e: err(f"manifest.json invalid: {e}")
    files = {"heaven": "heaven.mp4", "hell": "hell.mp4", "poster": "poster.jpg", **man.get("files", {})}
    info = {}
    for k in ("heaven", "hell"):
        p = d / files[k]
        if not p.exists(): err(f"{files[k]} missing"); continue
        pr = probe(p)
        if not pr: continue
        v = next((s for s in pr["streams"] if s["codec_type"] == "video"), None)
        if not v: err(f"{p.name}: no video stream"); continue
        if v["codec_name"] != "h264": err(f"{p.name}: codec {v['codec_name']} (need h264)")
        if v.get("pix_fmt") != "yuv420p": err(f"{p.name}: pix_fmt {v.get('pix_fmt')} (need yuv420p)")
        if v.get("profile") not in ("High", "Main", "Constrained Baseline", "Baseline"): warn(f"{p.name}: profile {v.get('profile')}")
        w, h = v["width"], v["height"]
        if w != 2 * h: err(f"{p.name}: {w}x{h} is not 2:1")
        fps = fps_of(v)
        if fps > 30.01: err(f"{p.name}: {fps:.2f} fps > 30")
        if v.get("r_frame_rate") != v.get("avg_frame_rate"): warn(f"{p.name}: variable frame rate? r={v.get('r_frame_rate')} avg={v.get('avg_frame_rate')}")
        n = int(v.get("nb_read_frames") or 0)
        dur = float(pr["format"]["duration"])
        if any(s["codec_type"] == "audio" for s in pr["streams"]): warn(f"{p.name}: has an audio track (the page plays muted)")
        if not faststart(p): err(f"{p.name}: moov atom not at the front (re-mux with -movflags +faststart)")
        mb = p.stat().st_size / 1e6
        if mb > 40: warn(f"{p.name}: {mb:.1f} MB (> 40 MB)")
        if not (5.0 <= dur <= 12.0): warn(f"{p.name}: duration {dur:.2f}s outside 5-12 s")
        info[k] = dict(w=w, h=h, fps=round(fps, 3), frames=n, dur=round(dur, 3), mb=round(mb, 1), sha256=hashlib.sha256(p.read_bytes()).hexdigest()[:16],
                       color=f"{v.get('color_space')}/{v.get('color_range')}", bitrate_mbps=round(int(pr['format'].get('bit_rate', 0)) / 1e6, 1))
    if len(info) == 2:
        a, b = info["heaven"], info["hell"]
        for f in ("w", "h", "fps", "frames"):
            if a[f] != b[f]: err(f"heaven/hell {f} differ: {a[f]} vs {b[f]}")
        if abs(a["dur"] - b["dur"]) > 0.02: err(f"heaven/hell duration differ: {a['dur']} vs {b['dur']}")
        if a["color"] != b["color"]: warn(f"colour tags differ: {a['color']} vs {b['color']}")
        if man.get("fps") and abs(man["fps"] - a["fps"]) > 0.01: err(f"manifest fps {man['fps']} != video {a['fps']}")
        if man.get("frames") and man["frames"] != a["frames"]: err(f"manifest frames {man['frames']} != video {a['frames']}")
    pp = d / files["poster"]
    if not pp.exists(): err(f"{files['poster']} missing")
    else:
        pr = probe(pp)
        if pr:
            s = pr["streams"][0]
            if s["width"] != 2 * s["height"]: err(f"poster {s['width']}x{s['height']} is not 2:1")
            if "heaven" in info and (s["width"], s["height"]) != (info["heaven"]["w"], info["heaven"]["h"]): warn(f"poster is {s['width']}x{s['height']}, video {info['heaven']['w']}x{info['heaven']['h']} (it is rescaled on screen)")
    if "--quiet" not in sys.argv:
        print(json.dumps(info, indent=1))
    for w in warns: print("WARN ", w)
    for e in errors: print("ERROR", e)
    print("media check:", "FAILED" if errors else "ok")
    sys.exit(1 if errors else 0)
main()
