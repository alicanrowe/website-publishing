#!/usr/bin/env node
// flicker_render_check.mjs: render a GLB the way the site's viewer does, turn the camera in tiny steps,
// and find pixels that flip back and forth between frames. That is what a person sees as flicker
// (z-fighting, coplanar decals, transparent sorting, a far/near depth range that is too wide).
// A static geometry check can miss it or drown it in false hits; this one looks at the pixels.
//
//   node scripts/flicker_render_check.mjs --site <site repo> model.glb \
//        [--orbit "30deg 72deg 3.8m"] [--target "0.24m 0.72m -0.12m"] [--size 900x900] \
//        [--angles 12] [--step 0.15] [--zoom 1,0.45] [--out dir] [--max 60]
//   --page /robotics : read src/orbit/target/maxorbit from every .ar3d / .g3d viewer on a built page instead
//
// Every view is shot at --angles camera headings round the model, and at each heading 5 frames
// --step degrees apart. A pixel "flickers" when it changes by more than 1/6 of full scale one way
// and then back the other way within those 5 frames. Smooth motion never reverses that fast.
// Clusters of flicker pixels are reported with their place in the frame and saved as a red overlay
// (<out>/flicker-<view>-<heading>.png). Exit 1 if any heading has more than --max flicker pixels.
// --zoom 1,0.45 also checks from 45% of the orbit distance (close-ups show what a far view hides).
// Needs: playwright (preinstalled), pngjs (npm i pngjs).
import { createRequire } from 'node:module';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawnSync } from 'node:child_process';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
let PNG; try { PNG = require('pngjs').PNG; } catch { PNG = createRequire(path.join(process.cwd(), 'x.js'))('pngjs').PNG; }

const a = process.argv.slice(2);
const opt = (k, d) => { const i = a.indexOf(k); if (i < 0) return d; const v = a[i + 1]; a.splice(i, 2); return v; };
const site = path.resolve(opt('--site', '.'));
const orbit0 = opt('--orbit', '');
const target = opt('--target', '');
const [W, H] = opt('--size', '900x900').split('x').map(Number);
const N = +opt('--angles', '12');
const STEP = +opt('--step', '0.15');
const zooms = opt('--zoom', '1,0.45').split(',').map(Number);
const out = path.resolve(opt('--out', 'flicker-check'));
const MAX = +opt('--max', '60');
const pageUrl = opt('--page', '');
const TH = 255 / 6;
fs.mkdirSync(out, { recursive: true });

// Serve the site's static folder (vendor model-viewer, GLBs), plus the built dist when --page is used.
let root = path.join(site, 'static');
if (pageUrl) {
  const dist = path.join(os.tmpdir(), 'ar-site-dist-flicker');
  const r = spawnSync('python3', [path.join(site, 'tools/build.py')], { env: { ...process.env, SITE_OUT: dist }, stdio: 'inherit' });
  if (r.status !== 0) { console.error('build failed'); process.exit(2); }
  root = dist;
}
const extra = new Map();
const types = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.glb': 'model/gltf-binary', '.wasm': 'application/wasm', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.hdr': 'application/octet-stream' };
const server = http.createServer((req, res) => {
  const p = decodeURIComponent(req.url.split('?')[0]);
  if (extra.has(p)) { const [f, t] = extra.get(p); res.writeHead(200, { 'content-type': t }); return fs.createReadStream(f).pipe(res); }
  let f = path.join(root, p);
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, 'index.html');
  if (!fs.existsSync(f) && fs.existsSync(f + '.html')) f += '.html';
  if (!fs.existsSync(f)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'content-type': types[path.extname(f)] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
}).listen(0);
const base = `http://127.0.0.1:${server.address().port}`;
const mvjs = fs.readdirSync(path.join(site, 'static/assets/vendor')).find(f => /^model-viewer.*\.js$/.test(f));
const meshopt = fs.readdirSync(path.join(site, 'static/assets/vendor')).find(f => /^meshopt_decoder.*\.js$/.test(f));

// The views to check
let views = [];
if (pageUrl) {
  const b = await chromium.launch(); const p = await b.newPage();
  await p.goto(base + pageUrl);
  views = await p.$$eval('.ar3d,[data-model]', els => els.map(e => ({ src: e.dataset.src || e.dataset.model, orbit: e.dataset.orbit || '', target: e.dataset.target || '', maxorbit: e.dataset.maxorbit || '', exposure: e.dataset.exposure || '1.05', env: e.dataset.env || 'neutral' })));
  await b.close();
  const seen = new Set(); views = views.filter(v => v.src && !seen.has(v.src + v.orbit) && seen.add(v.src + v.orbit));
} else {
  for (const g of a) { const f = path.resolve(g); const u = '/__check/' + path.basename(f); extra.set(u, [f, 'model/gltf-binary']); views.push({ src: u, orbit: orbit0, target, maxorbit: 'auto auto 100m', exposure: '1.05', env: 'neutral' }); }
}
if (!views.length) { console.error('no models to check'); process.exit(2); }

