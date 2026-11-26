#!/usr/bin/env python3
"""THE wood library: one walnut, one ash, one oak ... for every render, reel, site card and web GLB.

Why (review, 26 Nov 2026): the same walnut looked different from project to project.
Every pipeline had its own wood: seven different walnut colours and five ashes were hard-coded across the CAD skill,
the web GLB builder and a handful of project render scripts, and the web GLBs only ever got rift grain, so a flat-sawn case side showed no cathedral. Now there is one table
(references/woods.json, photo-measured) and one wood model (this file, plus the same maths as Blender nodes in
scripts/blender/woodlib_bl.py). A pipeline asks for a species and a cut; it never writes a wood colour or a grain
node itself. scripts/woodlib_lint.py and the site gate (tools/gate/wood.py) fail anything that does.

The model. Wood is a solid: every point of a board sits at some distance from the log's pith, and that distance,
in growth rings, decides earlywood or latewood. A board is a part frame (u along the grain, v across the wide
face, w through the thickness, origin at the part's centre, inches) plus where the pith runs relative to it:
  flat     pith a few inches under the wide face, tilting slowly up through the board (taper): the rings cut the
           face in nested arches, a few cathedrals along the board, centred, running out to straight grain at
           both edges (sqrt(across^2 + depth^2), not a V)
  quarter  pith far off one edge in the board's mid plane: rings at 90 deg to the face, straight stripes, ray fleck on oak
  rift     pith about 45 deg off a corner: straight lines on all four faces (legs, rails, stiles)
Sapwood is the rings beyond the heart radius, so its edge follows a ring and the figure runs straight through it.
End grain is the same rings seen end on, darker and crisper. Pores are streaks along the grain, in the earlywood
for ring-porous ash and oak.

  import woodlib as W
  lam = W.board(P_part_in, grain=(1, 0, 0), cut='flat', species='walnut', seed=7)   # JSON-able, store it with the part
  rgb = W.color(P_in, N, lam)                                                        # sRGB 0..1 per point
  W.stamp('walnut', 'flat')  ->  'woodlib:walnut/flat@2026-11-26.1+<hash>'           # tag every material you make
Positions in inches. scripts/solid_wood.py keeps its old API (stack / stave / panel / solid laminations) on top of this.
"""
import hashlib, json, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
# the table ships with hardwood-furniture-cad; copies of this file in other skills find it there
WOODS = next(p for p in [os.environ.get('WOODLIB_JSON'), os.path.join(HERE, '..', 'references', 'woods.json'),
                         os.path.join(HERE, '..', '..', 'hardwood-furniture-cad', 'references', 'woods.json')] if p and os.path.exists(p))
LIB = json.load(open(WOODS))
_code = open(os.path.abspath(__file__), 'rb').read()
VERSION = LIB['version'] + '+' + hashlib.sha256(json.dumps(LIB['species'], sort_keys=True).encode()).hexdigest()[:8]
CUTS = ('flat', 'quarter', 'rift')


def species(name):
    """Species record (aliases resolved). Unknown species raise: never fall back to a guessed colour."""
    k = (name or 'walnut').lower().strip()
    k = LIB['aliases'].get(k, k)
    if k not in LIB['species']:
        raise KeyError(f'woodlib: no species {name!r}; add it to references/woods.json (one of {sorted(LIB["species"])})')
    return k, LIB['species'][k]


def target(sp):
    """The colour the library aims for (median/p10/p90, sRGB): an approved "look" when the client picked one over
    the photo (walnut: the PM case reel's walnut), else the photo measurement."""
    _, S = species(sp)
    return S.get('look') or S.get('photo')


def stamp(sp, cut='auto', finish='oil'):
    return f'woodlib:{species(sp)[0]}/{cut}/{finish}@{VERSION}'


def srgb2lin(c):
    c = np.asarray(c, float); return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin2srgb(c):
    c = np.clip(np.asarray(c, float), 0, 1); return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


