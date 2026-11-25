#!/usr/bin/env python3
"""Solid (3D) wood colour, numpy port of scripts/blender/laminated_wood.py, for baking web viewer textures.

Wood is a solid, not a sticker. On a curved, twisted or swept part a 2D texture laid along the surface (an
auto-unwrap, or one UV strip following the sweep) shows one board bent into shape: the figure flows round the
twist. A real stack lamination ground to that shape shows each layer's straight grain and, where the surface cuts
through the layers at a slant, long contour bands that break at every glue line. A turned or carved solid shows
its rings where the cut crosses them. The only way to get that is to evaluate the wood in 3D at every surface
point, which is what this does, with the same modes and parameters as the Cycles shader, so the viewer matches the
renders:

  stack  horizontal layers of thickness t from z0, grain along axis x|y   (stack-laminated planks, seats, tops)
  stave  n vertical staves round (cx, cy), middle at radius rm, grain up  (coopered drums, columns, curved backs)
  panel  edge-glued boards of width t across the part, grain along axis    (discs, seat blanks, table tops)
  solid  one board, grain along axis x|y|z or a vector, rings round origin (pegs, keys, braces, rails, turned parts)

Positions are in inches, model frame, Z up (the CAD frame the renders use). Output is sRGB 0..1.

  from solid_wood import wood_color
  rgb = wood_color(P_in, N, dict(mode='stack', t=0.875, z0=17.6, axis='x', seed=3), species='walnut')
"""
import numpy as np

SPECIES = {   # oiled colour (sRGB 0..1), same table as web_glb.py
    "walnut": (0.40, 0.29, 0.22), "cherry": (0.62, 0.38, 0.25), "white oak": (0.70, 0.56, 0.39),
    "red oak": (0.74, 0.55, 0.40), "ash": (0.80, 0.70, 0.54), "hard maple": (0.85, 0.74, 0.58),
    "mahogany": (0.55, 0.30, 0.20), "sapele": (0.52, 0.30, 0.20), "pine": (0.82, 0.68, 0.46),
    "cedar": (0.66, 0.43, 0.30), "baltic birch": (0.84, 0.74, 0.58),
}
MODES = ('stack', 'stave', 'panel', 'solid')
AX = {'x': 0, 'y': 1, 'z': 2}

_rng = np.random.default_rng(1234)
_PERM = np.tile(_rng.permutation(256), 2)
_GRAD = np.array([[1, 1, 0], [-1, 1, 0], [1, -1, 0], [-1, -1, 0], [1, 0, 1], [-1, 0, 1], [1, 0, -1], [-1, 0, -1],
                  [0, 1, 1], [0, -1, 1], [0, 1, -1], [0, -1, -1], [1, 1, 0], [-1, 1, 0], [0, -1, 1], [0, -1, -1]], float)


def h1(k, s):
    """cellnoise stand-in: a fixed random number in 0..1 per (board index, seed)."""
    x = np.asarray(k, np.float64) * 1.37 + 0.5 + np.asarray(s, np.float64) * 3.11 * 1013.0
    v = np.sin(np.floor(x * 1000.0) * 12.9898 + 78.233) * 43758.5453
    return v - np.floor(v)


def perlin(x, y, z):
    """Improved Perlin gradient noise, signed, about -1..1."""
    xi, yi, zi = np.floor(x), np.floor(y), np.floor(z)
    xf, yf, zf = x - xi, y - yi, z - zi
    xi, yi, zi = xi.astype(np.int64) & 255, yi.astype(np.int64) & 255, zi.astype(np.int64) & 255
    f = lambda t: t * t * t * (t * (t * 6 - 15) + 10)
    u, v, w = f(xf), f(yf), f(zf)

    def g(ix, iy, iz, dx, dy, dz):
        h = _PERM[_PERM[_PERM[ix] + iy] + iz] & 15
        G = _GRAD[h]
        return G[..., 0] * dx + G[..., 1] * dy + G[..., 2] * dz
    X1, Y1, Z1 = (xi + 1) & 255, (yi + 1) & 255, (zi + 1) & 255
    l = lambda a, b, t: a + t * (b - a)
    x00 = l(g(xi, yi, zi, xf, yf, zf), g(X1, yi, zi, xf - 1, yf, zf), u)
    x10 = l(g(xi, Y1, zi, xf, yf - 1, zf), g(X1, Y1, zi, xf - 1, yf - 1, zf), u)
    x01 = l(g(xi, yi, Z1, xf, yf, zf - 1), g(X1, yi, Z1, xf - 1, yf, zf - 1), u)
    x11 = l(g(xi, Y1, Z1, xf, yf - 1, zf - 1), g(X1, Y1, Z1, xf - 1, yf - 1, zf - 1), u)
    return l(l(x00, x10, v), l(x01, x11, v), w)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)


