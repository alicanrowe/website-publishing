#!/usr/bin/env python3
"""Replace one material's base-colour texture in a GLB with a recoloured copy that keeps its grain.

  python3 scripts/glb_recolor_texture.py model.glb Raw_Ash --light 222,213,195 --dark 194,178,152

Used when a web GLB carries a texture that doesn't match the finish the project page describes
(the Moth case is raw white ash on the site, but its export carried a near-black ash texture).
The texture's grain becomes a blend between --light and --dark; all other data is left alone,
meshopt-compressed buffer views included.
"""
import argparse, io, json, struct
import numpy as np
from PIL import Image
ap = argparse.ArgumentParser(); ap.add_argument('glb'); ap.add_argument('material')
ap.add_argument('--light', default='222,213,195'); ap.add_argument('--dark', default='194,178,152')
A = ap.parse_args()
light = np.array([float(x) for x in A.light.split(',')], np.float32); dark = np.array([float(x) for x in A.dark.split(',')], np.float32)
b = open(A.glb, 'rb').read(); l = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20 + l])
o = 20 + l; bl = struct.unpack('<I', b[o:o + 4])[0]; bin_ = bytearray(b[o + 8:o + 8 + bl]); rest = b[o + 8 + bl:]
mats = [m for m in j['materials'] if m.get('name', '').startswith(A.material)]
assert mats, f'no material starting {A.material}'
tex = mats[0]['pbrMetallicRoughness']['baseColorTexture']['index']
vi = j['images'][j['textures'][tex]['source']]['bufferView']; bv = j['bufferViews'][vi]
off, n = bv.get('byteOffset', 0), bv['byteLength']
g = np.asarray(Image.open(io.BytesIO(bytes(bin_[off:off + n]))).convert('L')).astype(np.float32)
lo, hi = np.percentile(g, 2), np.percentile(g, 98); g = np.clip((g - lo) / max(hi - lo, 1), 0, 1)
rgb = light[None, None] * (1 - g[..., None]) + dark[None, None] * g[..., None]
buf = io.BytesIO(); Image.fromarray(rgb.astype(np.uint8)).save(buf, 'JPEG', quality=82); new = buf.getvalue()
pad = lambda x: (x + 3) // 4 * 4
delta = pad(len(new)) - pad(n)
bin_ = bin_[:off] + new + b'\0' * (pad(len(new)) - len(new)) + bin_[off + pad(n):]
bv['byteLength'] = len(new)
j['images'][j['textures'][tex]['source']]['mimeType'] = 'image/jpeg'
for k, v in enumerate(j['bufferViews']):
    if k != vi and v.get('buffer', 0) == 0 and v.get('byteOffset', 0) > off: v['byteOffset'] += delta
    e = v.get('extensions', {}).get('EXT_meshopt_compression')
    if e and e.get('buffer') == 0 and e['byteOffset'] > off: e['byteOffset'] += delta
j['buffers'][0]['byteLength'] = len(bin_)
js = json.dumps(j, separators=(',', ':')).encode(); js += b' ' * ((4 - len(js) % 4) % 4)
out = struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(bin_) + len(rest)) + struct.pack('<II', len(js), 0x4E4F534A) + js + struct.pack('<II', len(bin_), 0x004E4942) + bytes(bin_) + rest
open(A.glb, 'wb').write(out); print(f'{A.glb}: {A.material} texture recoloured ({len(b)} -> {len(out)} bytes)')