# ---------------- noise ----------------
_rng = np.random.default_rng(1234)
_PERM = np.tile(_rng.permutation(256), 2)
_GRAD = np.array([[1, 1, 0], [-1, 1, 0], [1, -1, 0], [-1, -1, 0], [1, 0, 1], [-1, 0, 1], [1, 0, -1], [-1, 0, -1],
                  [0, 1, 1], [0, -1, 1], [0, 1, -1], [0, -1, -1], [1, 1, 0], [-1, 1, 0], [0, -1, 1], [0, -1, -1]], float)


def h1(k, s):
    """A fixed random number in 0..1 per (index, seed)."""
    x = np.asarray(k, np.float64) * 1.37 + 0.5 + np.asarray(s, np.float64) * 3.11 * 1013.0
    v = np.sin(np.floor(x * 1000.0) * 12.9898 + 78.233) * 43758.5453
    return v - np.floor(v)


def perlin(x, y, z):
    """Improved Perlin gradient noise, signed, about -1..1."""
    x, y, z = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float), np.asarray(z, float))
    xi, yi, zi = np.floor(x), np.floor(y), np.floor(z)
    xf, yf, zf = x - xi, y - yi, z - zi
    xi, yi, zi = xi.astype(np.int64) & 255, yi.astype(np.int64) & 255, zi.astype(np.int64) & 255
    f = lambda t: t * t * t * (t * (t * 6 - 15) + 10)
    u, v, w = f(xf), f(yf), f(zf)

    def g(ix, iy, iz, dx, dy, dz):
        G = _GRAD[_PERM[_PERM[_PERM[ix] + iy] + iz] & 15]
        return G[..., 0] * dx + G[..., 1] * dy + G[..., 2] * dz
    X1, Y1, Z1 = (xi + 1) & 255, (yi + 1) & 255, (zi + 1) & 255
    l = lambda a, b, t: a + t * (b - a)
    x00 = l(g(xi, yi, zi, xf, yf, zf), g(X1, yi, zi, xf - 1, yf, zf), u)
    x10 = l(g(xi, Y1, zi, xf, yf - 1, zf), g(X1, Y1, zi, xf - 1, yf - 1, zf), u)
    x01 = l(g(xi, yi, Z1, xf, yf, zf - 1), g(X1, yi, Z1, xf - 1, yf, zf - 1), u)
    x11 = l(g(xi, Y1, Z1, xf, yf - 1, zf - 1), g(X1, Y1, Z1, xf - 1, yf - 1, zf - 1), u)
    return l(l(x00, x10, v), l(x01, x11, v), w)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a + 1e-12), 0, 1); return t * t * (3 - 2 * t)


# ---------------- boards ----------------
def part_frame(P, grain=None):
    """u (grain), v (wide), w (thin) unit axes, centre and sizes of a part from its points (any units).
    grain: 'x'|'y'|'z' or a vector; else the longest side (the smaller of the PCA box and the axis box, as look.py)."""
    P = np.asarray(P, float); c0 = (P.min(0) + P.max(0)) / 2
    if isinstance(grain, str):
        u = np.eye(3)['xyz'.index(grain)]
    elif grain is not None:
        u = np.asarray(grain, float); u = u / np.linalg.norm(u)
    else:
        C = P - P.mean(0); w_, V = np.linalg.eigh(np.cov(C.T)); V = V[:, np.argsort(w_)[::-1]]
        ext_p, ext_a = np.ptp(C @ V, 0), np.ptp(P, 0)
        Ax = np.eye(3)[:, np.argsort(ext_a)[::-1]] if np.prod(ext_a + 1e-9) <= np.prod(ext_p + 1e-9) * 1.02 else V
        u = Ax[:, 0]
    # the two cross axes: the part's own (PCA of the points projected across the grain), wide first
    Q = (P - P.mean(0)); Q = Q - np.outer(Q @ u, u)
    h = np.eye(3)[np.argmin(np.abs(u))]; e1 = np.cross(u, h); e1 /= np.linalg.norm(e1); e2 = np.cross(u, e1)
    best = None
    for ang in np.linspace(0, np.pi / 2, 91):          # min-area box across the grain (boards are boxes)
        a = np.cos(ang) * e1 + np.sin(ang) * e2; b = np.cross(u, a)
        ea, eb = np.ptp(Q @ a), np.ptp(Q @ b)
        if best is None or ea * eb < best[0] - 1e-12: best = (ea * eb, a, b, ea, eb)
    _, a, b, ea, eb = best
    v, w = (a, b) if ea >= eb else (b, a)
    if abs(v[np.argmax(np.abs(v))]) > 0 and v[np.argmax(np.abs(v))] < 0: v = -v
    w = np.cross(u, v)
    c = c0 if grain is None else P.min(0) + (P.max(0) - P.min(0)) / 2
    return dict(origin=c, u=u, v=v, w=w, L=float(np.ptp(P @ u)), W=float(np.ptp(P @ v)), T=float(np.ptp(P @ w)),
                mid=[float(np.mean([(P @ x).min(), (P @ x).max()])) for x in (u, v, w)])


