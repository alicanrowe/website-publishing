#!/usr/bin/env python3
"""Re-derive every normal of a web GLB from its geometry, with real edges split, then re-compress it.

Fixes what glb_shading_check.py fails as smeared / softedge / facets / flipped / 8bit: normals averaged round hard
edges (flat panels that shade as bulges), curved surfaces shaded flat, normals pointing inwards, 8-bit normals on gloss.
For every face corner the new normal is the corner-angle-weighted mean of the faces round that point (welded by
position, so UV seams don't crease the shading) that meet the face within --crease degrees; so flat panels get their
exact face normal, real edges stay sharp and curves stay smooth. Positions, UVs, materials, node names, extras and
textures are untouched (each output vertex is an original vertex, split only where its normal must differ).

  python3 glb_reshade.py in.glb out.glb [--crease 30] [--only REGEX] [--skip REGEX] [--flat REGEX] [--refine 0.3]
    --only / --skip   match material or node names to choose which primitives are reshaded (default: all)
    --flat REGEX      materials cut as facets (default gem|stone|crystal|facet): every face shaded flat
  Output is meshopt-compressed (level medium: 'high' squeezes normals to 8 bits) with 12-bit normals and 14-bit
  positions (gltf-transform), never gltfpack.
Then run glb_shading_check.py on the output and look at the viewer close up.
"""
import argparse, json, os, re, struct, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glb_shading_check import read_glb, accessor, decode, panels, check_prim, glossy, WOODISH  # noqa: E402


def corner_angles(V, F):
    out = np.zeros(F.shape)
    for k in range(3):
        a = V[F[:, (k + 1) % 3]] - V[F[:, k]]; b = V[F[:, (k + 2) % 3]] - V[F[:, k]]
        na = np.linalg.norm(a, axis=1); nb = np.linalg.norm(b, axis=1)
        out[:, k] = np.arccos(np.clip(np.einsum('ij,ij->i', a, b) / np.maximum(na * nb, 1e-30), -1, 1))
    return out


