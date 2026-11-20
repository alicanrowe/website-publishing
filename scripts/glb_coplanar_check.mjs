// glb_coplanar_check.mjs: list every pair of parts whose faces lie on top of each other (the cause of z-fighting).
// Usage: node glb_coplanar_check.mjs model.glb [eps_m=0.0008] [rows=60]   (npm i @gltf-transform/core @gltf-transform/extensions meshoptimizer)
// World space, EXT_mesh_gpu_instancing expanded, meshopt decoded. Same-facing faces, and opposite-facing ones when the material
// is double-sided (a double-sided panel back-to-back with another fights from the side you can see). Rows: overlap area, closest gap,
// a point on it, and the two parts (node/material). Run it on the FULL model (node names intact), not the gltfpack output, which
// merges parts and loses names. Pairs of the same colour (white skin on white skin) do not show; anything else under ~0.5 mm will.
// Fast: buckets faces by normal, plane offset and a 5 cm cell, so 420k triangles take ~6 s.
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { MeshoptDecoder } from 'meshoptimizer';
await MeshoptDecoder.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder});
const doc=await io.read(process.argv[2]);const EPS=+(process.argv[3]||0.0008);
const mul=(m,p)=>[m[0]*p[0]+m[4]*p[1]+m[8]*p[2]+m[12],m[1]*p[0]+m[5]*p[1]+m[9]*p[2]+m[13],m[2]*p[0]+m[6]*p[1]+m[10]*p[2]+m[14]];
function compose(t,r,s){const [x,y,z,w]=r;const m=[1-2*(y*y+z*z),2*(x*y+z*w),2*(x*z-y*w),0,2*(x*y-z*w),1-2*(x*x+z*z),2*(y*z+x*w),0,2*(x*z+y*w),2*(y*z-x*w),1-2*(x*x+y*y),0,t[0],t[1],t[2],1];for(let i=0;i<3;i++)for(let j=0;j<3;j++)m[i*4+j]*=s[i];return m;}
function mm(a,b){const o=new Array(16).fill(0);for(let c=0;c<4;c++)for(let r=0;r<4;r++)for(let k=0;k<4;k++)o[c*4+r]+=a[k*4+r]*b[c*4+k];return o;}
const tris=[];let pid=0;
for(const node of doc.getRoot().listNodes()){const mesh=node.getMesh();if(!mesh)continue;
 const W=node.getWorldMatrix();let inst=[W];
 const ext=node.getExtension('EXT_mesh_gpu_instancing');
 if(ext){const T=ext.getAttribute('TRANSLATION'),R=ext.getAttribute('ROTATION'),S=ext.getAttribute('SCALE');const n=(T||R||S).getCount();inst=[];
  for(let i=0;i<n;i++)inst.push(mm(W,compose(T?T.getElement(i,[]):[0,0,0],R?R.getElement(i,[]):[0,0,0,1],S?S.getElement(i,[]):[1,1,1])));}
 for(const prim of mesh.listPrimitives()){const pos=prim.getAttribute('POSITION');const I=prim.getIndices()?.getArray();if(!I)continue;
  const mat=prim.getMaterial();const blend=mat?.getAlphaMode()==='BLEND';const ds=!!mat?.getDoubleSided();
  inst.forEach((M,ii)=>{const id=pid++;const label=(node.getName()||'?')+'/'+(mat?.getName()||'')+(inst.length>1?'#'+ii:'');
   for(let t=0;t<I.length;t+=3){const p=[0,1,2].map(k=>mul(M,pos.getElement(I[t+k],[])));
    const e1=p[1].map((x,i)=>x-p[0][i]),e2=p[2].map((x,i)=>x-p[0][i]);
    let n=[e1[1]*e2[2]-e1[2]*e2[1],e1[2]*e2[0]-e1[0]*e2[2],e1[0]*e2[1]-e1[1]*e2[0]];const L=Math.hypot(...n);if(L<1e-10)continue;n=n.map(x=>x/L);if(ds){const s0=n.find(x=>Math.abs(x)>1e-3)>0?1:-1;n=n.map(x=>x*s0);}
    tris.push({id,label,blend,ds,p,n,d:n[0]*p[0][0]+n[1]*p[0][1]+n[2]*p[0][2],area:L/2});}});}}