import re as _re
FRAME = _re.compile(r'(?i)(leg|post|rail|stile|mullion|muntin|apron|stretcher|frame|batten|breadboard|cleat|runner|kicker|spline|key|peg|dowel|tenon|handle)')


def auto_cut(W, T, name=''):
    """Frame members and small stock are rift (straight on all faces: cathedral on a stile or leg reads as wrong
    grain); boards (thin for their width) are flat sawn so their wide faces show cathedrals."""
    if name and FRAME.search(name): return 'rift'
    return 'flat' if (T < W / 3 and W > 2.5) else 'rift'


def board(P, grain=None, cut='auto', species_name='walnut', seed=0, sap=None, finish='oil', frame=None, name='', up=(0, 0, 1), **kw):
    """Board parameters for a part (P in inches). JSON-able: store it with the part (GLB extras, object props).
    sap: None (heart only), 'edge' (a ring of sapwood along the +v edge), or a heart radius in inches.
    up: the piece's up direction in P's space. On a part whose grain stands upright (case sides, doors, panels)
    the flat-sawn cathedral arches point UP, as a maker sets them; upside-down arches read as wrong at once
    (client review, 26 Nov 2026). Pass up=None to leave the direction to the seed."""
    sk, S = species(species_name)
    F = frame or part_frame(P, grain)
    W, T = max(F['W'], 0.05), max(F['T'], 0.05)
    cut = auto_cut(W, T, name) if cut in (None, 'auto') else cut
    if cut not in CUTS: raise ValueError(f'cut {cut!r}: one of {CUTS} or auto')
    hh = lambda i: float(h1(i, seed))
    D = S['flat_depth_in'] * (0.8 + 0.4 * hh(1))
    if cut == 'flat':
        v0 = W * 0.08 * (hh(2) - 0.5); w0 = -(T / 2 + D)
        tv, tw = 0.004 * (hh(3) - 0.5), S['taper'] * (0.8 + 0.4 * hh(4))
        # the arch apex points to where the pith lies deepest under the face, i.e. along -sign(tw) * u
        uz = float(np.dot(F['u'], np.asarray(up, float) / np.linalg.norm(up))) if up is not None else 0.0
        if abs(uz) > 0.6: tw = -abs(tw) * np.sign(uz)
    elif cut == 'quarter':
        v0 = -(W / 2 + 1.6 * D); w0 = T * 0.15 * (hh(2) - 0.5)
        tv, tw = 0.01 * (0.5 + hh(3)), 0.003 * (hh(4) - 0.5)
    else:   # rift: pith 35..55 deg off a corner
        ang = np.radians(35 + 20 * hh(2)); R = 1.6 * D
        v0 = -(W / 2) - R * np.cos(ang); w0 = -(T / 2) - R * np.sin(ang)
        tv, tw = 0.006 * (hh(3) - 0.5), 0.006 * (hh(4) - 0.5)
    # heart only unless asked: the heart radius sits beyond the farthest corner of the section
    corners = [(sv * W / 2, sw * T / 2) for sv in (-1, 1) for sw in (-1, 1)]
    rmax = max(np.hypot(cv - v0, cw - w0) for cv, cw in corners) + abs(tv) * F['L'] + abs(tw) * F['L']
    rh = rmax + 2.0
    if sap == 'edge':     # put the heart/sap boundary 0.4..1.1 in inside the +v edge on the show face
        ev = W / 2 - (0.4 + 0.7 * hh(6))
        rh = float(np.hypot(ev - v0, T / 2 - w0))
    elif isinstance(sap, (int, float)):
        rh = float(sap)
    u0 = F['L'] * 0.25 * (hh(7) - 0.5)     # where along the board the pith sits deepest (cathedral apexes move)
    lam = dict(mode='board', species=sk, cut=cut, finish=finish, seed=int(seed),
               origin=[float(x) for x in F['origin']], u=[float(x) for x in F['u']], v=[float(x) for x in F['v']], w=[float(x) for x in F['w']],
               pith=[float(v0), float(w0)], tilt=[float(tv), float(tw)], u0=float(u0), rh=float(rh), size=[F['L'], W, T],
               woodlib=stamp(sk, cut, finish), name=name)
    lam.update(kw)
    return lam