def reshade(V, F, crease):
    """Corner normals by smoothing fans: round each point, faces joined across an edge flatter than crease share one
    normal (corner-angle weighted); a sharper edge splits it. Same rule as Blender's auto smooth, so shading is
    continuous across every smooth edge and every real edge stays crisp."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    ln = np.linalg.norm(fn, axis=1); good = ln > 1e-20
    fn = fn / np.maximum(ln, 1e-30)[:, None]
    W = corner_angles(V, F) * good[:, None]
    span = np.ptp(V, axis=0).max() or 1.0
    key = np.round(V / (span * 1e-6)).astype(np.int64)
    _, pid = np.unique(key, axis=0, return_inverse=True); pid = pid.ravel()
    PF = pid[F]; nF = len(F)
    # directed half-edges (face, corner k -> k+1) keyed by welded endpoints
    a = PF.ravel(); b = PF[:, [1, 2, 0]].ravel()
    cid_a = np.arange(nF * 3); cid_b = (np.arange(nF)[:, None] * 3 + np.array([1, 2, 0])[None, :]).ravel()
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    lo_c = np.where(a <= b, cid_a, cid_b); hi_c = np.where(a <= b, cid_b, cid_a)
    order = np.lexsort((hi, lo)); lo, hi, lo_c, hi_c = lo[order], hi[order], lo_c[order], hi_c[order]
    fidx = np.repeat(np.arange(nF), 3)[order]
    same = (lo[1:] == lo[:-1]) & (hi[1:] == hi[:-1])
    # every pair of faces on the same edge (all pairs where more than two faces share it: duplicates, fins)
    gstart = np.r_[0, np.nonzero(~same)[0] + 1]; gsize = np.diff(np.r_[gstart, len(lo)])
    pa, pb = [], []
    for k in np.unique(gsize[gsize >= 2]):
        st = gstart[gsize == k]
        for x in range(k):
            for y in range(x + 1, k):
                pa.append(st + x); pb.append(st + y)
    pa = np.concatenate(pa) if pa else np.zeros(0, int); pb = np.concatenate(pb) if pb else np.zeros(0, int)
    fa, fb = fidx[pa], fidx[pb]
    # flat panels first (same rule as the check): two different panels never share a normal, however shallow the
    # angle between them (a tapered leg, a faceted ogive), so each stays dead flat
    ia = same.nonzero()[0]
    dih = np.degrees(np.arccos(np.clip(np.einsum('ij,ij->i', fn[fidx[ia]], fn[fidx[ia + 1]]), -1, 1)))
    pan, pcomp = panels(fn, np.where(good, ln / 2, 0), fidx[ia], fidx[ia + 1], dih, crease, ids=True)
    ok = (fa != fb) & (np.einsum('ij,ij->i', fn[fa], fn[fb]) >= np.cos(np.radians(crease))) & good[fa] & good[fb]
    ok &= ~(pan[fa] & pan[fb] & (pcomp[fa] != pcomp[fb]))
    pa, pb = pa[ok], pb[ok]
    r = np.r_[lo_c[pa], hi_c[pa]]; c = np.r_[lo_c[pb], hi_c[pb]]
    C = nF * 3
    g = coo_matrix((np.ones(len(r)), (r, c)), shape=(C, C))
    _, lab = connected_components(g, directed=False)
    cf = np.repeat(np.arange(nF), 3)
    # weighted normals: a fan that touches a flat panel takes the panel's normal, so the panel shades dead flat and
    # only its roundover / chamfer carries the turn (the long triangles across a lid can't smear an edge normal over it)
    w = W.ravel() * np.where(pan[cf], 1e6, 1.0)
    acc = np.zeros((lab.max() + 1, 3))
    np.add.at(acc, lab, fn[cf] * w[:, None])
    out = acc[lab]
    # a fan that wraps round a sharp point (needle tip, cone apex) joins faces far apart through its neighbours; there
    # each corner keeps only the faces of its fan within crease of its own face
    on = out / np.maximum(np.linalg.norm(out, axis=1), 1e-30)[:, None]
    far = np.nonzero(np.einsum('ij,ij->i', on, fn[cf]) < np.cos(np.radians(crease)))[0]
    if len(far):
        order_l = np.argsort(lab, kind='stable'); sl = lab[order_l]
        st = np.searchsorted(sl, lab[far]); en = np.searchsorted(sl, lab[far], side='right')
        cosc = np.cos(np.radians(crease))
        for c, a0, a1 in zip(far.tolist(), st.tolist(), en.tolist()):
            mem = order_l[a0:a1]; fm = fn[cf[mem]]
            sel = fm @ fn[cf[c]] >= cosc
            out[c] = (fm[sel] * w[mem][sel][:, None]).sum(0)
    nl = np.linalg.norm(out, axis=1); bad = nl < 1e-12
    out[bad] = fn[cf[bad]]
    out /= np.maximum(np.linalg.norm(out, axis=1), 1e-30)[:, None]
    return out.reshape(-1, 3, 3)


def refine(V, N, A, F, crease):
    """One 1-to-4 split with PN-triangle edge midpoints: on a smooth edge the new point sits on the curve the two end
    normals describe, so a coarse turned handle gets rounder instead of just denser; on a split (hard) edge, and on
    flat panels, it stays on the straight line, so no cracks open and panels stay flat. Attributes interpolate."""
    E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    Es = np.sort(E, 1)
    ue, einv = np.unique(Es, axis=0, return_inverse=True); einv = einv.ravel()
    i0, i1 = ue[:, 0], ue[:, 1]
    p0, p1, n0, n1 = V[i0], V[i1], N[i0], N[i1]
    span = np.ptp(V, axis=0).max() or 1.0
    key = np.round(V / (span * 1e-6)).astype(np.int64)
    _, pid = np.unique(key, axis=0, return_inverse=True); pid = pid.ravel()
    # an edge is hard if any copy of it (same welded ends) carries other normals
    pe = np.sort(np.c_[pid[i0], pid[i1]], 1)
    nq = np.round(np.c_[n0, n1] * 512).astype(np.int64)
    swap = pid[i0] > pid[i1]; nq[swap] = nq[swap][:, [3, 4, 5, 0, 1, 2]]
    _, ginv = np.unique(pe, axis=0, return_inverse=True); ginv = ginv.ravel()
    _, kinv = np.unique(np.c_[pe, nq], axis=0, return_inverse=True); kinv = kinv.ravel()
    kinds = np.zeros(ginv.max() + 1, int)
    first = {}
    for g, k in zip(ginv.tolist(), kinv.tolist()):
        if g not in first:
            first[g] = k
        elif first[g] != k:
            kinds[g] = 1
    hard = kinds[ginv] == 1
    hard |= np.degrees(np.arccos(np.clip(np.einsum('ij,ij->i', n0, n1), -1, 1))) > crease
    d = p1 - p0
    w01 = np.einsum('ij,ij->i', d, n0); w10 = np.einsum('ij,ij->i', -d, n1)
    mid = (p0 + p1) / 2 - np.where(hard[:, None], 0, (w01[:, None] * n0 + w10[:, None] * n1) / 8)
    nm = n0 + n1; nm /= np.maximum(np.linalg.norm(nm, axis=1), 1e-30)[:, None]
    nv = len(V)
    V2 = np.r_[V, mid]; N2 = np.r_[N, nm]
    A2 = {k: np.r_[v, (v[i0] + v[i1]) / 2] for k, v in A.items()}
    m = (einv + nv).reshape(3, -1).T            # mids of edges 01, 12, 20 per face
    a, b, c = F[:, 0], F[:, 1], F[:, 2]
    F2 = np.concatenate([np.c_[a, m[:, 0], m[:, 2]], np.c_[m[:, 0], b, m[:, 1]],
                         np.c_[m[:, 2], m[:, 1], c], np.c_[m[:, 0], m[:, 1], m[:, 2]]])
    return V2, N2, A2, F2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src'); ap.add_argument('dst')
    ap.add_argument('--crease', type=float, default=30.0)
    ap.add_argument('--only'); ap.add_argument('--skip')
    ap.add_argument('--flat', default=r'(?i)gem|stone|crystal|facet',
                    help='materials/nodes cut as facets (gems): every face flat-shaded (crease 1 deg)')
    ap.add_argument('--no-compress', action='store_true')
    ap.add_argument('--force-refine', metavar='REGEX',
                    help='always split the matching parts (material or node name) --passes times, e.g. one part whose '
                         'flat triangles sit in a curve, without growing the rest of the model')
    ap.add_argument('--passes', type=int, default=3, help='most refinement passes per part (default 3)')
    ap.add_argument('--refine', type=float, default=0.30,
                    help='split a part 1-to-4 (PN midpoints, up to twice) while glb_shading_check calls more than this '
                         'share of it coarse (default 0.30, the fail line; 0 = never)')
    a = ap.parse_args()
    only = re.compile(a.only) if a.only else None
    skip = re.compile(a.skip) if a.skip else None
    cli = (os.environ.get('GLTF_TRANSFORM') or 'npx --yes @gltf-transform/cli@4.5.1').split()
    with tempfile.TemporaryDirectory() as tmp:
        plain = decode(a.src, tmp)
        j, binc = read_glb(plain)
        blob = bytearray(binc)
        def add(arr, comp, typ, target=None, minmax=False):
            nonlocal blob
            while len(blob) % 4:
                blob.append(0)
            off = len(blob); data = np.ascontiguousarray(arr).tobytes(); blob += data
            bv = {'buffer': 0, 'byteOffset': off, 'byteLength': len(data)}
            if target:
                bv['target'] = target
            j['bufferViews'].append(bv)
            acc = {'bufferView': len(j['bufferViews']) - 1, 'componentType': comp, 'count': len(arr), 'type': typ}
            if minmax:
                acc['min'] = arr.min(0).tolist(); acc['max'] = arr.max(0).tolist()
            j['accessors'].append(acc)
            return len(j['accessors']) - 1
        TYPES = {1: 'SCALAR', 2: 'VEC2', 3: 'VEC3', 4: 'VEC4'}
        names = {}
        for nd in j.get('nodes', []):
            if 'mesh' in nd:
                names.setdefault(nd['mesh'], nd.get('name', ''))
        done = 0; refined = [0]; dupes = [0]
        for mi, mesh in enumerate(j['meshes']):
            for p in mesh['primitives']:
                if p.get('mode', 4) != 4:
                    continue
                mname = j['materials'][p['material']].get('name', '') if 'material' in p else ''
                label = f"{mname} {mesh.get('name', '')} {names.get(mi, '')}"
                if (only and not only.search(label)) or (skip and skip.search(label)):
                    continue
                V = accessor(j, j and bytes(binc), p['attributes']['POSITION'])
                F = accessor(j, bytes(binc), p['indices']).astype(np.int64).reshape(-1, 3) if 'indices' in p \
                    else np.arange(len(V)).reshape(-1, 3)
                # drop exact duplicate triangles (same three points): they z-fight and break the smoothing fans
                span = np.ptp(V, axis=0).max() or 1.0
                _, pidd = np.unique(np.round(V / (span * 1e-6)).astype(np.int64), axis=0, return_inverse=True)
                _, keep = np.unique(np.sort(pidd.ravel()[F], 1), axis=0, return_index=True)
                if len(keep) < len(F):
                    dupes[0] += len(F) - len(keep); F = F[np.sort(keep)]
                flat = bool(a.flat) and re.search(a.flat, label)
                CN = reshade(V, F, 1.0 if flat else a.crease)
                # weld: one output vertex per (original vertex, quantized new normal)
                q = np.round(CN.reshape(-1, 3) * 4096).astype(np.int64)
                keys = np.c_[F.ravel(), q]
                uk, inv = np.unique(keys, axis=0, return_inverse=True); inv = inv.ravel()
                src_v = uk[:, 0]
                newN = np.zeros((len(uk), 3)); np.add.at(newN, inv, CN.reshape(-1, 3))
                newN /= np.maximum(np.linalg.norm(newN, axis=1), 1e-30)[:, None]
                Vn = V[src_v]
                other = {an: accessor(j, bytes(binc), ai)[src_v] for an, ai in p['attributes'].items()
                         if an not in ('NORMAL', 'POSITION')}
                Fn = inv.reshape(-1, 3)
                mat = j['materials'][p['material']] if 'material' in p else {}
                cd = 15.0 if glossy(mat) else 20.0
                forced = bool(a.force_refine) and re.search(a.force_refine, label)
                for _ in range(a.passes if ((a.refine or forced) and not flat) else 0):
                    r = check_prim(Vn, newN, Fn, 40.0, cd)[0]
                    if forced:
                        r = dict(r, smeared=1.0)
                    # wood/finish curves too coarse, or (any material) big flat triangles sitting in a curve, which
                    # shade as smeared panels: split them so the curve can carry the light
                    if not ((WOODISH.search(mname) and r['coarse'] > a.refine) or r['smeared'] > 0.005 or r['facets'] > 0.005):
                        break
                    Vn, newN, other, Fn = refine(Vn, newN, other, Fn, a.crease)
                    refined[0] += 1
                    # normals again from the refined (now rounder) surface, same fans and panel rule
                    CN2 = reshade(Vn, Fn, a.crease)
                    k2 = np.c_[Fn.ravel(), np.round(CN2.reshape(-1, 3) * 4096).astype(np.int64)]
                    u2, i2 = np.unique(k2, axis=0, return_inverse=True); i2 = i2.ravel()
                    sv = u2[:, 0]
                    newN = np.zeros((len(u2), 3)); np.add.at(newN, i2, CN2.reshape(-1, 3))
                    newN /= np.maximum(np.linalg.norm(newN, axis=1), 1e-30)[:, None]
                    Vn = Vn[sv]; other = {k: v[sv] for k, v in other.items()}; Fn = i2.reshape(-1, 3)
                attrs = {'POSITION': add(Vn.astype(np.float32), 5126, 'VEC3', 34962, minmax=True)}
                for an, arr in other.items():
                    attrs[an] = add(arr.astype(np.float32), 5126, TYPES[arr.shape[1]], 34962)
                attrs['NORMAL'] = add(newN.astype(np.float32), 5126, 'VEC3', 34962)
                inv = Fn.ravel()
                p['attributes'] = attrs
                p.pop('targets', None)
                p['indices'] = add(inv.astype(np.uint32), 5125, 'SCALAR', 34963)
                p.get('extensions', {}).pop('KHR_draco_mesh_compression', None)
                done += 1
        j['buffers'] = [{'byteLength': len(blob)}]
        for k in ('extensionsUsed', 'extensionsRequired'):
            if k in j:
                j[k] = [e for e in j[k] if e not in ('EXT_meshopt_compression', 'KHR_mesh_quantization', 'KHR_draco_mesh_compression')]
                if not j[k]:
                    del j[k]
        js = json.dumps(j, separators=(',', ':')).encode()
        js += b' ' * (-len(js) % 4); blob += b'\0' * (-len(blob) % 4)
        raw = os.path.join(tmp, 'raw.glb')
        with open(raw, 'wb') as fh:
            fh.write(struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(blob)))
            fh.write(struct.pack('<II', len(js), 0x4E4F534A)); fh.write(js)
            fh.write(struct.pack('<II', len(blob), 0x004E4942)); fh.write(blob)
        pr = os.path.join(tmp, 'pruned.glb')
        for cmd in (['prune', raw, pr, '--keep-attributes', 'true', '--keep-leaves', 'true'],):
            r = subprocess.run(cli + cmd, capture_output=True, text=True)
            if r.returncode:
                sys.exit((r.stdout + r.stderr)[-800:])
        if a.no_compress:
            os.replace(pr, a.dst)
        else:
            r = subprocess.run(cli + ['meshopt', pr, a.dst, '--level', 'medium', '--quantize-normal', '12', '--quantize-position', '14'],
                               capture_output=True, text=True)
            if r.returncode:
                sys.exit((r.stdout + r.stderr)[-800:])
    print(f'{done} primitives reshaded at {a.crease} deg, {refined[0]} refinement passes, {dupes[0]} duplicate '
          f'triangles dropped -> {a.dst} '
          f'({os.path.getsize(a.dst) / 1e6:.2f} MB)')


if __name__ == '__main__':
    main()
