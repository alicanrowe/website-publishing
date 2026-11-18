#!/usr/bin/env node
// Site-wide brand theme audit for alicanrowe.com.
// Builds the site, opens EVERY page at desktop (1440) and phone (390), reads the computed style of
// everything on screen and lists what doesn't match the brand theme (references/brand-on-the-web.md).
// lint_page.py reads the page source; this reads what the browser actually draws, so it also catches
// browser defaults (bold <strong>), shared-header drift and styles that come from site.css.
//
//   node scripts/theme_audit.mjs --site /path/to/alicanrowe-site            # every page
//   node scripts/theme_audit.mjs --site ... --json audit.json /dancers /moth # some pages, save raw data
//   options: --no-build
//
// Exit 1 if any page has a FAIL. Allowed exceptions live in ALLOW below, each with the reason.
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
const jsonOut = opt('--json', '');
const noBuild = flag('--no-build');

// Known, approved exceptions: page url prefix -> what is allowed there and why.
const ALLOW = {
  '/moth': { fonts: ['Monsieur La Doulaise', 'Pinyon Script'], darkHeader: true, exempt: '.ds-dot,.ds-dot *', why: 'moth custom theme (night band, script title), approved for its own page; red numbered dots are drawing callouts' },
  '/fairy-ring': { exempt: '.lc-board,.lc-board *', why: 'drawn Quest app screens (dark boards, coloured buttons) are illustrations, not page chrome' },
};

const dist = path.join(os.tmpdir(), 'ar-site-audit');
if (!noBuild) {
  const r = spawnSync('python3', [path.join(site, 'tools/build.py')], { env: { ...process.env, SITE_OUT: dist }, stdio: 'ignore' });
  if (r.status !== 0) { console.error('build failed'); process.exit(1); }
}
const root = noBuild && fs.existsSync(path.join(site, 'dist')) ? path.join(site, 'dist') : (fs.existsSync(dist) ? dist : path.join(site, 'dist'));
let pages = a.length ? a : [];
if (!pages.length) (function walk(d) {
  for (const f of fs.readdirSync(d)) { const p = path.join(d, f);
    if (fs.statSync(p).isDirectory()) walk(p);
    else if (f === 'index.html') pages.push('/' + path.relative(root, d).split(path.sep).join('/')); }
})(root);
pages = pages.map(p => p === '/' || p === '/.' ? '/' : p.replace(/\/$/, '')).sort();

const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json',
  '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.gif': 'image/gif',
  '.mp4': 'video/mp4', '.webm': 'video/webm', '.glb': 'model/gltf-binary', '.ttf': 'font/ttf', '.woff2': 'font/woff2' };
const server = http.createServer((req, res) => {
  let f = path.join(root, decodeURIComponent(req.url.split('?')[0]));
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, 'index.html');
  if (!fs.existsSync(f)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'content-type': types[path.extname(f).toLowerCase()] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
}).listen(0);
const base = `http://127.0.0.1:${server.address().port}`;