def apex(lam):
    """Unit vector (in the board's space) the flat-sawn cathedral apexes point along, or None for quarter/rift."""
    if lam.get('cut') != 'flat': return None
    return [float(x) for x in -np.sign(lam['tilt'][1]) * np.asarray(lam['u'], float)]


def board_extras(lam, sk=None):
    """Material extras for a baked part: the stamp, plus the cathedral apex direction (model frame, Z up) and the
    bookmatch partner, so the lint can fail upside-down cathedrals and unmatched door pairs in any GLB."""
    sk = sk or lam.get('species', 'walnut')
    ex = {'woodlib': stamp(sk, lam.get('cut', lam.get('mode')), lam.get('finish', 'oil'))}
    ap = apex(lam) if lam.get('mode') == 'board' else None
    if ap is not None: ex['woodlib_apex'] = [round(x, 3) for x in ap]
    if lam.get('bookmatch'): ex['woodlib_match'] = lam['bookmatch'] if isinstance(lam['bookmatch'], str) else True
    if lam.get('name'): ex['woodlib_part'] = lam['name']
    return ex


def check_boards(boards, up=(0, 0, 1)):
    """boards: {part name: extras or board}. Fails: WOODAPEX (an upright flat-sawn part with its cathedrals
    pointing down) and WOODMATCH (a ..._L/_R door or panel pair, both flat sawn, not bookmatched)."""
    up = np.asarray(up, float); fails = []
    def apx(b): return b.get('woodlib_apex') or (apex(b) if 'tilt' in b else None)
    def cut(b): return b.get('cut') or (parse_stamp(b.get('woodlib', '')) or [None, None])[1]
    for n, b in boards.items():
        ap = apx(b)
        if ap is not None and float(np.dot(ap, up)) < -0.6:
            fails.append(('WOODAPEX', n, 'cathedral arches point down on an upright part: they must point up'))
        m = pair_name(n)
        if m in boards and n < m and cut(b) == 'flat' == cut(boards[m]) and not (b.get('woodlib_match') or b.get('bookmatch')
                                                                                 or boards[m].get('woodlib_match') or boards[m].get('bookmatch')):
            fails.append(('WOODMATCH', f'{n} + {m}', 'a door/panel pair not bookmatched: bake with web_laminate --all (or woodlib_bl.apply_all)'))
    return fails


BOOKMATCH = _re.compile(r'(?i)(door|panel|leaf|lid|front)')


def pair_name(name):
    """The bookmatch partner of a part named ..._L / ..._R (Door_Board_L <-> Door_Board_R), else None."""
    m = _re.match(r'(.*[_ .-])([LR])$', name or '')
    return (m.group(1) + {'L': 'R', 'R': 'L'}[m.group(2)]) if m and BOOKMATCH.search(name) else None


