#!/usr/bin/env node
// Build alicanrowe.com and screenshot pages at desktop (1440) and phone (390) widths.
// Also reports console errors, failed requests, and sideways scroll on phone.
//
//   node scripts/shoot.mjs --site /path/to/alicanrowe-site --out shots/ /mouthpad /moth
//   options: --no-build  --scale 2 (for screenshots a person will see)  --only desktop|phone
//            --wait 3000 (extra ms for 3D viewers)  --prefix before-
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
// require() finds a globally installed playwright where a bare ESM import does not
const { chromium } = createRequire(import.meta.url)('playwright');

const a = process.argv.slice(2);
const opt = (k, d) => { const i = a.indexOf(k); if (i < 0) return d; const v = a[i + 1]; a.splice(i, 2); return v; };
const flag = k => { const i = a.indexOf(k); if (i < 0) return false; a.splice(i, 1); return true; };
const site = path.resolve(opt('--site', '.'));
const out = path.resolve(opt('--out', 'shots'));
const scale = Number(opt('--scale', '1'));
const only = opt('--only', '');
const wait = Number(opt('--wait', '1500'));
const prefix = opt('--prefix', '');
const noBuild = flag('--no-build');
const pages = a.length ? a : ['/'];

const dist = path.join(os.tmpdir(), 'ar-site-dist');
if (!noBuild) {
  const r = spawnSync('python3', [path.join(site, 'tools/build.py')], { env: { ...process.env, SITE_OUT: dist }, stdio: 'inherit' });
  if (r.status !== 0) { console.error('build failed'); process.exit(1); }
}
const root = noBuild && fs.existsSync(path.join(site, 'dist')) ? path.join(site, 'dist') : dist;
const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json',
  '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.gif': 'image/gif',
  '.mp4': 'video/mp4', '.webm': 'video/webm', '.glb': 'model/gltf-binary', '.ttf': 'font/ttf', '.woff2': 'font/woff2', '.ico': 'image/x-icon', '.pdf': 'application/pdf' };
const server = http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0]);
  let f = path.join(root, p);
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, 'index.html');
  if (!fs.existsSync(f)) { res.writeHead(404); return res.end('not found'); }
  res.writeHead(200, { 'content-type': types[path.extname(f).toLowerCase()] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
}).listen(0);
const base = `http://127.0.0.1:${server.address().port}`;
fs.mkdirSync(out, { recursive: true });

const sizes = [['desktop', 1440, 900], ['phone', 390, 844]].filter(s => !only || s[0] === only);
const browser = await chromium.launch();
let problems = 0;
for (const p of pages) {
  for (const [name, w, h] of sizes) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: scale, isMobile: name === 'phone', hasTouch: name === 'phone' });
    const page = await ctx.newPage();
    const issues = [];
    // model-viewer logs this for instanced meshes (EXT_mesh_gpu_instancing); the model still draws correctly
    const BENIGN = [/Mesh is missing primitive index association/];
    page.on('console', m => { if (m.type() === 'error' && !BENIGN.some(r => r.test(m.text()))) issues.push('console: ' + m.text()); });
    page.on('pageerror', e => issues.push('js error: ' + e.message));
    page.on('response', r => { if (r.status() >= 400) issues.push(`${r.status()}: ${r.url().replace(base, '')}`); });
    // pages with looping video never go network-idle: wait for load, then idle at most 10 s
    await page.goto(base + p, { waitUntil: 'load', timeout: 60000 });
    await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {});
    // scroll through so lazy images and 3D viewers load
    const H = await page.evaluate(() => document.documentElement.scrollHeight);
    for (let y = 0; y < H; y += h * 0.8) { await page.evaluate(v => window.scrollTo(0, v), y); await page.waitForTimeout(120); }
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(wait);
    const sideways = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    if (sideways > 1) issues.push(`page scrolls sideways by ${sideways}px`);
    const broken = await page.evaluate(() => [...document.images].filter(i => i.complete && i.naturalWidth === 0).map(i => i.getAttribute('src')));
    broken.forEach(s => issues.push('broken image: ' + s));
    const notReady = await page.evaluate(() => [...document.querySelectorAll('.ar3d')].filter(b => !b.classList.contains('is-ready')).map(b => b.id || b.dataset.src));
    notReady.forEach(s => issues.push('3D viewer not loaded: ' + s));
    const slug = (p.replace(/^\/|\/$/g, '').replace(/\//g, '_') || 'home');
    const file = path.join(out, `${prefix}${slug}-${name}.png`);
    await page.screenshot({ path: file, fullPage: true });
    console.log(`${file}${issues.length ? '' : '  ok'}`);
    issues.forEach(i => console.log('  ! ' + i));
    problems += issues.length;
    await ctx.close();
  }
}
await browser.close();
server.close();
process.exit(problems ? 2 : 0);
