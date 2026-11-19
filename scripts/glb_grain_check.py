#!/usr/bin/env python3
"""Grain direction check for the wood parts of a web or render GLB.

For every triangle of a wood material it finds the 3D direction in which the texture's grain
runs (the long axis of the texture image: U for a wide image, V for a tall one), and compares it
with the part's long axis as it lies on that face. End-grain faces are skipped, and so are
square-ish parts with no single grain direction. A part fails when under 80% of its face area
has grain along the part. Flat-colour wood (no texture) is noted and skipped.

  blender -b -P glb_grain_check.py -- model.glb ["material regex"]
  python3 glb_grain_check.py model.glb      # with the bpy module installed
Meshopt-compressed GLBs: decode first, `npx @gltf-transform/cli copy in.glb plain.glb`.
Exit code 1 when any part fails.
"""
import sys as _s
if '--' in _s.argv: _s.argv=[_s.argv[0]]+_s.argv[_s.argv.index('--')+1:]
# Grain direction check for wood parts in a GLB.
# For every triangle of a wood material, find the 3D direction in which the texture's grain runs
# (the long axis of the texture image, U for a wide image, V for a tall one) and compare it with
# the part's long axis. End-grain faces (normal along the long axis) are skipped.
# usage: bp grain_check.py model.glb [material regex, default ash|oak|walnut|maple|cherry|wood|ply]
import bpy,bmesh,sys,re,numpy as np,mathutils
glb=sys.argv[1]; MRX=sys.argv[2] if len(sys.argv)>2 else r'(?i)ash|oak|walnut|maple|cherry|wood|ply|birch'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
def tex_axis(mat):
    for n in (mat.node_tree.nodes if mat and mat.node_tree else []):
        if n.type=='TEX_IMAGE' and n.image and n.image.size[0]:
            return 0 if n.image.size[0]>=n.image.size[1] else 1
    return None
bad=[];tot=0
for o in sorted(bpy.data.objects,key=lambda o:o.name):
    if o.type!='MESH': continue
    mats=[m for m in o.data.materials if m and re.search(MRX,m.name)]
    if not mats: continue
    ax=tex_axis(mats[0])
    if ax is None: print('note',o.name,'has no wood texture (flat colour), skipped'); continue
    if not o.data.uv_layers: bad.append((o.name,'no UVs')); continue
    M=o.matrix_world; P=np.array([(M@v.co)[:] for v in o.data.vertices]); C=P-P.mean(0)
    w,v=np.linalg.eigh(np.cov(C.T)); ext=[np.ptp(C@v[:,k]) for k in range(3)]
    if sorted(ext)[-1] < 1.3*sorted(ext)[-2]: continue   # square-ish part: no single grain direction to check
    g=mathutils.Vector(v[:,int(np.argmax(ext))])
    bm=bmesh.new(); bm.from_mesh(o.data); bm.transform(M); uvl=bm.loops.layers.uv.active
    bmesh.ops.triangulate(bm,faces=bm.faces[:])
    ok=area=0.0
    for f in bm.faces:
        nrm=f.normal
        if abs(nrm.dot(g))>0.7: continue
        p0,p1,p2=[l.vert.co for l in f.loops]; t0,t1,t2=[l[uvl].uv for l in f.loops]
        e1,e2=p1-p0,p2-p0; d1,d2=t1-t0,t2-t0
        det=d1.x*d2.y-d1.y*d2.x
        if abs(det)<1e-12: continue
        # 3D direction of increasing U (or V)
        dU=(e1*d2.y-e2*d1.y)/det; dV=(e2*d1.x-e1*d2.x)/det
        gd=(dU if ax==0 else dV)
        if gd.length<1e-12: continue
        a=f.calc_area(); area+=a; gp=(g-nrm*g.dot(nrm)).normalized()  # the part's long axis as it lies on this face
        ok+=a*(abs(gd.normalized().dot(gp))>0.94)
    bm.free()
    if area==0: continue
    frac=ok/area; tot+=1
    if frac<0.8: bad.append((o.name,f'grain along the part on {frac*100:.0f}% of its faces'))
for n,why in bad: print('GRAIN',n,'-',why)
print(f'{tot} wood parts checked, {len(bad)} with grain across the part' if bad else f'{tot} wood parts checked, grain runs along every part')
sys.exit(1 if bad else 0)
