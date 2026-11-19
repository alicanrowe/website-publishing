#!/usr/bin/env python3
"""Compare a web (lite) GLB with the full model it was cut from, part by part.

Simplifying, decimating or "fixing" a model can crush thin parts, shatter them into shards or
tear holes, and none of that shows at the default viewer distance. This samples points over each
part of the full model and finds the nearest surface of the same part in the lite model, and the
other way round. A hole or a missing piece shows as full-model points far from the lite surface;
shards and crushed shapes show as lite points far from the full surface.

  blender -b -P glb_fidelity_check.py -- full.glb lite.glb [--tol 0.01] [--only REGEX]
Decode meshopt first (npx @gltf-transform/cli copy lite.glb plain.glb). Parts are matched by
node name (Blender suffixes like .001 and gltfpack's Mesh_N children use the parent's name).
FAIL a part when the 98th percentile distance either way is over tol x the part's size
(default 1%), with an absolute floor of 0.2 mm. A part missing from the lite model also FAILs.
"""
import sys as _s
if '--' in _s.argv: _s.argv=[_s.argv[0]]+_s.argv[_s.argv.index('--')+1:]
import bpy,bmesh,sys,re,random,mathutils
from mathutils.bvhtree import BVHTree
a=sys.argv[1:]; full,lite=a[0],a[1]
tol=float(a[a.index('--tol')+1]) if '--tol' in a else 0.01
only=re.compile(a[a.index('--only')+1]) if '--only' in a else None
def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=path)
    parts={}
    for o in bpy.data.objects:
        if o.type!='MESH' or not len(o.data.polygons): continue
        n=o.name
        q=o
        while re.match(r'^(Mesh_\d+|mesh\d*|)(\.\d+)?$',n) and q.parent: q=q.parent; n=q.name
        n=re.sub(r'\.\d+$','',n)
        bm=bmesh.new(); bm.from_mesh(o.data); bm.transform(o.matrix_world); bmesh.ops.triangulate(bm,faces=bm.faces[:])
        tris=[[v.co.copy() for v in f.verts] for f in bm.faces]; bm.free()
        parts.setdefault(n,[]).extend(tris)
    return parts
def sample(tris,n=1500):
    areas=[((b-a).cross(c-a)).length/2 for a,b,c in tris]; tot=sum(areas) or 1
    out=[]; rnd=random.Random(1)
    for (a,b,c),ar in zip(tris,areas):
        k=ar/tot*n; m=int(k)+(1 if rnd.random()<k-int(k) else 0)
        for _ in range(m):
            u,v=rnd.random(),rnd.random()
            if u+v>1: u,v=1-u,1-v
            out.append(a+(b-a)*u+(c-a)*v)
    return out
def tree(tris):
    verts=[];faces=[]
    for t in tris: i=len(verts); verts+=t; faces.append((i,i+1,i+2))
    return BVHTree.FromPolygons(verts,faces)
def size(tris):
    P=[p for t in tris for p in t]; mn=mathutils.Vector(map(min,*P)); mx=mathutils.Vector(map(max,*P)); return (mx-mn).length
def p98(xs): xs=sorted(xs); return xs[int(len(xs)*.98)] if xs else 0
F=load(full); L=load(lite)
bad=0; checked=0
for n,tris in sorted(F.items()):
    if only and not only.search(n): continue
    checked+=1
    if n not in L: bad+=1; print(f'MISSING {n}'); continue
    s=size(tris); lim=max(tol*s,0.0002)
    tf,tl=tree(tris),tree(L[n])
    d1=p98([(tl.find_nearest(p)[0]-p).length for p in sample(tris)])      # full -> lite: holes, lost pieces
    d2=p98([(tf.find_nearest(p)[0]-p).length for p in sample(L[n])])     # lite -> full: shards, crushed shapes
    if d1>lim or d2>lim:
        bad+=1; print(f'FAIL {n}: size {s*1000:.1f} mm, full->lite {d1*1000:.2f} mm (holes/lost), lite->full {d2*1000:.2f} mm (shards/crushed), limit {lim*1000:.2f} mm')
extra=[n for n in L if n not in F and (not only or only.search(n))]
if extra: print('only in the lite model:',', '.join(extra[:20]))
print(f'{checked} parts checked, {bad} failed' if bad else f'{checked} parts checked, every part matches the full model')
sys.exit(1 if bad else 0)
