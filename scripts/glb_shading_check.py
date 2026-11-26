#!/usr/bin/env python3
"""Fail a web GLB whose surfaces will shade wrong in the viewer: faceting, smeared normals, shading seams.

The Moth case went on the site twice with its piano-black lid and roof wobbling like wet plastic: the flat panels
carried normals averaged round their hard edges, so every flat face shaded as if it were bulging, and gloss
(black French polish, clearcoat, polished metal) shows that at a glance (the owner, 26 Nov 2026: "polygons on moth are
fucked again ... i thought we had a rule for this by now"). Matte wood hid it, so nothing looked for it. This looks
at the normals themselves, part by part, in world space, so it can't be fooled by a viewer angle.

Fails (exit 1) on any part where one of these covers more than --max-share (default 1%) of its area:
  smeared   a FLAT panel (a connected run of faces whose normals agree within 0.5 deg, at least 1% of the part's
            area) whose vertex normals lean off the face normal by more than 2 deg: the panel shades as a bulge,
            reflections wobble and smear (normals averaged across a hard edge, a bad weld, a bad decimation)
  softedge  a real edge (faces meeting at more than --crease, default 40 deg) whose two sides share one averaged
            normal: the box shades as if it were rounded, dark streaks run across both faces
  facets    a curved surface shaded flat: neighbouring faces 2 to 20 deg apart with split (hard) normals,
            so every polygon shows as its own flat facet (missing smooth shading / auto-smooth). Cut gems
            (material or node matching --faceted, default gem|stone|crystal|facet) are meant to be faceted: skipped
  coarse    a smooth-shaded curve too coarse to read as smooth: neighbours more than --coarse (default 20 deg,
            15 deg on gloss) but under --crease apart, over 30% of the part; the outline and highlights show the
            polygons (needs more subdivision before export, or a less aggressive simplify; glb_reshade.py refines
            it). Fails on wood, finish and leather parts (turned handles, roundovers); on cast or sculpted parts
            it only WARNs, because their bumps are detail, not polygons: judge those with glb_fidelity_check.py
  flipped   vertex normals pointing into the part (more than 90 deg off the face, against the winding): the
            face lights from behind and goes black or flickers
and that patch is also at least --min-model-share (default 0.05%) of the whole model's surface, so a seam on one
screw of a 240-part case doesn't fail it but the same seam on a lid, or on a ring that is the whole model, does.
And on the GLB as shipped (before decoding):
  8bit      NORMAL stored as 8-bit (BYTE) on a glossy material (roughness <= 0.4, clearcoat, or polished metal):
            the steps show as banding in the reflections. Re-compress with --quantize-normal 12 (glb_reshade.py does).

  python3 glb_shading_check.py model.glb [more.glb ...] [--crease 40] [--max-share 0.01] [--json out.json]
  python3 glb_shading_check.py --site <site repo>        # every GLB under static/ and content/
Meshopt/quantized GLBs (every site GLB) are decoded with npx @gltf-transform/cli first (no Blender needed).
Fix a failing GLB with glb_reshade.py (same folder): it re-derives every normal from the geometry with a crease
angle, splits real edges, keeps UVs, materials, names and extras, and re-compresses with 12-bit normals.
Passing this is necessary, not enough: still look at the site's own viewer close up on a glossy panel.
"""
import argparse, glob, json, os, re, struct, subprocess, sys, tempfile
import numpy as np

WOODISH = re.compile(r'(?i)wood|walnut|oak|ash|maple|cherry|polish|lacquer|paint|ply|birch|mahogany|leather|grain')
CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def read_glb(path):
    b = open(path, 'rb').read()
    if b[:4] != b'glTF':
        raise ValueError('not a GLB')
    off, j, binc = 12, None, b''
    while off < len(b):
        ln, typ = struct.unpack('<II', b[off:off + 8])
        chunk = b[off + 8:off + 8 + ln]
        if typ == 0x4E4F534A:
            j = json.loads(chunk)
        elif typ == 0x004E4942:
            binc = chunk
        off += 8 + ln
    return j, binc


def accessor(j, binc, i):
    a = j['accessors'][i]
    n, k, dt = a['count'], NC[a['type']], CT[a['componentType']]
    out = np.zeros((n, k), np.float64)
    if 'bufferView' in a:
        bv = j['bufferViews'][a['bufferView']]
        isz = np.dtype(dt).itemsize
        stride = bv.get('byteStride', isz * k)
        start = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
        vals = np.ndarray((n, k), dtype=np.dtype(dt).newbyteorder('<'), buffer=binc, offset=start, strides=(stride, isz))
        out = vals.astype(np.float64)
        if a.get('normalized'):
            out = {np.int8: np.maximum(out / 127, -1), np.uint8: out / 255,
                   np.int16: np.maximum(out / 32767, -1), np.uint16: out / 65535}.get(dt, out)
    if 'sparse' in a:
        raise ValueError('sparse accessors not supported')
    return out