const html = v => `<!doctype html><meta charset=utf-8><style>html,body{margin:0;background:#f4f2ee}model-viewer{width:${W}px;height:${H}px;display:block;--poster-color:transparent}</style>
<script>self.ModelViewerElement={meshoptDecoderLocation:'/assets/vendor/${meshopt}'}</script>
<script type=module src="/assets/vendor/${mvjs}"></script>
<model-viewer id=mv src="${v.src}" shadow-intensity="0.9" shadow-softness="1" exposure="${v.exposure}" environment-image="${v.env}"
 interaction-prompt="none" ${v.orbit ? `camera-orbit="${v.orbit}"` : ''} ${v.target ? `camera-target="${v.target}"` : ''} ${v.maxorbit ? `max-camera-orbit="${v.maxorbit}"` : ''} interpolation-decay="1"></model-viewer>`;

const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
let failed = 0;
for (const [vi, v] of views.entries()) {
  const name = path.basename(v.src).replace(/\.glb.*$/, '');
  extra.set('/__check.html', [path.join(out, '_page.html'), 'text/html']);
  fs.writeFileSync(path.join(out, '_page.html'), html(v));
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  await page.goto(base + '/__check.html');
  await page.waitForFunction(() => { const m = document.getElementById('mv'); return m && m.loaded; }, null, { timeout: 180000 });
  const start = await page.evaluate(() => { const o = document.getElementById('mv').getCameraOrbit(); return { t: o.theta * 180 / Math.PI, p: o.phi * 180 / Math.PI, r: o.radius }; });
  let worst = 0;
  for (const z of zooms) for (let k = 0; k < N; k++) {
    const th = start.t + k * 360 / N, frames = [];
    for (let s = 0; s < 5; s++) {
      await page.evaluate(async ([t, p, r]) => { const m = document.getElementById('mv'); m.cameraOrbit = `${t}deg ${p}deg ${r}m`; m.jumpCameraToGoal();
        for (let i = 0; i < 4; i++) await new Promise(q => requestAnimationFrame(q)); }, [th + s * STEP, start.p, start.r * z]);
      frames.push(PNG.sync.read(await page.locator('#mv').screenshot()));
    }
    const { data, width, height } = frames[2]; const flick = new Uint8Array(width * height); let n = 0;
    for (let i = 0; i < width * height; i++) {
      let hit = false;
      for (let c = 0; c < 3 && !hit; c++) for (let s = 1; s < 4 && !hit; s++) {
        const d1 = frames[s].data[i * 4 + c] - frames[s - 1].data[i * 4 + c], d2 = frames[s + 1].data[i * 4 + c] - frames[s].data[i * 4 + c];
        if (Math.abs(d1) > TH && Math.abs(d2) > TH && Math.sign(d1) !== Math.sign(d2)) hit = true;
      }
      if (hit) { flick[i] = 1; n++; }
    }
    // drop lone pixels (an edge crossing a pixel centre can reverse once); keep pixels with a flickering neighbour
    let kept = 0; const keep = new Uint8Array(width * height); let bx = [width, height, 0, 0];
    for (let y = 1; y < height - 1; y++) for (let x = 1; x < width - 1; x++) { const i = y * width + x; if (!flick[i]) continue;
      if (flick[i - 1] + flick[i + 1] + flick[i - width] + flick[i + width] >= 1) { keep[i] = 1; kept++; bx = [Math.min(bx[0], x), Math.min(bx[1], y), Math.max(bx[2], x), Math.max(bx[3], y)]; } }
    worst = Math.max(worst, kept);
    const label = `${name} z${z} heading ${Math.round(k * 360 / N)}`;
    if (kept > MAX) {
      const o = new PNG({ width, height }); data.copy(o.data);
      for (let i = 0; i < width * height; i++) if (keep[i]) { o.data[i * 4] = 255; o.data[i * 4 + 1] = 0; o.data[i * 4 + 2] = 0; }
      const f = path.join(out, `flicker-${name}-z${z}-${Math.round(k * 360 / N)}.png`); fs.writeFileSync(f, PNG.sync.write(o));
      console.log(`FLICKER ${label}: ${kept} px in box x${bx[0]}-${bx[2]} y${bx[1]}-${bx[3]} -> ${f}`);
    }
  }
  console.log(`${worst > MAX ? 'FAIL' : 'ok  '} ${name} (orbit ${v.orbit || 'auto'}): worst heading ${worst} flicker px (limit ${MAX})`);
  if (worst > MAX) failed++;
  await page.close();
}
await browser.close(); server.close();
process.exit(failed ? 1 : 0);
