#!/usr/bin/env python3
"""SUPERSEDED (2026-11-23): use scripts/web_grain_check.py to check, and hardwood-furniture-cad scripts/web_glb.py
to build furniture GLBs. This script missed merged parts and exempted textures by name.

Re-map the UVs of every wood part so the grain runs along the part.

Procedural grain (object or generated coordinates) doesn't survive a GLB export, and an
auto-unwrap or box projection lays a baked grain texture diagonally or across the part.
This projects each face onto its own plane with U along the part's long axis (found by PCA,
so parts set at an angle work), scaled so one texture repeat covers L metres along the grain
and keeps the image's aspect across it. Each part gets a random offset so parts don't repeat.
Run glb_grain_check.py on the result.

  blender -b -P glb_regrain.py -- in.glb out.glb [L metres, default 0.5]
  WOOD="(?i)ash|oak" (env) picks the wood materials; default ash|oak|walnut|maple|cherry|wood|ply|birch
"""
import sys as _s
if '--' in _s.argv: _s.argv=[_s.argv[0]]+_s.argv[_s.argv.index('--')+1:]
import os,bpy,bmesh,sys,numpy as np,random,mathutils,re
src,dst=sys.argv[1],sys.argv[2]
L=float(sys.argv[3]) if len(sys.argv)>3 else 0.5   # metres of grain per texture repeat along U
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
def img_of(m):
    for nd in (m.node_tree.nodes if m and m.node_tree else []):
        if nd.type=='TEX_IMAGE' and nd.image and nd.image.size[0]: return nd.image
random.seed(7); n=0
for o in bpy.data.objects:
    if o.type!='MESH': continue
    ims=[img_of(m) for m in o.data.materials if m and re.search(os.environ.get('WOOD',r'(?i)ash|oak|walnut|maple|cherry|wood|ply|birch'),m.name)]
    ims=[i for i in ims if i]
    if not ims: continue
    asp=ims[0].size[0]/ims[0].size[1]
    me=o.data; M=o.matrix_world
    P=np.array([(M@v.co)[:] for v in me.vertices])
    C=P-P.mean(0)
    # long axis by PCA of the vertex cloud (handles parts set at an angle, e.g. roof stiles)
    w,v=np.linalg.eigh(np.cov(C.T)); g=v[:,np.argmax(w)]
    # prefer the bbox extent along the principal axes
    ext=[np.ptp(C@v[:,k]) for k in range(3)]; g=v[:,int(np.argmax(ext))]
    g=mathutils.Vector(g).normalized()
    bm=bmesh.new(); bm.from_mesh(me); uvl=bm.loops.layers.uv.active or bm.loops.layers.uv.new()
    ou,ov=random.random(),random.random()
    for f in bm.faces:
        nrm=(M.to_3x3()@f.normal).normalized()
        a=g if abs(nrm.dot(g))<0.9 else (mathutils.Vector((0,0,1)) if abs(nrm.z)<0.9 else mathutils.Vector((1,0,0)))
        a=(a-nrm*a.dot(nrm)).normalized(); b=nrm.cross(a).normalized()
        for l in f.loops:
            p=M@l.vert.co
            if asp>=1: l[uvl].uv=(p.dot(a)/L+ou, p.dot(b)/(L/asp)+ov)   # wide image: grain along U
            else:      l[uvl].uv=(p.dot(b)/(L*asp)+ou, p.dot(a)/L+ov)   # tall image: grain along V
    bm.to_mesh(me); bm.free(); n+=1
print('regrained',n,'parts')
bpy.ops.export_scene.gltf(filepath=dst,export_format='GLB',export_image_format='AUTO')
