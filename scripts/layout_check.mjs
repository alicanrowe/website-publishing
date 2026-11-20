#!/usr/bin/env node
// Clipping and alignment check across screen widths.
// Builds the site, opens each page at 390, 768, 1024, 1280, 1440, 1680 and 1920 wide (and 1440 at 2x),
// and flags:
//   CLIP   text, images, figures, tables or viewers that run past the left or right edge of the window,
//          or that are cut off by an ancestor with overflow hidden/clip
//   SCROLL the page scrolls sideways
//   ALIGN  items of one grid or flex row whose tops differ by more than 80 px and 20% of the row's height
//          (a 3D viewer sitting high while the drawings beside it start far down, as on the Moth stand)
//
//   node scripts/layout_check.mjs --site <repo> /moth /nine-lives
//   node scripts/layout_check.mjs --site <repo> --all          every page in the built site
// Exit code 1 when anything is flagged. Run it for every page you touch, before the PR.
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
const { chromium } = createRequire(import.meta.url)('playwright');

const a = process.argv.slice(2);
const opt = (k, d) => { const i = a.indexOf(k); if (i < 0) return d; const v = a[i + 1]; a.splice(i, 2); return v; };
const flag = k => { const i = a.indexOf(k); if (i < 0) return false; a.splice(i, 1); return true; };
const site = path.resolve(opt('--site', '.'));
const all = flag('--all');
const dist = path.join(os.tmpdir(), 'ar-site-dist');
const r = spawnSync('python3', [path.join(site, 'tools/build.py')], { env: { ...process.env, SITE_OUT: dist }, stdio: 'ignore' });
if (r.status !== 0) { console.error('build failed'); process.exit(1); }
const root = fs.existsSync(dist) ? dist : path.join(site, 'dist');
let pages = a;
if (all || !pages.length) {
  pages = [];
  const walk = d => { for (const f of fs.readdirSync(d)) { const p = path.join(d, f);
    if (fs.statSync(p).isDirectory()) walk(p); else if (f === 'index.html') pages.push('/' + path.relative(root, d).replace(/\\/g, '/')); } };
  walk(root);
}
const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json',
  '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.glb': 'model/gltf-binary', '.woff2': 'font/woff2', '.mp4': 'video/mp4' };
const server = http.createServer((req, res) => {
  let f = path.join(root, decodeURIComponent(req.url.split('?')[0]));
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, 'index.html');
  if (!fs.existsSync(f)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'content-type': types[path.extname(f).toLowerCase()] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
}).listen(0);
const base = `http://127.0.0.1:${server.address().port}`;
const sizes = [[390, 844, 1], [768, 1024, 1], [1024, 768, 1], [1280, 800, 1], [1440, 900, 1], [1440, 900, 2], [1680, 1050, 1], [1920, 1080, 1]];
const browser = await chromium.launch();
let n = 0;
for (const p of pages) {
  for (const [w, h, dpr] of sizes) {
    const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: dpr });
    await page.goto(base + p, { waitUntil: 'load', timeout: 60000 }).catch(() => {});
    await page.waitForTimeout(600);
    const found = await page.evaluate(() => {
      const out = [], W = document.documentElement.clientWidth;
      const name = e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (typeof e.className === 'string' && e.className ? '.' + e.className.trim().split(/\s+/).slice(0, 2).join('.') : '');
      const label = e => (name(e) + ' "' + (e.textContent || e.alt || '').trim().replace(/\s+/g, ' ').slice(0, 40) + '"');
      if (document.documentElement.scrollWidth > W + 1) out.push(`SCROLL page is ${document.documentElement.scrollWidth}px wide in a ${W}px window`);
      const sel = 'main p, main h1, main h2, main h3, main li, main dt, main dd, main td, main th, main figcaption, main img, main figure, main table, main .ar3d, main model-viewer, main video, .ds p, .ds h2, .ds h3, .ds dd, .ds dt, .ds figcaption, .ds img, .ds figure, .ds table, .ds .ar3d';
      const seen = new Set();
      for (const e of document.querySelectorAll(sel)) {
        if (seen.has(e)) continue; seen.add(e);
        const b = e.getBoundingClientRect();
        if (b.width < 2 || b.height < 2) continue;
        const cs = getComputedStyle(e); if (cs.visibility === 'hidden' || cs.position === 'fixed') continue;
        if (e.closest('[aria-hidden="true"]') || cs.pointerEvents === 'none') continue; // decorative backdrops may bleed on purpose
        // the nearest ancestor that crops sideways (overflow hidden/clip)
        let crop = null;
        for (let anc = e.parentElement; anc && anc !== document.body; anc = anc.parentElement) {
          const s = getComputedStyle(anc);
          if (/(hidden|clip|auto|scroll)/.test(s.overflowX)) { crop = anc; break; }  // sideways-scrolling rows (carousels) count as a frame
        }
        const cb = crop ? crop.getBoundingClientRect() : null;
        const visL = cb ? Math.max(b.left, cb.left) : b.left, visR = cb ? Math.min(b.right, cb.right) : b.right;
        if (visR > W + 1 || visL < -1) { out.push(`CLIP ${label(e)} spans ${Math.round(visL)}..${Math.round(visR)} in a ${W}px window`); continue; }
        // a photo cropped by its frame (cover, slow zoom) is fine; text cut by its box is not
        const isText = /^(P|H1|H2|H3|LI|DT|DD|TD|TH|FIGCAPTION|TABLE)$/.test(e.tagName);
        if (isText && cb && /(hidden|clip)/.test(getComputedStyle(crop).overflowX) && (b.right > cb.right + 2 || b.left < cb.left - 2)) out.push(`CLIP ${label(e)} is cut off by ${name(crop)}`);
      }
      for (const g of document.querySelectorAll('main *, .ds *')) {
        const d = getComputedStyle(g).display;
        if (!/grid|flex/.test(d)) continue;
        const kids = [...g.children].filter(k => { const b = k.getBoundingClientRect(); return b.width > 40 && b.height > 40; })
          .map(k => ({ k, b: k.getBoundingClientRect() }));
        for (let i = 0; i < kids.length; i++) for (let j = i + 1; j < kids.length; j++) {
          const A = kids[i].b, B = kids[j].b;
          const sameRow = A.top < B.bottom && B.top < A.bottom && (A.right <= B.left + 1 || B.right <= A.left + 1);
          if (!sameRow) continue;
          const rowH = Math.max(A.bottom, B.bottom) - Math.min(A.top, B.top);
          const dt = Math.abs(A.top - B.top);
          if (dt > 80 && dt > rowH * 0.2) out.push(`ALIGN ${name(kids[i].k)} and ${name(kids[j].k)} in ${name(g)} start ${Math.round(dt)}px apart`);
        }
      }
      return [...new Set(out)];
    });
    for (const f of found) { console.log(`${p} @${w}${dpr > 1 ? 'x' + dpr : ''}: ${f}`); n++; }
    await page.close();
  }
}
await browser.close(); server.close();
console.log(n ? `${n} layout problem(s)` : 'no clipping or misaligned rows');
process.exit(n ? 1 : 0);