def node_mats(j):
    M = {}
    def local(nd):
        if 'matrix' in nd:
            return np.array(nd['matrix'], float).reshape(4, 4).T
        t = np.array(nd.get('translation', [0, 0, 0]), float)
        x, y, z, w = nd.get('rotation', [0, 0, 0, 1])
        s = np.array(nd.get('scale', [1, 1, 1]), float)
        R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                      [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                      [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        T = np.eye(4); T[:3, :3] = R * s; T[:3, 3] = t
        return T
    def walk(i, P):
        W = P @ local(j['nodes'][i]); M[i] = W
        for c in j['nodes'][i].get('children', []):
            walk(c, W)
    roots = j['scenes'][j.get('scene', 0)]['nodes'] if j.get('scenes') else range(len(j.get('nodes', [])))
    for r in roots:
        walk(r, np.eye(4))
    return M


def glossy(mat):
    pbr = mat.get('pbrMetallicRoughness', {})
    r = pbr.get('roughnessFactor', 1.0); m = pbr.get('metallicFactor', 1.0)
    cc = mat.get('extensions', {}).get('KHR_materials_clearcoat', {}).get('clearcoatFactor', 0)
    has_rmap = 'metallicRoughnessTexture' in pbr
    return cc > 0 or (r <= 0.4 and not has_rmap) or (m > 0.5 and r <= 0.45 and not has_rmap)


def decode(path, tmp):
    j, _ = read_glb(path)
    ext = set(j.get('extensionsUsed', []))
    if not ext & {'EXT_meshopt_compression', 'KHR_draco_mesh_compression', 'KHR_mesh_quantization'}:
        return path
    a, b = os.path.join(tmp, 'a.glb'), os.path.join(tmp, 'plain.glb')
    cli = os.environ.get('GLTF_TRANSFORM') or 'npx --yes @gltf-transform/cli@4.5.1'
    for cmd in ([path, a], [a, b]):
        verb = 'copy' if cmd[1] == a else 'dequantize'
        r = subprocess.run(cli.split() + [verb] + cmd, capture_output=True, text=True)
        if r.returncode:
            sys.exit(f'decode failed ({verb}): {r.stderr[-400:]}')
    return b


def angle(u, v):
    return np.degrees(np.arccos(np.clip(np.einsum('...i,...i->...', u, v), -1, 1)))


def components(n, a, b):
    """Connected components over n items with edges a-b (union-find)."""
    p = np.arange(n)
    def find(x):
        while p[x] != x:
            p[x] = p[p[x]]; x = p[x]
        return x
    for x, y in zip(a.tolist(), b.tolist()):
        rx, ry = find(x), find(y)
        if rx != ry:
            p[rx] = ry
    return np.array([find(x) for x in range(n)])


def panels(fn, A, fa, fb, dih, crease, min_share=0.01, ids=False, join=0.5, planar=1.0):
    """Faces that belong to a FLAT PANEL: a connected run of faces agreeing within 0.5 deg, planar (every face within
    1 deg of the run's mean normal), at least min_share of the part's area, and at least 4x the area of any flat run
    it meets across a smooth edge. The last test keeps the facets of a polygonal arc or a turned handle (equal-sized
    runs side by side, meant to shade as one curve) out, while a lid next to its narrow roundover stays a panel."""
    n = len(fn); tot = A.sum()
    flat = dih < join
    comp = components(n, fa[flat], fb[flat])
    _, comp = np.unique(comp, return_inverse=True)
    carea = np.bincount(comp, weights=A)
    mean = np.zeros((len(carea), 3)); np.add.at(mean, comp, fn * A[:, None])
    mean /= np.maximum(np.linalg.norm(mean, axis=1, keepdims=True), 1e-12)
    nonplanar = np.bincount(comp, weights=(angle(fn, mean[comp]) >= planar).astype(float), minlength=len(carea)) > 0
    ok = (carea >= min_share * tot) & ~nonplanar
    sm = (dih >= join) & (dih < crease)
    ca, cb = comp[fa[sm]], comp[fb[sm]]
    nb = np.zeros(len(carea))
    np.maximum.at(nb, ca, carea[cb]); np.maximum.at(nb, cb, carea[ca])
    ok &= carea >= 4 * nb
    return (ok[comp], comp) if ids else ok[comp]


def check_prim(V, N, F, crease, coarse_deg):
    """Returns area shares per defect for one triangle soup in world space."""
    e0, e1 = V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]
    fn = np.cross(e0, e1); A = np.linalg.norm(fn, axis=1) / 2
    ok = A > 1e-14
    F, fn, A = F[ok], fn[ok] / (2 * A[ok, None]), A[ok]
    tot = A.sum()
    res = dict(smeared=0.0, softedge=0.0, facets=0.0, coarse=0.0, flipped=0.0)
    if tot <= 0 or len(F) == 0:
        return res, tot
    CN = N[F]                                    # (f,3,3) corner normals
    CN = CN / np.maximum(np.linalg.norm(CN, axis=2, keepdims=True), 1e-12)
    dev = angle(CN, fn[:, None, :])              # (f,3)
    res['flipped'] = A[(dev > 90).any(1)].sum() / tot
    # weld by position so UV seams / split normals don't break adjacency
    span = np.ptp(V, axis=0).max() or 1.0
    key = np.round(V / (span * 1e-6)).astype(np.int64)
    _, pid = np.unique(key, axis=0, return_inverse=True); pid = pid.ravel()
    PF = pid[F]
    # undirected edges -> face pairs
    E = np.concatenate([PF[:, [0, 1]], PF[:, [1, 2]], PF[:, [2, 0]]])
    ci = np.concatenate([np.repeat([[0, 1]], len(F), 0), np.repeat([[1, 2]], len(F), 0), np.repeat([[2, 0]], len(F), 0)])
    fid = np.tile(np.arange(len(F)), 3)
    Es = np.sort(E, 1)
    order = np.lexsort((Es[:, 1], Es[:, 0])); Es, fid, ci, E = Es[order], fid[order], ci[order], E[order]
    same = (Es[1:] == Es[:-1]).all(1)
    i0 = np.nonzero(same)[0]
    # keep only edges with exactly two faces (manifold pairs)
    first = np.r_[True, ~same]; grp = np.cumsum(first) - 1
    cnt = np.bincount(grp)
    i0 = i0[cnt[grp[i0]] == 2]
    fa, fb = fid[i0], fid[i0 + 1]
    m = fa != fb
    i0, fa, fb = i0[m], fa[m], fb[m]
    dih = angle(fn[fa], fn[fb])
    # slivers thinner than a few position-quantization steps (14-bit over the part) have no reliable face normal:
    # their tilt is rounding, and the viewer shades them with the vertex normals anyway. Leave them out.
    L = np.maximum.reduce([np.linalg.norm(V[F[:, i]] - V[F[:, (i + 1) % 3]], axis=1) for i in range(3)])
    thin = (2 * A / np.maximum(L, 1e-30)) < 4 * span / 16384
    keep = ~thin[fa] & ~thin[fb]
    i0, fa, fb, dih = i0[keep], fa[keep], fb[keep], dih[keep]
    # corner normals at the edge's two ends on each side (match by welded position)
    def cn_at(f, pidv):
        k = (PF[f] == pidv[:, None]).argmax(1)
        return CN[f, k]
    pa, pb = Es[i0, 0], Es[i0, 1]
    split = np.maximum(angle(cn_at(fa, pa), cn_at(fb, pa)), angle(cn_at(fa, pb), cn_at(fb, pb))) > 1.0
    def share(faces):
        if len(faces) == 0:
            return 0.0
        return A[np.unique(faces)].sum() / tot
    soft = (dih > crease) & ~split & (dih < 175)
    res['softedge'] = share(np.r_[fa[soft], fb[soft]])
    pan_f, pcomp = panels(fn, A, fa, fb, dih, crease, ids=True)
    # an edge on a flat panel is the panel's own edge (a taper, a faceted ogive), meant to show; facets are curves
    fac = (dih > 2) & (dih <= 20) & split & ~(pan_f[fa] | pan_f[fb])
    res['facets'] = share(np.r_[fa[fac], fb[fac]])
    crs = (dih > coarse_deg) & (dih <= crease) & ~split
    res['coarse'] = share(np.r_[fa[crs], fb[crs]])
    # flat panels: see panels(); every corner on a panel must carry the panel's own normal
    panel = pan_f
    lean = dev.max(1) > 2.0
    res['smeared'] = A[panel & lean & (dev.max(1) <= 90) & ~thin].sum() / tot
    return res, tot


def check_glb(path, crease=40.0, coarse=20.0, faceted=r'(?i)gem|stone|crystal|facet', max_share=0.01, quiet=False, min_model_share=0.0005):
    raw_j, _ = read_glb(path)
    fails, rows, warns, parts = [], [], [], []
    with tempfile.TemporaryDirectory() as tmp:
        plain = decode(path, tmp)
        j, binc = read_glb(plain)
        mats = j.get('materials', [])
        M = node_mats(j)
        # 8-bit normals on gloss, judged on the GLB as shipped
        for mi, mesh in enumerate(raw_j.get('meshes', [])):
            for p in mesh['primitives']:
                ni = p['attributes'].get('NORMAL')
                if ni is None or 'material' not in p:
                    continue
                if raw_j['accessors'][ni]['componentType'] in (5120, 5121) and glossy(raw_j['materials'][p['material']]):
                    fails.append(('8bit', mesh.get('name') or f'mesh{mi}', raw_j['materials'][p['material']].get('name', '?'), 1.0))
        for ni, nd in enumerate(j.get('nodes', [])):
            if 'mesh' not in nd or ni not in M:
                continue
            W = M[ni]; R = W[:3, :3]
            if abs(np.linalg.det(R)) < 1e-18:   # scaled to nothing: hidden, never drawn
                continue
            Nm = np.linalg.inv(R).T
            for p in j['meshes'][nd['mesh']]['primitives']:
                if p.get('mode', 4) != 4 or 'NORMAL' not in p['attributes']:
                    if p.get('mode', 4) == 4 and 'NORMAL' not in p['attributes']:
                        fails.append(('nonormals', nd.get('name') or f'node{ni}', '?', 1.0))
                    continue
                V = accessor(j, binc, p['attributes']['POSITION'])
                N = accessor(j, binc, p['attributes']['NORMAL'])
                F = accessor(j, binc, p['indices']).astype(np.int64).reshape(-1, 3) if 'indices' in p \
                    else np.arange(len(V)).reshape(-1, 3)
                V = V @ R.T + W[:3, 3]; N = N @ Nm.T
                if np.linalg.det(R) < 0:
                    F = F[:, ::-1]
                mat = mats[p['material']] if 'material' in p else {}
                cd = coarse - 5 if glossy(mat) else coarse
                res, area = check_prim(V, N, F, crease, cd)
                parts.append(area)
                name = nd.get('name') or f'node{ni}'
                rows.append(dict(node=name, material=mat.get('name', '?'), faces=len(F), **{k: round(v, 4) for k, v in res.items()}))
                cut = bool(faceted) and re.search(faceted, f"{mat.get('name', '')} {name}")
                for k, v in res.items():
                    if cut and k in ('facets', 'smeared', 'coarse'):
                        continue
                    if k == 'coarse' and not WOODISH.search(mat.get('name', '')):
                        if v > 0.30:
                            warns.append((k, name, mat.get('name', '?'), v))
                        continue
                    lim = max_share if k != 'coarse' else max(max_share, 0.30)
                    if v > lim:
                        fails.append((k, name, mat.get('name', '?'), v, v * area))
    # a defect has to be big enough to see: over max_share of its part AND over min_model_share of the whole model's
    # surface (a 2% seam on one screw of a 240-part case is invisible; the same on a lid is not). Rules about the data
    # (8bit, nonormals) always count.
    total = sum(parts) or 1.0
    fails = [(k, n, m, v) for k, n, m, v, *ab in fails if not ab or ab[0] >= min_model_share * total]
    if not quiet:
        for k, n, m, v in fails:
            print(f'  FAIL {k:9s} {n} [{m}] {v * 100:.1f}% of its area')
        if warns:
            print(f'  WARN coarse on {len(warns)} cast/sculpted parts (judge them against the full model with '
                  f'glb_fidelity_check.py), worst: ' + ', '.join(f'{n} [{m}] {v * 100:.0f}%' for _, n, m, v in
                                                          sorted(warns, key=lambda w: -w[3])[:3]))
    return fails, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('glb', nargs='*')
    ap.add_argument('--site')
    ap.add_argument('--crease', type=float, default=40.0)
    ap.add_argument('--coarse', type=float, default=20.0)
    ap.add_argument('--faceted', default=r'(?i)gem|stone|crystal|facet')
    ap.add_argument('--max-share', type=float, default=0.01)
    ap.add_argument('--json')
    a = ap.parse_args()
    files = list(a.glb)
    if a.site:
        for sub in ('static', 'content'):
            files += sorted(glob.glob(os.path.join(a.site, sub, '**', '*.glb'), recursive=True))
    if not files:
        ap.error('give GLBs or --site')
    bad, report = 0, {}
    for f in files:
        print(f)
        try:
            fails, rows = check_glb(f, a.crease, a.coarse, a.faceted, a.max_share)
        except Exception as e:  # a GLB we can't read is a fail, not a skip
            print(f'  FAIL unreadable: {e}'); bad += 1; report[f] = {'error': str(e)}; continue
        report[f] = {'fails': [dict(rule=k, node=n, material=m, share=round(v, 4)) for k, n, m, v in fails]}
        if fails:
            bad += 1
        else:
            print('  PASS')
    if a.json:
        json.dump(report, open(a.json, 'w'), indent=1)
    print(f'{len(files) - bad}/{len(files)} pass')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