def board_coords(P, N, lam):
    """Per point: board index k, along-grain g, across a, through b, distance to nearest glue line gl,
    end-grain-ness (|normal . grain|), and the grain direction (unit, model frame)."""
    mode = lam.get('mode', 'solid'); axk = lam.get('axis', 'x' if mode != 'stave' else 'z')
    ax = AX[axk] if isinstance(axk, str) else 0
    t = float(lam.get('t', 0.875)); z0 = float(lam.get('z0', 0.0))
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    n = N / (np.linalg.norm(N, axis=1, keepdims=True) + 1e-12)
    gdir = np.zeros_like(P)
    if mode in ('stack', 'panel'):
        if ax == 2: raise ValueError(f'{mode}: grain axis must be x or y')
        c = z if mode == 'stack' else (y if ax == 0 else x)
        uu = (c - z0) / t; k = np.floor(uu); f = uu - k
        gl = np.minimum(f, 1 - f) * t
        g = x if ax == 0 else y
        a = (y if ax == 0 else x) if mode == 'stack' else z
        b = c - (k + 0.5) * t - z0
        gdir[:, ax] = 1
    elif mode == 'stave':
        nst = int(lam.get('n', 16)); cx, cy, rm = float(lam.get('cx', 0)), float(lam.get('cy', 0)), float(lam.get('rm', 0))
        dx, dy = x - cx, y - cy
        th = np.arctan2(dy, dx); s = (th + np.pi) / (2 * np.pi) * nst
        k = np.floor(s); f = s - k; r = np.hypot(dx, dy)
        gl = np.minimum(f, 1 - f) * (2 * np.pi / nst) * r
        tc = -np.pi + (k + 0.5) * 2 * np.pi / nst
        a = -dx * np.sin(tc) + dy * np.cos(tc)
        b = dx * np.cos(tc) + dy * np.sin(tc) - rm
        g = z; ax = 2; gdir[:, 2] = 1
    elif mode == 'solid':
        u = np.asarray(lam['axis'], float) if isinstance(lam.get('axis'), (list, tuple)) else np.eye(3)[ax]
        u = u / np.linalg.norm(u); h = np.eye(3)[np.argmin(np.abs(u))]
        v = np.cross(u, h); v /= np.linalg.norm(v); w = np.cross(u, v)
        o = np.asarray(lam.get('origin', [0, 0, 0]), float)   # a point on the part's axis: the log's pith sits off it
        g, a, b = (P - o) @ u, (P - o) @ v, (P - o) @ w
        k = np.zeros(len(P)); gl = np.full(len(P), 1e6); gdir[:] = u
        return k, g, a, b, gl, np.abs(n @ u), gdir
    else:
        raise ValueError(f'unknown lamination mode {mode!r} (one of {MODES})')
    endg = np.abs(n[:, ax])
    return k, g, a, b, gl, endg, gdir


def wood_value(P, N, lam):
    """Linear-ish lightness 0..1 per point plus a per-board tone factor and glue/end shading, as in the shader."""
    seed = float(lam.get('seed', 1)); rings = float(lam.get('rings', 2.2)); tone = float(lam.get('tone', 0.2))
    glue = float(lam.get('glue', 0.04))
    k, g, a, b, gl, endg, _ = board_coords(P, N, lam)
    pa = (h1(k, seed) - 0.5) * 6.0
    pb = np.where(h1(k, seed + 1) < 0.5, -1.0, 1.0) * (3.0 + 5.0 * h1(k, seed + 2))
    if lam.get('mode') == 'stave': pb = -(5.0 + 4.0 * h1(k, seed + 2))
    cone = 0.012 + 0.02 * h1(k, seed + 3)
    rr = rings * (0.8 + 0.4 * h1(k, seed + 4))
    d = np.hypot(a - pa, b - pb)
    d = d + 0.35 * perlin(g * 0.06 + k * 13.1, a * 0.25, b * 0.25)
    d = d + cone * g + 0.03 * perlin(g * 0.15, a * 1.5 + k, b * 1.5)
    ring = d * rr; fr = ring - np.floor(ring)
    late = smoothstep(0.55, 0.95, fr) * (1 - smoothstep(0.95, 1.0, fr))
    figure = 0.5 + 0.5 * perlin(g * 0.02 + k * 5.3, d * 0.8, np.zeros_like(d))
    val = np.clip(0.08 + 0.62 * (1 - late) * (0.45 + 0.55 * figure), 0, 1)
    tv = 1 + tone * 2 * (h1(k, seed + 5) - 0.5) * 2
    hue = (h1(k, seed + 6) - 0.5) * 0.12
    # pores: streaks along the grain (coarser than the shader's: a web texel is ~0.04 in)
    pf = float(lam.get('pore_freq', 5.0)); pw = float(lam.get('pores', 0.05))
    pore = perlin(g * pf / 20, a * pf, b * pf)
    pm = smoothstep(0.05, 0.45, pore)
    shade = ((1 - pw) + pw * pm) * (1 - 0.38 * smoothstep(0.6, 0.95, endg)) * (1 - 0.55 * (1 - smoothstep(0.0, glue, gl)))
    return val, tv, hue, shade


def wood_color(P, N, lam, species='walnut', contrast=None):
    """sRGB 0..1, mean tone near the species' oiled colour (web_glb.py SPECIES)."""
    val, tv, hue, shade = wood_value(np.asarray(P, float), np.asarray(N, float), lam)
    base = np.array(lam.get('rgb') or SPECIES.get(species, SPECIES['walnut']))   # rgb: keep a model's own tone
    lin = np.where(base <= 0.04045, base / 12.92, ((base + 0.055) / 1.055) ** 2.4)
    dark, light = lin * 0.30, lin * 1.05      # latewood to earlywood; tung oil: darker, low contrast (renders)
    contrast = float(lam.get('contrast', 0.65)) if contrast is None else contrast
    val = 0.45 + contrast * (val - 0.45)
    c = dark[None] + (light - dark)[None] * val[:, None]
    c = c * (tv * shade)[:, None] * np.stack([1 + hue, np.ones_like(hue), 1 - hue], 1)
    if lam.get('rgb'):      # keep the model's own tone: the median comes out on its colour
        c = c * (lin @ [0.2126, 0.7152, 0.0722]) / (np.median(c @ [0.2126, 0.7152, 0.0722]) + 1e-9)
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def grain_dir(P, N, lam):
    """Unit grain direction per point (model frame), before projecting into the surface."""
    return board_coords(np.asarray(P, float), np.asarray(N, float), lam)[6]
