#!/usr/bin/env python3
"""SUPERSEDED (2026-11-23): use scripts/web_grain_check.py to check, and hardwood-furniture-cad scripts/web_glb.py
to build furniture GLBs. This script missed merged parts and exempted textures by name.

Check that every wood texture in a GLB is straight grain running along U.

glb_grain_check.py proves the UVs lay the texture along each part, but a texture can still be
flat-sawn figure (cathedrals, swirls, knots), which reads as wavy grain on every part however
well it's mapped. This measures the grain direction at every point of each wood base-colour
image with a structure tensor and fails when the lines wander away from the U axis.

  python3 glb_texture_check.py model.glb [--max-mean 6] [--max-off 0.12] [--out sheet.jpg]
WOOD="(?i)ash|oak" (env) picks the wood materials; default ash|oak|walnut|maple|cherry|wood|ply|birch.
Reports per texture: mean angle of the grain from U (degrees, weighted by how line-like each spot
is) and the share of line-like area more than 15 degrees off U. FAIL when either is over its limit.
Charred or painted materials and end-grain materials (name has "end") are skipped. A material named
as figured on purpose (flat, figure, burl, crotch) is reported but doesn't fail. Look at the --out sheet too.
"""
import argparse, json, os, re, struct, sys, io
import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument('glb'); ap.add_argument('--max-mean', type=float, default=6.0)
ap.add_argument('--max-off', type=float, default=0.12); ap.add_argument('--out')
A = ap.parse_args()
WOOD = re.compile(os.environ.get('WOOD', r'(?i)ash|oak|walnut|maple|cherry|wood|ply|birch'))
raw = open(A.glb, 'rb').read()
assert raw[:4] == b'glTF', 'not a GLB'
off, js, binc = 12, None, b''
while off < len(raw):
    ln, typ = struct.unpack_from('<I4s', raw, off); chunk = raw[off + 8: off + 8 + ln]
    if typ == b'JSON': js = json.loads(chunk)
    elif typ == b'BIN\x00': binc = chunk
    off += 8 + ln
def image(ti):
    src = js['textures'][ti].get('source')
    if src is None:  # EXT_texture_webp etc.
        src = next(iter(js['textures'][ti].get('extensions', {}).values()))['source']
    im = js['images'][src]; bv = js['bufferViews'][im['bufferView']]
    return Image.open(io.BytesIO(binc[bv.get('byteOffset', 0): bv.get('byteOffset', 0) + bv['byteLength']]))
def blur(a, s):
    k = np.exp(-0.5 * (np.arange(-3 * s, 3 * s + 1) / s) ** 2); k /= k.sum()
    a = np.apply_along_axis(lambda r: np.convolve(np.pad(r, 3 * s, mode='wrap'), k, 'valid'), 1, a)
    return np.apply_along_axis(lambda c: np.convolve(np.pad(c, 3 * s, mode='wrap'), k, 'valid'), 0, a)
fails, sheets, seen = 0, [], set()
for m in js.get('materials', []):
    name = m.get('name', '')
    bc = m.get('pbrMetallicRoughness', {}).get('baseColorTexture')
    if not WOOD.search(name) or re.search(r'(?i)char|paint|black|\bend\b|end[_ ]?grain', name): continue
    figured = bool(re.search(r'(?i)flat|figure|burl|crotch', name))
    if not bc: print(f'note {name}: no texture, skipped'); continue
    if bc['index'] in seen: continue
    seen.add(bc['index'])
    im = image(bc['index']).convert('L'); W, H = im.size
    sc = 1024 / max(W, H); im = im.resize((max(8, int(W * sc)), max(8, int(H * sc))), Image.LANCZOS)
    g = np.asarray(im, np.float32) / 255
    gx = (np.roll(g, -1, 1) - np.roll(g, 1, 1)) / 2; gy = (np.roll(g, -1, 0) - np.roll(g, 1, 0)) / 2
    Jxx, Jyy, Jxy = blur(gx * gx, 4), blur(gy * gy, 4), blur(gx * gy, 4)
    # gradient direction is across the grain; the grain runs perpendicular to it
    ang = 0.5 * np.arctan2(2 * Jxy, Jxx - Jyy)          # gradient angle from U
    grain = np.degrees(np.abs(np.abs(ang) - np.pi / 2))   # grain angle from U, 0..90
    lam = np.sqrt((Jxx - Jyy) ** 2 + 4 * Jxy ** 2); coh = lam / (Jxx + Jyy + 1e-9)
    w = coh * (Jxx + Jyy); w = w / (w.sum() + 1e-12)
    mean = float((grain * w).sum()); offshare = float((w * (grain > 15)).sum())
    bad = (mean > A.max_mean or offshare > A.max_off) and not figured
    fails += bad
    print(f'{"FAIL" if bad else ("figd" if figured else "ok  ")} {name}: texture {W}x{H}, grain {mean:.1f} deg from U on average, {offshare*100:.0f}% of the figure more than 15 deg off'
          + ('  (flat-sawn figure or grain across U: use a straight-grain texture with lines along U)' if bad else ''))
    if A.out: sheets.append(im.convert('RGB').resize((1024, 256)))
if A.out and sheets:
    sh = Image.new('RGB', (1024, 256 * len(sheets)), 'white')
    for i, s in enumerate(sheets): sh.paste(s, (0, 256 * i))
    sh.save(A.out, quality=85); print('sheet', A.out)
if not seen: print('no wood textures found')
sys.exit(1 if fails else 0)
