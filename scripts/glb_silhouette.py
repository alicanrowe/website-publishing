"""Front-elevation silhouettes of a web GLB (Y up, metres) for inline SVG dimension drawings (inline-layout.md).
Reads a meshopt/quantized lite GLB (decodes with gltf-transform), rasterises the triangles and traces outlines in mm.
Used for the jewelry collection page: four pieces per motif drawn side by side at one scale.
silhouette(glb, one=False) -> dict(w,h,d mm, paths metal/stone in mm, origin top-left).
"""
import os, subprocess, hashlib, json
import numpy as np, trimesh
from PIL import Image, ImageDraw
from skimage import measure

CACHE = os.path.join(__import__("tempfile").gettempdir(), "glb_silhouette"); os.makedirs(CACHE, exist_ok=True)
PX = 0.04  # mm per raster pixel


def _plain(glb):
    h = hashlib.md5(open(glb, "rb").read()).hexdigest()[:12]
    out = f"{CACHE}/{h}.glb"
    if not os.path.exists(out):
        cli = ["npx", "-y", "@gltf-transform/cli@4.1.1"]
        subprocess.run(cli + ["copy", glb, out + ".a.glb"], check=True, capture_output=True)
        subprocess.run(cli + ["dequantize", out + ".a.glb", out], check=True, capture_output=True)
        os.remove(out + ".a.glb")
    return out


def _raster(tris, x0, y1, W, H):
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    for t in tris:
        d.polygon([((x - x0) / PX, (y1 - y) / PX) for x, y in t], fill=255)
    return np.array(im) > 127


def _paths(mask):
    m = np.pad(mask, 2).astype(float)
    out = []
    for c in measure.find_contours(m, 0.5):
        c = measure.approximate_polygon(c, 0.7)
        if len(c) < 4: continue
        pts = [((col - 2) * PX, (row - 2) * PX) for row, col in c]
        out.append(pts)
    return out


def silhouette(glb, one=False, face=False):
    """face=True: flat pieces (earrings, pendants, clips) lie in the GLB's XZ plane; draw that face, x right, -z up."""
    s = trimesh.load(_plain(glb))
    metal, stone = [], []
    for g in s.dump():
        v = g.vertices * 1000.0
        if face: v = np.column_stack([v[:, 0], -v[:, 2], v[:, 1]])
        (stone if "stone" in str(g.metadata.get("name", "")) else metal).append(v[g.faces][:, :, :2] * [1, 1])
        if "stone" not in str(g.metadata.get("name", "")):
            zr = (v[:, 2].min(), v[:, 2].max())
    M = np.concatenate(metal)
    lo, hi = M.reshape(-1, 2).min(0) - 3, M.reshape(-1, 2).max(0) + 3
    # GPU-instanced stones (gltf-transform 'instance') load mis-placed in trimesh: keep only stones inside the metal's box
    stone = [t for t in stone if (t.reshape(-1, 2).min(0) >= lo).all() and (t.reshape(-1, 2).max(0) <= hi).all()]
    S = np.concatenate(stone) if stone else np.zeros((0, 3, 2))
    allp = np.concatenate([M.reshape(-1, 2), S.reshape(-1, 2)])
    x0, y0 = allp.min(0) - 0.2; x1, y1 = allp.max(0) + 0.2
    W, H = int((x1 - x0) / PX) + 1, int((y1 - y0) / PX) + 1
    mm = _raster(M, x0, y1, W, H); sm = _raster(S, x0, y1, W, H) if len(S) else np.zeros_like(mm)
    if one:  # earring pair: keep the left one
        lab = measure.label(mm | sm)
        keep = np.zeros_like(mm)
        for r in measure.regionprops(lab):
            if r.centroid[1] < W / 2: keep |= lab == r.label
        mm &= keep; sm &= keep
    full = mm | sm
    rows, cols = np.where(full)
    r0, r1, c0, c1 = rows.min(), rows.max() + 1, cols.min(), cols.max() + 1
    mm, sm = mm[r0:r1, c0:c1], sm[r0:r1, c0:c1]
    depth = zr[1] - zr[0]
    return dict(w=round((c1 - c0) * PX, 1), h=round((r1 - r0) * PX, 1), d=round(depth, 1),
                metal=_paths(mm), stone=_paths(sm) if sm.any() else [])


if __name__ == "__main__":
    import sys
    r = silhouette(sys.argv[1], one="ear" in sys.argv[1])
    print(r["w"], r["h"], r["d"], len(r["metal"]), len(r["stone"]), sum(len(p) for p in r["metal"]))