def bookmatch(lam_a, P_a, P_b, name=''):
    """Board for leaf b, bookmatched to leaf a: the two leaves are one board resawn and opened like a book, so b is
    a's grain mirrored across the joint between them (cathedrals meet at the joint as one symmetric figure).
    P_a, P_b: the two parts' points in the same space as lam_a."""
    P_a, P_b = np.asarray(P_a, float), np.asarray(P_b, float)
    u = np.asarray(lam_a['u'], float)
    d = P_b.mean(0) - P_a.mean(0)
    va = np.asarray(lam_a['v'], float)            # the leaves sit side by side across their width (v)
    if abs(d @ va) < 0.5 * np.linalg.norm(d - (d @ u) * u) or np.linalg.norm(d) < 1e-6: return None
    n = va * np.sign(d @ va)
    j = 0.5 * ((P_a @ n).max() + (P_b @ n).min())          # the joint plane: between a's far edge and b's near edge
    ref_p = lambda x: x - 2 * (x @ n - j) * n
    ref_v = lambda x: x - 2 * (x @ n) * n
    lam = json.loads(json.dumps(lam_a))
    o = ref_p(np.asarray(lam_a['origin'], float))
    for k in ('u', 'v', 'w'): lam[k] = [float(x) for x in ref_v(np.asarray(lam_a[k], float))]
    # show face onto show face: if b sits a hair proud of a or higher up, the figure moves with it. The flat-sawn
    # figure shifts ~1/taper in along the grain per inch of depth (2 mm proud put the arches 2 in apart), so match
    # the leaves' own centres across the face (w) and along the grain (u), not only the mirror plane
    cb = (P_b.min(0) + P_b.max(0)) / 2; ca = ref_p((P_a.min(0) + P_a.max(0)) / 2)
    for k in ('u', 'w'):
        ax = np.asarray(lam[k], float); o = o + ((cb - ca) @ ax) * ax
    lam['origin'] = [float(x) for x in o]
    lam['bookmatch'] = lam_a.get('name', '') or True
    if name: lam['name'] = name
    return lam


def board_coords(P, lam):
    """g (along the grain from the part centre), r (distance to the pith), theta, in inches."""
    P = np.asarray(P, float)
    o, u, v, w = (np.asarray(lam[k], float) for k in ('origin', 'u', 'v', 'w'))
    if 'mid' in lam: o = o  # origin already the box centre
    Q = P - o
    g, a, b = Q @ u, Q @ v, Q @ w
    gu = g - lam.get('u0', 0.0)
    dv = a - (lam['pith'][0] + lam['tilt'][0] * gu)
    dw = b - (lam['pith'][1] + lam['tilt'][1] * gu)
    return g, np.hypot(dv, dw), np.arctan2(dw, dv), a, b


