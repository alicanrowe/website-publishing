#!/usr/bin/env python3
"""Check the grain of a web viewer GLB, part by part, before it goes on the site.

Fails (exit 1) when any of these is true:
  (a wood mesh holding several separate parts, joined by material, is split and each part checked by
   its own long side; it's noted, because the spec's grain overrides can't reach it)
  across    on a part's long faces the texture's grain (U) doesn't run along the part's grain axis
  end       end-grain material on a long face, or long-grain material on an end face
  figure    a long-grain texture that isn't straight: cathedral, swirl, contour-map figure (no name exemption)
The grain axis of each part comes from, in order: the node's extras "grain_axis" (written by web_glb.py),
the cadcheck spec (--spec, "grain": "x|y|z", model axes Z up), then the part's longest side.

  python3 scripts/web_grain_check.py model.glb [--spec piece.cadcheck.json] [--sheet textures.jpg]
Meshopt/Draco GLBs: decode first, `npx @gltf-transform/cli copy in.glb plain.glb`.
Passing this is necessary, not enough: also look at the site's own viewer from two sides
(website-publishing scripts/shoot.mjs) and at the --sheet.
"""
import argparse, io, json, re, sys
import numpy as np
import trimesh
from PIL import Image

WOOD = re.compile(r'(?i)walnut|oak|ash|maple|cherry|cedar|wood|ply|birch|mahogany|sapele|pine|grain|rift|flat')
END = re.compile(r'(?i)\bend\b|end[ _-]?grain')


