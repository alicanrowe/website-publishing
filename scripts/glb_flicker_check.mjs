// glb_flicker_check.mjs: find what makes a GLB shimmer or flicker in the site's 3D viewers.
// Usage: node glb_flicker_check.mjs model.glb [gap=0.0015]
// Needs: npm i @gltf-transform/core @gltf-transform/extensions meshoptimizer
// 1) Transparent (BLEND) materials that are double-sided: their inner faces sort per triangle and fight what's behind.
// 2) Report z-fighting risks: same-facing axis-aligned faces of different colour closer than EPS (metres-ish, after node scale) and overlapping.
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { MeshoptDecoder } from 'meshoptimizer';
await MeshoptDecoder.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder});
const doc=await io.read(process.argv[2]);const EPS=+(process.argv[3]||0.0015);
let total=0;
for(const m of doc.getRoot().listMaterials()) if(m.getAlphaMode()==='BLEND'&&m.getDoubleSided()){total++;console.log('BLEND + doubleSided material (set doubleSided false):',m.getName());}
for(const node of doc.getRoot().listNodes()){const mesh=node.getMesh();if(!mesh)continue;const sc=node.getScale();
 for(const prim of mesh.listPrimitives()){
  const pos=prim.getAttribute('POSITION'),uv=prim.getAttribute('TEXCOORD_0'),I=prim.getIndices()?.getArray();if(!I)continue;
  const faces=[];
  for(let t=0;t<I.length;t+=3){const p=[0,1,2].map(k=>pos.getElement(I[t+k],[]));
   const e1=p[1].map((x,i)=>x-p[0][i]),e2=p[2].map((x,i)=>x-p[0][i]);
   const n=[e1[1]*e2[2]-e1[2]*e2[1],e1[2]*e2[0]-e1[0]*e2[2],e1[0]*e2[1]-e1[1]*e2[0]];const L=Math.hypot(...n);if(L<1e-9)continue;
   const ax=n.findIndex(c=>Math.abs(c)/L>0.999);if(ax<0)continue;
   const o=[0,1,2].filter(i=>i!==ax);const u=uv?uv.getElement(I[t],[]):[0,0];
   faces.push({ax,s:Math.sign(n[ax]),d:p[0][ax]*sc[ax],lo:o.map(i=>Math.min(...p.map(q=>q[i]))),hi:o.map(i=>Math.max(...p.map(q=>q[i]))),c:u[0].toFixed(3),t:t/3,area:L/2});}
  const hits=new Map();
  for(let i=0;i<faces.length;i++)for(let j=i+1;j<faces.length;j++){const a=faces[i],b=faces[j];
   if(a.ax!==b.ax||a.s!==b.s||a.c===b.c||Math.abs(a.d-b.d)>EPS)continue;
   const ox=Math.min(a.hi[0],b.hi[0])-Math.max(a.lo[0],b.lo[0]),oy=Math.min(a.hi[1],b.hi[1])-Math.max(a.lo[1],b.lo[1]);
   if(ox<=1e-4||oy<=1e-4)continue;
   const k=[node.getName(),a.ax,a.s,a.c,b.c].join('|');const h=hits.get(k)||{n:0,d:[],box:null};h.n++;h.d.push(Math.abs(a.d-b.d));h.box=[a.lo,a.hi].map(v=>v.map(x=>+x.toFixed(3)));hits.set(k,h);}
  for(const [k,h] of hits){total++;console.log(k,'pairs',h.n,'gap min',Math.min(...h.d).toExponential(2),'at',JSON.stringify(h.box));}
 }}
console.log('total groups',total);