def color(P, N, lam, species_name=None, finish=None, linear=False):
    """sRGB 0..1 (or linear) per point, for a board made by board(). N: surface normals (for end grain)."""
    sk, S = species(species_name or lam.get('species', 'walnut'))
    fin = finish or lam.get('finish', 'oil')
    P = np.asarray(P, float); N = np.asarray(N, float)
    N = N / (np.linalg.norm(N, axis=1, keepdims=True) + 1e-12)
    seed = float(lam.get('seed', 0))
    lod = float(lam.get('lod', 0.0))     # inches per sample (a web bake's texel): detail finer than ~3 samples fades out
    fade = lambda freq: 1.0 - float(smoothstep(0.12, 0.33, freq * lod))
    g, r, th, a, b = board_coords(P, lam)
    # ring position: the log's rings wander slowly along the board and round the log (cathedral arches wobble)
    wa = S.get('wander', 1.0)
    rw = (r + wa * 0.20 * perlin(g * 0.035 + seed * 7.1, th * 1.3, r * 0.12) + wa * 0.07 * perlin(g * 0.11, th * 4.0 + seed, r * 0.4)
          + S.get('ring_jag', 0.015) * fade(2.0) * perlin(g * 0.6, th * 20.0, r * 2.0))
    rpi = S['rings_per_in'] * float(lam.get('ring_scale', 1.0))
    # uneven rings: each year's width differs (a term that varies ring to ring, not a smooth stretch)
    ring = rw * rpi + 0.45 * perlin(rw * rpi * 0.23, th * 0.6, seed * 0.37) + 0.12 * perlin(rw * rpi * 0.9, th * 1.5, 5.0 + seed)
    f = ring - np.floor(ring)
    lf, ls = S['late_frac'], S['late_soft']
    # within a ring: earlywood light, darkening gradually into the latewood, sharp edge at the ring boundary
    late = smoothstep(1 - lf - ls, 1 - 0.25 * lf, f) ** 1.3 * (1 - smoothstep(0.975, 1.0, f))
    u = np.asarray(lam['u'], float)
    endg = np.abs(N @ u)
    e = smoothstep(0.55, 0.92, endg)
    late_end = smoothstep(1 - lf - 0.3 * ls, 1 - lf + 0.1 * ls, f) * (1 - smoothstep(0.985, 1.0, f))
    late = late * (1 - e) + late_end * e                       # end grain: the same rings, crisper
    # ring-to-ring strength: some years show strong latewood, some faint
    rb = S.get('ring_break', 0.45)     # and each ring line fades in and out along the board (walnut's are diffuse)
    late = late * ((1 - rb) + rb * smoothstep(-0.4, 0.5, perlin(np.floor(ring) * 0.37 + seed, g * S.get('ring_fade', 0.0), th * 0.3)))
    # flat-sawn apex: where the face runs tangent to a ring the latewood spreads into a broad dark flame; real
    # boards show it, but soft (the dark wedges read as painted on the PM case card, 26 Nov 2026)
    asf = S.get('apex_soft', 0.0)
    if asf > 0:
        tg = np.abs(np.cos(th) * (N @ np.asarray(lam['v'], float)) + np.sin(th) * (N @ np.asarray(lam['w'], float)))
        late = late * (1 - asf * smoothstep(0.9, 0.995, tg) * (1 - e))
    A = S['albedo']
    early, latec = srgb2lin(A['early']), srgb2lin(A['late'])
    c = early[None] + (latec - early)[None] * late[:, None]
    # fibre: fine streaks along the grain, and broad figure patches, so no band reads as flat paint
    fib = 1 + S.get('fibre', 0.07) * fade(9.0) * perlin(g * 0.25 + seed, a * 9.0, b * 9.0) + 0.09 * perlin(g * 0.06, a * 1.6 + seed, b * 1.6)
    c = c * fib[:, None]
    # sapwood: rings beyond the heart radius (its edge is a ring), figure runs through it
    rh = float(lam.get('rh', S['heart_radius_in']))
    sm = smoothstep(rh - 0.2, rh + 0.25, rw + 0.25 * perlin(g * 0.05 + 3.3, th * 2.0, seed))
    if np.any(sm > 0):
        se, sl = srgb2lin(A['sap']), srgb2lin(A['sap_late'])
        cs = se[None] + (sl - se)[None] * late[:, None]
        c = c * (1 - sm[:, None]) + cs * sm[:, None]
    # pores: streaks along the grain; ring-porous species carry them in the earlywood band
    ps = S['pore_scale']
    pn = perlin(g * 0.9 / ps + seed, a * 22 / ps, b * 22 / ps)
    pm = smoothstep(0.15, 0.6, pn)
    por = S['porosity']
    zone = {'ring': 1 - smoothstep(0.0, 0.22, f), 'semi': 0.55 + 0.45 * (1 - smoothstep(0.0, 0.4, f))}.get(por, np.full_like(f, 0.5))
    pore = 1 - S['pores'] * fade(22.0 / ps) * zone * pm * (1 - 0.5 * e)
    # long colour streaks (walnut's mineral streaks), slow tone wander, one tone per board
    st = 1 + S['streak'] * perlin(g * 0.025 + seed, a * 0.7, b * 0.7) + S.get('streak_fine', 0.0) * perlin(g * 0.04 + 2 * seed, a * 3.2, b * 3.2)
    bt = 1 + S['board_tone'] * 2 * (h1(7, seed) - 0.5)
    shade = pore * st * bt * (1 - S['end_dark'] * e)
    c = c * shade[:, None]
    # oak ray fleck: on faces that look across the rays (quarter faces), short light flakes
    if S.get('rays', 0) > 0:
        rad = np.stack([np.cos(th), np.sin(th)], 1)            # radial direction in (v, w)
        nv, nw = N @ np.asarray(lam['v'], float), N @ np.asarray(lam['w'], float)
        tang = np.abs(nv * -rad[:, 1] + nw * rad[:, 0])         # face normal along the tangent = quarter face
        fl = smoothstep(0.45, 0.7, perlin(g * 1.1 + seed, th * 140.0, rw * 0.9)) * smoothstep(0.6, 0.95, tang) * (1 - e)
        c = c * (1 + S['rays'] * 0.45 * fl)[:, None]
    fz = LIB['finishes'].get(fin, LIB['finishes']['oil'])
    if fin == 'char':
        c = srgb2lin(fz['albedo'])[None] * (0.85 + 0.3 * late[:, None] * 0 + 0.15 * pm[:, None])
    elif fin == 'raw':
        lum = (c @ [0.2126, 0.7152, 0.0722])[:, None]
        c = (c + (lum - c) * fz.get('desat', 0.25)) * fz.get('albedo_gain', 1.12)
    c = np.clip(c, 0, 1)
    return c if linear else lin2srgb(c)


