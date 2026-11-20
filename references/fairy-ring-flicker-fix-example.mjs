// Lift decals/screens off the surfaces they sit on, and pull flush internal panels inside the skin.
import { NodeIO, getBounds } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { MeshoptDecoder } from 'meshoptimizer';
await MeshoptDecoder.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder});
const doc=await io.read(process.argv[2]);
// [regex on node name, lift in mm along the face normal pointing away from the reference group's centre, reference regex]
const LIFT=[
 [/^ultrawide_lg_34wq650w_lg_lg_glass_black/,1.5,/^ultrawide_lg_34wq650w_lg_lg_white_back/],
 [/^ultrawide_lg_34wq650w_lg_lg_screen/,3.0,/^ultrawide_lg_34wq650w_lg_lg_white_back/],
 [/^ultrawide_lg_34wq650w_lg_port_black/,0.6,/^ultrawide_lg_34wq650w_lg_lg_screen/],
 [/^camwall_monitor_mb16acv_zen_zen_glass_black/,1.5,/^camwall_monitor_mb16acv_zen_zen_dark_grey/],
 [/^camwall_monitor_mb16acv_zen_zen_screen/,3.0,/^camwall_monitor_mb16acv_zen_zen_dark_grey/],
 [/^camwall_monitor_mb16acv_zen_zen_logo/,0.6,/^camwall_monitor_mb16acv_zen_zen_screen/],
 [/^fr_controls_\w+_legends_/,0.8,/^fr_controls_\w+_plate_white_mask/],
 [/^fr_controls_look_fr_look_lcd_screen/,0.8,null,[0,1,0]],
 [/^fr_controls_\w+_acrylic_clear/,0.4,/^fr_controls_\w+_plate_white_mask/],
 [/^fr_controls_\w+_led_(?!tray)/,0.6,/^fr_controls_\w+_plate_white_mask/],
 [/^fr_controls_shape_fr_shape_knob_engraving/,0.8,/^fr_controls_shape_fr_shape_plate_white_mask/],
 [/^camwall_tray_acrylic_7dc6e8/,0.6,/^camwall_monitor_mb16acv_zen_zen_dark_grey/],
 [/^dji_pocket3_screen/,0.8,/^dji_osmo_pocket3_/],
 [/^dji_pocket3_bezel/,0.5,/^dji_osmo_pocket3_/],
];
const nodes=doc.getRoot().listNodes();
const centre=re=>{let lo=[1e9,1e9,1e9],hi=[-1e9,-1e9,-1e9],k=0;for(const n of nodes)if(n.getMesh()&&re.test(n.getName())){const b=getBounds(n);lo=lo.map((x,i)=>Math.min(x,b.min[i]));hi=hi.map((x,i)=>Math.max(x,b.max[i]));k++}return k?lo.map((x,i)=>(x+hi[i])/2):null;};
const inv3=m=>{const [a,b,c,d,e,f,g,h,i]=[m[0],m[4],m[8],m[1],m[5],m[9],m[2],m[6],m[10]];const det=a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g);
 return [[(e*i-f*h)/det,(c*h-b*i)/det,(b*f-c*e)/det],[(f*g-d*i)/det,(a*i-c*g)/det,(c*d-a*f)/det],[(d*h-e*g)/det,(b*g-a*h)/det,(a*e-b*d)/det]];};
const xf=(M,p)=>[0,1,2].map(r=>M[r]*p[0]+M[4+r]*p[1]+M[8+r]*p[2]+M[12+r]);
const done=new Set();
function moveNode(n,off){ // off: world-space vector
 const M=n.getWorldMatrix();const I=inv3(M);const lo=[0,1,2].map(r=>I[r][0]*off[0]+I[r][1]*off[1]+I[r][2]*off[2]);
 let mesh=n.getMesh();if(mesh.listParents().filter(p=>p.propertyType==='Node').length>1){mesh=mesh.clone();n.setMesh(mesh);}
 for(const p of mesh.listPrimitives()){let a=p.getAttribute('POSITION');if(done.has(a)){a=a.clone();p.setAttribute('POSITION',a);}done.add(a);
  const v=[];for(let i=0;i<a.getCount();i++){a.getElement(i,v);a.setElement(i,[v[0]+lo[0],v[1]+lo[1],v[2]+lo[2]]);}}}
let moved=0;
for(const [re,mm,refre,force] of LIFT){const c=refre?centre(refre):[0,0,0];if(!c){console.log('no ref',refre);continue;}
 for(const n of nodes){if(!n.getMesh()||!re.test(n.getName()))continue;
  // dominant face normal (area weighted, sign-insensitive) in world space
  const M=n.getWorldMatrix();let best=null,ba=0;const acc=new Map();
  for(const p of n.getMesh().listPrimitives()){const a=p.getAttribute('POSITION'),I=p.getIndices()?.getArray();if(!I)continue;
   for(let t=0;t<I.length;t+=3){const q=[0,1,2].map(k=>xf(M,a.getElement(I[t+k],[])));const e1=q[1].map((x,i)=>x-q[0][i]),e2=q[2].map((x,i)=>x-q[0][i]);
    let nn=[e1[1]*e2[2]-e1[2]*e2[1],e1[2]*e2[0]-e1[0]*e2[2],e1[0]*e2[1]-e1[1]*e2[0]];const L=Math.hypot(...nn);if(L<1e-12)continue;nn=nn.map(x=>x/L);
    const s=nn.find(x=>Math.abs(x)>1e-3)>0?1:-1;nn=nn.map(x=>x*s);const k=nn.map(x=>x.toFixed(2)).join(',');const r=acc.get(k)||{n:nn,a:0};r.a+=L/2;acc.set(k,r);}}
  for(const r of acc.values())if(r.a>ba){ba=r.a;best=r.n;}
  const b=getBounds(n);const mc=b.min.map((x,i)=>(x+b.max[i])/2);
  const dir=(mc[0]-c[0])*best[0]+(mc[1]-c[1])*best[1]+(mc[2]-c[2])*best[2]>=0?1:-1;
  const off=force?force.map(x=>x*mm/1000):best.map(x=>x*dir*mm/1000);moveNode(n,off);moved++;
  console.log('lift',n.getName(),mm+'mm',off.map(x=>(x*1000).toFixed(2)).join(','));}}