const browser = await chromium.launch();
const raw = {};
for (const [name, w] of [['desktop', 1440], ['phone', 390]]) for (const pg of pages) {
  const ctx = await browser.newContext({ viewport: { width: w, height: 900 } });
  const page = await ctx.newPage();
  await page.goto(base + (pg === '/' ? '/' : pg + '/'), { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {});
  await page.waitForTimeout(1200);
  const ex = Object.entries(ALLOW).find(([p]) => pg.startsWith(p))?.[1].exempt || '';
  raw[`${pg} ${name}`] = await page.evaluate((ex) => {
    const o = { text: [], boxes: [], page: getComputedStyle(document.body).backgroundColor, header: null, nav: [] };
    const d = e => { let s = e.tagName.toLowerCase(); if (e.classList.length) s += '.' + [...e.classList].slice(0, 2).join('.');
      const t = (e.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 28); return s + (t ? ` "${t}"` : ''); };
    const hdr = document.querySelector('header'); if (hdr) {
      const cs = getComputedStyle(hdr); const logo = hdr.querySelector('.ar-logo,.mark');
      o.header = { bg: cs.backgroundColor, logoX: logo ? Math.round(logo.getBoundingClientRect().left / innerWidth * 100) : null };
      o.nav = [...hdr.querySelectorAll('nav a')].map(a => a.textContent.trim().toLowerCase());
      const a0 = hdr.querySelector('nav a'); if (a0) { const c = getComputedStyle(a0); o.header.nav = `${c.fontSize} ${c.color}`; }
    }
    for (const e of document.querySelectorAll('body *')) {
      const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden') continue;
      const r = e.getBoundingClientRect(); if (!r.width && !r.height) continue;
      if (e.closest('iframe,[data-theme-exempt]') || (ex && e.matches(ex))) continue;
      if ([...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()))
        o.text.push({ el: d(e), fam: cs.fontFamily.split(',')[0].replace(/["']/g, '').trim(), w: cs.fontWeight,
          col: e instanceof SVGElement ? cs.fill : cs.color, bg: (() => { let x = e; while (x && x !== document.body) { const b = getComputedStyle(x).backgroundColor; if (b !== 'rgba(0, 0, 0, 0)') return b; x = x.parentElement; } return null; })() });
      const border = ['Top', 'Right', 'Bottom', 'Left'].filter(s => parseFloat(cs['border' + s + 'Width']) > 0 && cs['border' + s + 'Style'] !== 'none');
      o.boxes.push(...[
        parseFloat(cs.borderTopLeftRadius) > 0 && e.tagName !== 'IMG' ? `radius ${cs.borderRadius}: ${d(e)}` : null,
        cs.boxShadow !== 'none' ? `shadow: ${d(e)}` : null,
        /gradient/.test(cs.backgroundImage) ? `gradient: ${d(e)}` : null,
        border.length === 4 ? `boxed (border all round): ${d(e)}` : null,
      ].filter(Boolean));
    }
    return o;
  }, ex);
  await ctx.close();
}
await browser.close(); server.close();
if (jsonOut) fs.writeFileSync(jsonOut, JSON.stringify(raw, null, 1));

// ---- rules (from brand/THEME.md and references/brand-on-the-web.md) ----
const rgb = c => { const m = /rgba?\(([\d.]+), ([\d.]+), ([\d.]+)(?:, ([\d.]+))?\)/.exec(c || ''); return m ? m.slice(1).map(Number) : null; };
const okInk = c => { const v = rgb(c); if (!v) return /^url/.test(c); const [r, g, b] = v;
  return (r === g && g === b && (r < 30 || r === 255)) || (r === 71 && g === 37 && b === 37) || (r === 20 && g === 18 && b === 16); };
const okBg = c => { const v = rgb(c); if (!v) return true; const [r, g, b, al = 1] = v;
  return al < 0.06 || Math.min(r, g, b) >= 228; };  // white, #F3F3F3 image fill, the home page's pale cyc
const rows = {}; let fails = 0;
// group repeats by rule + element tag/class, keep the first text as the example
const add = (pg, lvl, msg) => { const k = `${lvl} ${msg.replace(/ "[^"]*"$/, '')}`; (rows[pg] ||= new Map()); if (lvl === 'FAIL' && !rows[pg].has(k)) fails++; rows[pg].set(k, (rows[pg].get(k) || 0) + 1); };
const headers = {};
for (const [key, o] of Object.entries(raw)) {
  const [pg, view] = key.split(' ');
  const allow = Object.entries(ALLOW).find(([p]) => pg.startsWith(p))?.[1] || {};
  if (!okBg(o.page)) add(pg, 'FAIL', `page background ${o.page} (brand: white)`);
  if (o.header) (headers[view] ||= {})[pg] = `${o.nav.join(' | ')} :: logo at ${o.header.logoX}% :: nav ${o.header.nav} :: bg ${o.header.bg}`;
  for (const t of o.text) {
    if (!['Newsreader', 'IBM Plex Mono'].includes(t.fam) && !(allow.fonts || []).includes(t.fam)) add(pg, 'FAIL', `font ${t.fam}: ${t.el}`);
    if (t.fam === 'Newsreader' && !['200', '300'].includes(t.w)) add(pg, 'WARN', `Newsreader ${t.w} asked for (renders the 300 cut, but set 200/300): ${t.el}`);
    const drawingRed = t.col === 'rgb(150, 40, 28)' && /^(text|tspan)/.test(t.el);  // dimension red on SVG drawings
    if (!okInk(t.col) && !drawingRed && !(allow.darkHeader && /^a\b/.test(t.el) && /^rgba?\(255, 2[45]\d/.test(t.col))) add(pg, 'FAIL', `text colour ${t.col} (brand: grey ink, nav mauve): ${t.el}`);
    if (t.bg && !okBg(t.bg) && !(allow.darkHeader && /^(a|header)/.test(t.el))) add(pg, 'FAIL', `text on a coloured plate ${t.bg}: ${t.el}`);
  }
  for (const b of o.boxes) add(pg, 'WARN', b);
}
// shared header: every page should carry the same nav labels, order, size and colour
for (const [view, hs] of Object.entries(headers)) {
  const count = {}; for (const h of Object.values(hs)) count[h] = (count[h] || 0) + 1;
  const common = Object.entries(count).sort((x, y) => y[1] - x[1])[0]?.[0];
  for (const [pg, h] of Object.entries(hs)) if (h !== common && !(Object.entries(ALLOW).find(([p]) => pg.startsWith(p))?.[1].darkHeader))
    add(pg, 'FAIL', `${view} header differs from the other pages: ${h}  (most pages: ${common})`);
}
for (const pg of pages) {
  const m = rows[pg]; if (!m) { console.log(`ok    ${pg}`); continue; }
  console.log(`\n${pg}`);
  for (const [k, n] of [...m].sort()) console.log(`  ${k}${n > 1 ? `  (x${n})` : ''}`.slice(0, 260));
}
console.log(`\n${pages.length} page(s) audited, ${fails} distinct fail(s)`);
process.exit(fails ? 1 : 0);