def roughness(sp, finish='oil'):
    _, S = species(sp); fz = LIB['finishes'].get(finish, {})
    return fz.get('roughness') or S['roughness'] + fz.get('roughness_add', 0.0)


def house_gain(sp, studio):
    """Linear RGB albedo gain a house studio needs for this species so its tonemapper lands on the photo
    (woodlib_calibrate.py writes them; (1, 1, 1) if never calibrated)."""
    g = LIB.get('house', {}).get(studio, {}).get(species(sp)[0], {}).get('gain', 1.0)
    return [float(g)] * 3 if isinstance(g, (int, float)) else [float(x) for x in g]


def parse_stamp(st):
    """'woodlib:walnut/flat/oil@ver' -> (species, cut, finish, version), or None."""
    if not isinstance(st, str) or not st.startswith('woodlib:'): return None
    body, _, ver = st[8:].partition('@'); parts = body.split('/') + ['oil', 'oil']
    return parts[0], parts[1], parts[2], ver


def swatch(sp='walnut', cut='flat', size=(24.0, 8.0, 0.75), res=(960, 320), seed=3, finish='oil', sap=None):
    """A flat render of the board's wide face (and its end strip), sRGB uint8 image array, for sheets and checks."""
    L, W, T = size
    Pbox = np.array([[x, y, z] for x in (-L / 2, L / 2) for y in (-W / 2, W / 2) for z in (-T / 2, T / 2)])
    lam = board(Pbox, grain='x', cut=cut, species_name=sp, seed=seed, sap=sap, finish=finish)
    X, Y = np.meshgrid(np.linspace(-L / 2, L / 2, res[0]), np.linspace(W / 2, -W / 2, res[1]))
    P = np.stack([X.ravel(), Y.ravel(), np.full(X.size, T / 2)], 1)
    Nn = np.tile([0, 0, 1.0], (len(P), 1))
    img = color(P, Nn, lam).reshape(res[1], res[0], 3)
    return (img * 255).astype(np.uint8), lam


if __name__ == '__main__':
    import argparse
    from PIL import Image
    ap = argparse.ArgumentParser(description='woodlib swatch sheet: every species x cut, plus the photo target chip')
    ap.add_argument('out'); ap.add_argument('--species', nargs='*', default=['walnut', 'ash', 'white oak'])
    a = ap.parse_args()
    rows = []
    for sp in a.species:
        tiles = []
        for cut, sap in (('flat', None), ('flat', 'edge'), ('quarter', None), ('rift', None)):
            im, _ = swatch(sp, cut, sap=sap, res=(720, 240)); tiles.append(im); tiles.append(np.full((240, 8, 3), 255, np.uint8))
        ph = LIB['species'][species(sp)[0]].get('photo')
        chip = np.full((240, 120, 3), 255, np.uint8)
        if ph: chip[:] = (np.array(ph['median']) * 255).astype(np.uint8)
        rows.append(np.hstack(tiles + [chip])); rows.append(np.full((8, rows[-1].shape[1], 3), 255, np.uint8))
    Image.fromarray(np.vstack(rows)).save(a.out)
    print('woodlib', VERSION, '->', a.out)