// floor ply sits flush with the skin's bottom and side faces: shrink it 2 mm in on every side and up 1 mm
for(const n of nodes){if(!/^floor_ply/.test(n.getName())||!n.getMesh())continue;
 const b=getBounds(n);if(b.max[0]-b.min[0]<0.5&&b.max[2]-b.min[2]<0.5&&!(b.max[0]-b.min[0]<1e-3||b.max[2]-b.min[2]<1e-3))continue;
}
// parts bolted on the outside of the case (hoods, the lid accessory rail): move each part as a whole 0.6 mm off the face it sits on
{const groups=new Map();for(const n of nodes){if(!n.getMesh())continue;const m=n.getName().match(/^(hood_[a-z_]+?|lid_accessory_rail)(?:_\d)?_[0-9a-f]{6}$/);if(!m)continue;const k=n.getName().replace(/_[0-9a-f]{6}$/,'');if(!groups.has(k))groups.set(k,[]);groups.get(k).push(n);}
 for(const [k,ns] of groups){let lo=[1e9,1e9,1e9],hi=[-1e9,-1e9,-1e9];for(const n of ns){const b=getBounds(n);lo=lo.map((x,i)=>Math.min(x,b.min[i]));hi=hi.map((x,i)=>Math.max(x,b.max[i]));}
  // case faces: x=0, x=0.96, z=0, z=-0.56 (body); lid front at the lid's outer face: use the nearest bbox face
  const cand=[[0,0,-1],[0,0.96,1],[2,0,1],[2,-0.56,-1]];
  if(k==='lid_accessory_rail'){cand.length=0;cand.push([2,(lo[2]+hi[2])/2,0]);}
  let best=null,bd=1e9;for(const [ax,v,s] of cand){const d=Math.min(Math.abs(lo[ax]-v),Math.abs(hi[ax]-v));if(d<bd){bd=d;best=[ax,s];}}
  let off=[0,0,0];
  if(k==='lid_accessory_rail'){ // rail sits on the lid's front face: move it away from the lid top panel centre along the face normal found by the coplanar check
   const c=centre(/^lid_top/);const gc=lo.map((x,i)=>(x+hi[i])/2);const d=gc.map((x,i)=>x-c[i]);const ax=[0,1,2].sort((a,b)=>Math.abs(d[b])-Math.abs(d[a]))[0];off[ax]=Math.sign(d[ax])*0.0006;}
  else off[best[0]]=best[1]*0.0006;
  for(const n of ns)moveNode(n,off);moved+=ns.length;console.log('move',k,ns.length,off.map(x=>(x*1000).toFixed(2)).join(','));}}
// internal panels flush with the skin: clamp them a little inside the case (world box)
const INSET=[[/^floor_ply/,[0.002,0.128,-0.558],[0.958,0.138,-0.002]],[/^gasket_top/,[0.001,0.766,-0.559],[0.959,0.7705,-0.001],[0,-0.001,0]],[/^(rail_(fb|lr)|post)(_\w+)?_[0-9a-f]{6}$/,[0.0035,0.1275,-0.5565],[0.9565,0.7635,-0.0035]]];
for(const [re,LO,HI,PRE] of INSET){const fl=nodes.filter(n=>n.getMesh()&&re.test(n.getName()));
 for(const n of fl){const M=n.getWorldMatrix();const I=inv3(M);let mesh=n.getMesh();if(mesh.listParents().filter(p=>p.propertyType==='Node').length>1){mesh=mesh.clone();n.setMesh(mesh);}
  for(const p of mesh.listPrimitives()){let a=p.getAttribute('POSITION');if(done.has(a)){a=a.clone();p.setAttribute('POSITION',a);}done.add(a);
   const v=[];for(let i=0;i<a.getCount();i++){a.getElement(i,v);const w=xf(M,v);
    const nw=w.map((x,k)=>Math.min(Math.max(x+(PRE?PRE[k]:0),LO[k]),HI[k]));
    const d=nw.map((x,k)=>x-w[k]);const l=[0,1,2].map(r=>I[r][0]*d[0]+I[r][1]*d[1]+I[r][2]*d[2]);a.setElement(i,[v[0]+l[0],v[1]+l[1],v[2]+l[2]]);}}
  moved++;}
 console.log('inset',re,fl.length);}
await io.write(process.argv[3],doc);console.log('moved',moved);