console.error('tris',tris.length);

// bucket by normal (quantized) + plane offset + coarse in-plane cell (5 cm)
const CELL=0.05;
const B=new Map();
for(const [i,t] of tris.entries()){const nq=t.n.map(x=>Math.round(x*50)).join(',');const dq=Math.round(t.d/EPS);
 const ax=[0,1,2].sort((x,y)=>Math.abs(t.n[x])-Math.abs(t.n[y])).slice(0,2);t.ax=ax;
 const lo=ax.map(a=>Math.min(...t.p.map(q=>q[a]))),hi=ax.map(a=>Math.max(...t.p.map(q=>q[a])));t.lo=lo;t.hi=hi;
 const c0=lo.map(x=>Math.floor(x/CELL)),c1=hi.map(x=>Math.floor(x/CELL));
 if((c1[0]-c0[0]+1)*(c1[1]-c0[1]+1)>400){c0[0]=c1[0]=c0[1]=c1[1]=-99999;}
 for(let u=c0[0];u<=c1[0];u++)for(let v=c0[1];v<=c1[1];v++){const k=nq+'|'+dq+'|'+u+','+v;if(!B.has(k))B.set(k,[]);B.get(k).push(i);}}
function proj(t,ax){return t.p.map(q=>[q[ax[0]],q[ax[1]]]);}
function inTri(P,a,b,c){const s=(p,q,r)=>(p[0]-r[0])*(q[1]-r[1])-(q[0]-r[0])*(p[1]-r[1]);const d1=s(P,a,b),d2=s(P,b,c),d3=s(P,c,a);return !((d1<0||d2<0||d3<0)&&(d1>0||d2>0||d3>0));}
const pairs=new Map();const done=new Set();
for(const [k,list] of B){const [nq,dq,cell]=k.split('|');
 const cand=[...list];for(const o of [-1,1]){const l2=B.get(nq+'|'+(+dq+o)+'|'+cell);if(l2)cand.push(...l2);}
 if(cand.length<2)continue;
 for(const i of list)for(const j of cand){if(i===j)continue;const a=tris[i],b=tris[j];if(a.id===b.id)continue;
  const pk=i<j?i*1e7+j:j*1e7+i;if(done.has(pk))continue;done.add(pk);
  if(a.n[0]*b.n[0]+a.n[1]*b.n[1]+a.n[2]*b.n[2]<0.9995)continue;if(Math.abs(a.d-b.d)>EPS)continue;
  if(a.hi[0]<b.lo[0]||b.hi[0]<a.lo[0]||a.hi[1]<b.lo[1]||b.hi[1]<a.lo[1])continue;
  const ax=a.ax;const A=proj(a,ax),Bp=proj(b,ax);
  let hit=0,tot=0;for(const [u,v] of [[.33,.33],[.1,.1],[.8,.1],[.1,.8],[.45,.45],[.6,.2],[.2,.6]]){for(const [X,Y] of [[A,Bp],[Bp,A]]){tot++;const P=[X[0][0]+u*(X[1][0]-X[0][0])+v*(X[2][0]-X[0][0]),X[0][1]+u*(X[1][1]-X[0][1])+v*(X[2][1]-X[0][1])];if(inTri(P,...Y))hit++;}}
  if(!hit)continue;
  const lk=[a.label,b.label].sort().join('  <>  ');const r=pairs.get(lk)||{area:0,gap:1,c:null};r.area+=Math.min(a.area,b.area)*hit/tot;r.gap=Math.min(r.gap,Math.abs(a.d-b.d));r.c=a.p[0].map(x=>+x.toFixed(3));pairs.set(lk,r);}}
const out=[...pairs].sort((x,y)=>y[1].area-x[1].area);
for(const [k,r] of out.slice(0,+(process.argv[4]||60)))console.log((r.area*1e4).toFixed(2).padStart(8),'cm2 gap',(r.gap*1000).toFixed(3),'mm at',JSON.stringify(r.c),' ',k);
console.log('pairs',out.length);
