#!/usr/bin/env python3
"""Z-fighting check: surfaces of different materials that lie on top of each other.

Samples every triangle (centre plus three inner points) of each mesh and finds the nearest
surface of every other mesh with a different material (BVH). A sample is a clash when the gap
is under EPS and the two surfaces face the same way (normal dot > 0.8): the GPU
can't tell which is in front and they shimmer as the camera moves. Faces pressed together
(normals opposite, two parts touching) are hidden by the parts themselves and are not counted. Hidden geometry inside
another solid shows up too (a core inside a sleeve), and that's often the real cause.
EPS defaults to 0.02% of the model's size (about the depth precision of a web viewer).

  blender -b -P glb_zfight_check.py -- model.glb [eps metres]
  python3 glb_zfight_check.py model.glb      # with the bpy module
Meshopt-compressed GLBs: decode first (npx @gltf-transform/cli copy in.glb plain.glb).
Exit 1 when any pair clashes over more than 1% of the smaller mesh's samples.
"""
import sys as _s
if '--' in _s.argv: _s.argv=[_s.argv[0]]+_s.argv[_s.argv.index('--')+1:]
import bpy,bmesh,sys,mathutils
from mathutils.bvhtree import BVHTree
glb=sys.argv[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
objs=[o for o in bpy.data.objects if o.type=='MESH' and len(o.data.polygons)]
mn=mathutils.Vector((1e9,)*3); mx=-mn
data={}
for o in objs:
    bm=bmesh.new(); bm.from_mesh(o.data); bm.transform(o.matrix_world); bmesh.ops.triangulate(bm,faces=bm.faces[:])
    bm.normal_update()
    for v in bm.verts: mn=mathutils.Vector(map(min,mn,v.co)); mx=mathutils.Vector(map(max,mx,v.co))
    samples=[]
    for f in bm.faces:
        a,b,c=[v.co.copy() for v in f.verts]; ctr=(a+b+c)/3
        for p in (ctr,(ctr*2+a)/3,(ctr*2+b)/3,(ctr*2+c)/3): samples.append((p,f.normal.copy()))
    mats=tuple(sorted({m.name for m in o.data.materials if m}))
    bb=[mathutils.Vector(map(min,*[v.co for v in bm.verts])), mathutils.Vector(map(max,*[v.co for v in bm.verts]))] if len(bm.verts) else None
    data[o.name]=(BVHTree.FromBMesh(bm),samples,mats,bb)
    bm.free()
size=(mx-mn).length
EPS=float(sys.argv[2]) if len(sys.argv)>2 else size*0.0002
bad=0
names=list(data)
for i,a in enumerate(names):
    ta,sa,ma,ba=data[a]
    for b in names[i+1:]:
        tb,sb,mb,bbb=data[b]
        if ma==mb or not ba or not bbb: continue
        if any(ba[0][k]>bbb[1][k]+EPS or bbb[0][k]>ba[1][k]+EPS for k in range(3)): continue
        def clash(samples,tree):
            n=0
            for p,nr in samples:
                hit=tree.find_nearest(p,EPS)
                if hit[0] is not None and nr.dot(hit[1])>0.8: n+=1
            return n
        ca,cb=clash(sa,tb),clash(sb,ta)
        frac=max(ca/len(sa),cb/len(sb))
        if frac>0.01:
            bad+=1; print(f'ZFIGHT {a} [{",".join(ma)}] / {b} [{",".join(mb)}]: {ca}/{len(sa)} and {cb}/{len(sb)} samples within {EPS*1000:.3f} mm')
print(f'{len(objs)} meshes, model {size:.3f} m, eps {EPS*1000:.3f} mm: {bad} clashing pair(s)' if bad else f'{len(objs)} meshes, model {size:.3f} m, eps {EPS*1000:.3f} mm: no z-fighting')
sys.exit(1 if bad else 0)
