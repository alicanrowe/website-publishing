#!/usr/bin/env python3
"""Reduce z-fighting: sink vertices that sit on another material's surface (and, with --delete, remove covered faces).

WARNING (19 Nov 2026): --delete tore the Moth saw blade and chisel. Thin parts made of two coincident
layers lose real faces. Leave it off, and always run glb_fidelity_check.py against the full model after.

For each mesh in turn, a face whose centre and three inner points all sit within EPS of a
surface of another mesh with a different material, with normals agreeing (dot > 0.8), is
deleted: the other surface already covers that spot, so nothing visible is lost and the two
can no longer fight for the same pixels. Meshes are processed in order and the tree is rebuilt
after each, so of two coincident surfaces only one loses its faces.
  blender -b -P glb_zfight_fix.py -- in.glb out.glb [eps metres] [--skip REGEX] [--delete]
Each mesh uses at most 0.2% of its own size as tolerance, so small parts in a big model aren't crushed.
Run glb_zfight_check.py afterwards and look at the model: a partly covered face is kept.
"""
import sys as _s
if '--' in _s.argv: _s.argv=[_s.argv[0]]+_s.argv[_s.argv.index('--')+1:]
import bpy,bmesh,sys,mathutils,re
from mathutils.bvhtree import BVHTree
DELETE='--delete' in sys.argv
sys.argv=[x for x in sys.argv if x!='--delete']
SKIP=None
if '--skip' in sys.argv:   # --skip REGEX: never move these meshes (they still count as covering surfaces)
    i=sys.argv.index('--skip'); SKIP=re.compile(sys.argv[i+1]); del sys.argv[i:i+2]
src,dst=sys.argv[1],sys.argv[2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
objs=[o for o in bpy.data.objects if o.type=='MESH' and len(o.data.polygons)]
def world_bm(o):
    bm=bmesh.new(); bm.from_mesh(o.data); bm.transform(o.matrix_world); bmesh.ops.triangulate(bm,faces=bm.faces[:]); bm.normal_update(); return bm
mn=mathutils.Vector((1e9,)*3); mx=-mn
for o in objs:
    for c in o.bound_box:
        w=o.matrix_world@mathutils.Vector(c); mn=mathutils.Vector(map(min,mn,w)); mx=mathutils.Vector(map(max,mx,w))
EPS=float(sys.argv[3]) if len(sys.argv)>3 else (mx-mn).length*0.0002
mats=lambda o: tuple(sorted({m.name for m in o.data.materials if m}))
trees={}
def tree(o):
    bm=world_bm(o); t=BVHTree.FromBMesh(bm); bb=(mathutils.Vector(map(min,*[v.co for v in bm.verts])),mathutils.Vector(map(max,*[v.co for v in bm.verts]))); bm.free(); return t,bb
for o in objs: trees[o.name]=tree(o)
# a small part gets a small tolerance: the model-wide EPS is about 0.4 mm on a 2 m case, which moved
# 20 mm tool parts by over 1 mm (crushed). Each mesh uses at most 0.2% of its own size.
def eps_of(o):
    a,b=trees[o.name][1]; return min(EPS,(b-a).length*0.002)
total=0
for o in objs:
    if SKIP and SKIP.search(o.name): continue
    others=[p for p in objs if p is not o and mats(p)!=mats(o)]
    bm=world_bm(o)  # triangulated, world space; indices match the triangulated mesh we write back
    _,bb=trees[o.name]
    near=[p for p in others if not any(bb[0][k]>trees[p.name][1][1][k]+EPS or trees[p.name][1][0][k]>bb[1][k]+EPS for k in range(3))]
    if not near: bm.free(); continue
    kill=[]
    for f in bm.faces:
        a,b,c=[v.co for v in f.verts]; ctr=(a+b+c)/3
        pts=(ctr,(ctr*2+a)/3,(ctr*2+b)/3,(ctr*2+c)/3)
        for p in near:
            t=trees[p.name][0]
            ok=True
            for q in pts:
                h=t.find_nearest(q,EPS)
                if h[0] is None or f.normal.dot(h[1])<=0.8: ok=False; break
            if ok: kill.append(f); break
    if kill and DELETE:
        total+=len(kill)
        bmesh.ops.delete(bm,geom=kill,context='FACES')
        bm.transform(o.matrix_world.inverted())
        bm.to_mesh(o.data); o.data.update()
        trees[o.name]=tree(o)
        print(f'{o.name}: removed {len(kill)} covered face(s)')
    bm.free()
print(f'eps {EPS*1000:.3f} mm, {total} covered face(s) removed')
# Second pass for partly covered faces: sink the vertices that sit on another material's surface
# (facing the same way) inward by 3*EPS, so the covering surface always wins the depth test.
moved=0
for o in objs:
    if SKIP and SKIP.search(o.name): continue
    e=eps_of(o)
    others=[p for p in objs if p is not o and mats(p)!=mats(o)]
    _,bb=trees[o.name]
    near=[p for p in others if not any(bb[0][k]>trees[p.name][1][1][k]+EPS or trees[p.name][1][0][k]>bb[1][k]+EPS for k in range(3))]
    if not near: continue
    me=o.data; mw=o.matrix_world; nmw=mw.to_3x3().inverted().transposed(); inv=mw.inverted()
    me.calc_normals_split() if hasattr(me,'calc_normals_split') else None
    n=0
    for v in me.vertices:
        w=mw@v.co; nw=(nmw@v.normal).normalized()
        for p in near:
            h=trees[p.name][0].find_nearest(w,e)
            if h[0] is not None and nw.dot(h[1])>0.8:
                v.co=inv@(w-nw*3*e); n+=1; break
    if n:
        me.update(); trees[o.name]=tree(o); moved+=n
        print(f'{o.name}: sank {n} vertex(es)')
print(f'{moved} vertex(es) sunk below a covering surface')
bpy.ops.export_scene.gltf(filepath=dst,export_format='GLB')