def straightness(img):
    """Mean grain angle from U (deg) and share of line-like area >15 deg off, by structure tensor."""
    g = np.asarray(img.convert('L').resize((512, max(8, int(512 * img.size[1] / img.size[0])))), np.float32) / 255
    gx = (np.roll(g, -1, 1) - np.roll(g, 1, 1)) / 2; gy = (np.roll(g, -1, 0) - np.roll(g, 1, 0)) / 2
    def blur(a, s=3):
        k = np.exp(-0.5 * (np.arange(-3 * s, 3 * s + 1) / s) ** 2); k /= k.sum()
        a = np.apply_along_axis(lambda r: np.convolve(np.pad(r, 3 * s, mode='wrap'), k, 'valid'), 1, a)
        return np.apply_along_axis(lambda c: np.convolve(np.pad(c, 3 * s, mode='wrap'), k, 'valid'), 0, a)
    Jxx, Jyy, Jxy = blur(gx * gx), blur(gy * gy), blur(gx * gy)
    ang = 0.5 * np.arctan2(2 * Jxy, Jxx - Jyy)
    grain = np.degrees(np.abs(np.abs(ang) - np.pi / 2))
    lam = np.sqrt((Jxx - Jyy) ** 2 + 4 * Jxy ** 2); w = lam; w = w / (w.sum() + 1e-12)
    return float((grain * w).sum()), float((w * (grain > 15)).sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('glb'); ap.add_argument('--spec'); ap.add_argument('--sheet')
    ap.add_argument('--min-along', type=float, default=0.9, help='share of long-face area with grain along the part')
    a = ap.parse_args()
    raw = open(a.glb, 'rb').read()
    js = json.loads(raw[20:20 + int.from_bytes(raw[12:16], 'little')])
    if any(e in js.get('extensionsRequired', []) for e in ('EXT_meshopt_compression', 'KHR_draco_mesh_compression')):
        sys.exit('decode first: npx @gltf-transform/cli copy in.glb plain.glb')
    extras = {n.get('name'): n.get('extras', {}) for n in js.get('nodes', [])}
    spec = json.load(open(a.spec)) if a.spec else {}
    sc = trimesh.load(a.glb, force='scene', process=False)
    fails, n_parts, textures = [], 0, {}
    by_node = {}
    for node in sc.graph.nodes_geometry:
        T, gname = sc.graph[node]
        # trimesh splits a multi-material mesh into one node per primitive, suffixed _<hex>
        by_node.setdefault(re.sub(r'_[0-9a-f]{6}$', '', node), []).append((T, sc.geometry[gname]))
    notes = []
    for node, prims in sorted(by_node.items()):
        wood = [(T, g) for T, g in prims if getattr(g.visual, 'material', None) is not None
                and WOOD.search(getattr(g.visual.material, 'name', '') or '')]
        if not wood: continue
        # flatten the node's wood primitives into one triangle list
        Ps, Fs, UVs, ENDs, Ws, off = [], [], [], [], [], 0
        for T, g in wood:
            mname = g.visual.material.name or ''
            img = getattr(g.visual.material, 'baseColorTexture', None)
            uv = getattr(g.visual, 'uv', None)
            if img is None or uv is None:
                notes.append(f'{node}: {mname} is flat colour (no texture), so it shows no grain; skipped'); continue
            if not END.search(mname): textures.setdefault(mname, img)
            P = trimesh.transform_points(g.vertices, T)
            Ps.append(P); Fs.append(g.faces + off); UVs.append(np.asarray(uv)); off += len(P)
            ENDs.append(np.full(len(g.faces), bool(END.search(mname))))
            Ws.append(np.full(len(g.faces), img.size[0] >= img.size[1]))
        if not Ps: continue
        P, F, UV, ISEND, WIDE = np.vstack(Ps), np.vstack(Fs), np.vstack(UVs), np.concatenate(ENDs), np.concatenate(Ws)
        # separate solids inside one mesh (weld by position: split normals and UV seams cut faces apart)
        wm = trimesh.Trimesh(P, F, process=False); wm.merge_vertices(merge_tex=True, merge_norm=True, digits_vertex=5)   # 10 micron: survives quantized GLBs
        comps = trimesh.graph.connected_components(wm.face_adjacency, nodes=np.arange(len(F)))
        size = np.ptp(P, 0).max()
        comps = [c for c in comps if np.ptp(P[F[c].ravel()], 0).max() > 0.25 * size]
        name = re.sub(r'(\.\d+)$', '', node)
        ex = extras.get(node) or extras.get(name) or {}
        if 'grain_axis' in ex:      # written per part by web_glb.py: one part, however its CAD faces connect
            comps = [np.arange(len(F))]
        merged = len(comps) > 1
        if merged:
            notes.append(f'{node}: {len(comps)} separate parts in one mesh; checked each by its own long side '
                         '(spec grain can\'t apply: export one mesh per part)')
        for ci, c in enumerate(comps):
            label = f'{node}[{ci}]' if merged else node
            Pc = P[np.unique(F[c].ravel())]
            g_ax = None
            if not merged:
                if 'grain_axis' in ex: g_ax = np.array(ex['grain_axis'], float)
                else:
                    for rx, d in spec.get('parts', {}).items():
                        if re.search(rx, name) and d.get('grain') in ('x', 'y', 'z'):
                            g_ax = np.array({'x': [1, 0, 0], 'y': [0, 0, -1], 'z': [0, 1, 0]}[d['grain']], float)  # model Z up -> GLB Y up
            if g_ax is None:
                C = Pc - Pc.mean(0); w, v = np.linalg.eigh(np.cov(C.T))
                e = [np.ptp(C @ v[:, k]) for k in range(3)]
                if sorted(e)[-1] < 1.15 * sorted(e)[-2]: continue      # near-cube: no single grain direction
                g_ax = v[:, int(np.argmax(e))]
            g_ax = g_ax / np.linalg.norm(g_ax); n_parts += 1
            f = F[c]; p0, p1, p2 = P[f[:, 0]], P[f[:, 1]], P[f[:, 2]]; t0, t1, t2 = UV[f[:, 0]], UV[f[:, 1]], UV[f[:, 2]]
            isend, wide = ISEND[c], WIDE[c]
            n = np.cross(p1 - p0, p2 - p0); area = np.linalg.norm(n, axis=1) / 2
            nn = n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-15)
            endface = np.abs(nn @ g_ax) > 0.7
            e1, e2, d1, d2 = p1 - p0, p2 - p0, t1 - t0, t2 - t0
            det = d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]; ok = np.abs(det) > 1e-14
            sd = np.where(ok, det, 1)[:, None]
            dU = (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) / sd; dV = (e2 * d1[:, 0:1] - e1 * d2[:, 0:1]) / sd
            gd = np.where(wide[:, None], dU, dV); gd /= (np.linalg.norm(gd, axis=1, keepdims=True) + 1e-15)
            gp = g_ax[None, :] - nn * (nn @ g_ax)[:, None]; gp /= (np.linalg.norm(gp, axis=1, keepdims=True) + 1e-15)
            m = ~endface & ok & ~isend
            tot = area[m].sum(); along = area[m][np.abs((gd[m] * gp[m]).sum(1)) > 0.94].sum()
            if tot > 0 and along / tot < a.min_along:
                fails.append((label, 'across', f'grain along the part on {100 * along / tot:.0f}% of its long faces'))
            has_end = ISEND.any()   # only judge end faces when the model has an end-grain material at all
            wrong = area[(endface & ~isend) if has_end else np.zeros(len(c), bool)].sum() + area[~endface & isend].sum()
            if wrong > 0.02 * area.sum():
                fails.append((label, 'end', f'{100 * wrong / area.sum():.0f}% of its surface has end grain on a long face or long grain on an end'))
    sheet = []
    for mname, img in textures.items():
        mean, off = straightness(img)
        bad = mean > 6 or off > 0.12
        print(f'{"FAIL" if bad else "ok  "} texture {mname}: grain {mean:.1f} deg from U, {off * 100:.0f}% of the figure >15 deg off')
        if bad: fails.append((mname, 'figure', 'long-grain texture is not straight grain along U (cathedral, swirl or contour figure)'))
        sheet.append(img.convert('RGB').resize((1024, 256)))
    if a.sheet and sheet:
        S = Image.new('RGB', (1024, 256 * len(sheet)), 'white')
        for i, s in enumerate(sheet): S.paste(s, (0, 256 * i))
        S.save(a.sheet, quality=85)
    for t in notes: print('note', t)
    for n, k, why in fails: print(f'FAIL {k:10s} {n}: {why}')
    print(f'{n_parts} wood parts, {len(textures)} long-grain textures: ' + ('grain OK' if not fails else f'{len(fails)} failures'))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
