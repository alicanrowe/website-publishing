#!/usr/bin/env python3
"""Background check: every image that goes out (site images, teasers, sheets) sits on white unless the owner
asked for another background.

    python3 check_image_backgrounds.py <image or dir> [...]          # check these images (dirs: every jpg/png in them)
    python3 check_image_backgrounds.py --changed <repo>              # every image added or changed vs origin/main
    python3 check_image_backgrounds.py --allow <name> ...            # image names (substring) that were asked to be dark

Why: renders come out of Blender as transparent PNGs (film_transparent). Any step that opens one with a plain
.convert("RGB") or saves it as JPEG drops the alpha and leaves the black under it, so the picture lands on black.
That shipped all 24 Dancers on black once (Nov 2026), even though the lesson was already written down.
Flatten with on_white() below (this file) and run this check before anything is published.

Rule per image:
  - opaque: FAIL when 3 or 4 of the corner patches are dark (mean < 90): a black background. A rail or cable
    crossing one or two corners of a close-up is fine. WARN when 3+ corners are mid grey (< 200).
  - transparent (alpha in a corner): OK as a render source, but FAIL with --opaque (it is about to be published
    as is, and many viewers and every JPEG export show transparent as black).
Exit code 1 on any FAIL.
"""
import sys, subprocess
from pathlib import Path
from PIL import Image

EXT = {".jpg", ".jpeg", ".png", ".webp"}
px = lambda im: im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata()


def on_white(p):
    """Open an image flattened onto white (the one safe way to turn a transparent render into RGB)."""
    im = Image.open(p)
    if im.mode in ("RGBA", "LA", "P", "PA"):
        im = im.convert("RGBA"); W = Image.new("RGBA", im.size, (255, 255, 255, 255)); W.alpha_composite(im); im = W
    return im.convert("RGB")


def corners(im, k):
    w, h = im.size
    return [(0, 0, k, k), (w - k, 0, w, k), (0, h - k, k, h), (w - k, h - k, w, h)]


def check(p, opaque=False):
    im = Image.open(p); w, h = im.size; k = max(8, min(w, h) // 25)
    if im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info):
        a = im.convert("RGBA").split()[3]
        clear = sum(sum(px(a.crop(b))) / (k * k) < 128 for b in corners(a, k))
        if clear:
            return ("FAIL" if opaque else "OK", f"transparent background ({clear} of 4 corners clear)"
                    + ("; flatten onto white before publishing" if opaque else "; flatten with on_white() before export"))
    L = im.convert("RGB").convert("L")
    m = [sum(px(L.crop(b))) / (k * k) for b in corners(L, k)]
    dark, grey = sum(v < 90 for v in m), sum(v < 200 for v in m)
    if dark >= 3:
        return "FAIL", f"black background: {dark} of 4 corners dark (corner means {', '.join(f'{v:.0f}' for v in m)})"
    if grey >= 3:
        return "WARN", f"grey background: {grey} of 4 corners below 200 (white unless the owner asked otherwise)"
    return "OK", "white"


def changed(repo):
    out = subprocess.run(["git", "-C", repo, "diff", "--name-only", "--diff-filter=AM", "origin/main...HEAD"],
                         capture_output=True, text=True).stdout.split()
    out += subprocess.run(["git", "-C", repo, "ls-files", "--others", "--exclude-standard", "-m"],
                          capture_output=True, text=True).stdout.split()
    return [Path(repo) / f for f in sorted(set(out)) if Path(f).suffix.lower() in EXT and (Path(repo) / f).exists()]


def main(argv):
    allow, opaque, files, i = [], False, [], 0
    while i < len(argv):
        a = argv[i]
        if a == "--allow": allow.append(argv[i + 1]); i += 2; continue
        if a == "--opaque": opaque = True; i += 1; continue
        if a == "--changed": files += changed(argv[i + 1]); opaque = True; i += 2; continue
        p = Path(a)
        files += sorted(q for q in p.rglob("*") if q.suffix.lower() in EXT) if p.is_dir() else [p]
        i += 1
    fails = 0
    for f in files:
        try:
            st, msg = check(f, opaque)
        except Exception as e:
            st, msg = "FAIL", f"not a readable image ({e.__class__.__name__}): a 404 page or broken download?"
        if st == "FAIL" and any(s in f.name for s in allow): st, msg = "OK", msg + " (allowed: asked for)"
        fails += st == "FAIL"
        if st != "OK" or len(files) <= 40: print(f"  {st:4s}  {f}: {msg}")
    print(f"{len(files)} images, {fails} FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
