#!/usr/bin/env node
// Site-wide brand theme audit for the owner's site.
// Builds the site, opens EVERY page at desktop (1440) and phone (390), reads the computed style of
// everything on screen and lists what doesn't match the brand theme (references/brand-on-the-web.md).
// lint_page.py reads the page source; this reads what the browser actually draws, so it also catches
// browser defaults (bold <strong>), shared-header drift and styles that come from site.css.
//
//   node scripts/theme_audit.mjs --site /path/to/site-repo            # every page
//   node scripts/theme_audit.mjs --site ... --json audit.json /dancers /moth # some pages, save raw data
//   node scripts/theme_audit.mjs --site ... --live https://alicanrowe.com   # the published pages, cache-busted (hard refresh); run after every deploy
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
const live = opt('--live', '');  // e.g. https://alicanrowe.com : audit the published site, cache-busted like a hard refresh

// Known, approved exceptions: page url prefix -> what is allowed there and why.
const ALLOW = {
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
const base = live ? live.replace(/\/$/, '') : `http://127.0.0.1:${server.address().port}`;
const bust = live ? `?nocache=${Date.now()}` : '';

const browser = await chromium.launch();
const raw = {};
for (const [name, w] of [['desktop', 1440], ['phone', 390]]) for (const pg of pages) {
  const ctx = await browser.newContext({ viewport: { width: w, height: 900 }, extraHTTPHeaders: live ? { 'Cache-Control': 'no-cache', Pragma: 'no-cache' } : {} });
  const page = await ctx.newPage();
  await page.goto(base + (pg === '/' ? '/' : pg + '/') + bust, { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {});
  await page.waitForTimeout(1200);
  const ex = Object.entries(ALLOW).find(([p]) => pg.startsWith(p))?.[1].exempt || '';
  raw[`${pg} ${name}`] = await page.evaluate((ex) => {
    const o = { text: [], boxes: [], page: getComputedStyle(document.body).backgroundColor, header: null, nav: [] };
    const d = e => { let s = e.tagName.toLowerCase(); if (e.classList.length) s += '.' + [...e.classList].slice(0, 2).join('.');
      const t = (e.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 28); return s + (t ? ` "${t}"` : ''); };
    const hdr = document.querySelector('header'); if (hdr) {
      const cs = getComputedStyle(hdr); const logo = hdr.querySelector('.ar-logo,.mark');
      o.header = { bg: cs.backgroundColor, logoX: logo ? Math.round(logo.getBoundingClientRect().left / innerWidth * 100) : null };
      // only the links you can see, each with where it sits (% of the width), so a nav that moves sides shows up
      const vis = [...hdr.querySelectorAll('nav a')].filter(a => { const r = a.getBoundingClientRect(), c = getComputedStyle(a);
        return r.width > 0 && c.visibility !== 'hidden' && +getComputedStyle(a.closest('nav')).opacity !== 0; });
      o.nav = vis.map(a => `${a.textContent.trim().toLowerCase()}@${Math.round(a.getBoundingClientRect().left / innerWidth * 100)}`);
      const a0 = vis[0] || hdr.querySelector('nav a'); if (a0) { const c = getComputedStyle(a0); o.header.nav = `${c.fontSize} ${c.color}`; }
    }
    for (const e of document.querySelectorAll('body *')) {
      const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden') continue;
      const r = e.getBoundingClientRect(); if (!r.width && !r.height) continue;
      if (e.closest('iframe,[data-theme-exempt]') || (ex && e.matches(ex))) continue;
      if ([...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()))
        o.text.push({ el: d(e), fam: cs.fontFamily.split(',')[0].replace(/["']/g, '').trim(), w: cs.fontWeight, fs: parseFloat(cs.fontSize),
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
const headers = {}, hstyle = {};
for (const [key, o] of Object.entries(raw)) {
  const [pg, view] = key.split(' ');
  const allow = Object.entries(ALLOW).find(([p]) => pg.startsWith(p))?.[1] || {};
  if (!okBg(o.page)) add(pg, 'FAIL', `page background ${o.page} (brand: white)`);
  if (o.header) {
    (headers[view] ||= {})[pg] = `${o.nav.join(' | ')} :: logo at ${o.header.logoX}%`;
    (hstyle[view] ||= {})[pg] = `nav ${o.header.nav}`;
  }
  for (const t of o.text) {
    if (!['Newsreader', 'IBM Plex Mono'].includes(t.fam) && !(allow.fonts || []).includes(t.fam)) add(pg, 'FAIL', `font ${t.fam}: ${t.el}`);
    if (t.fam === 'Newsreader' && !['200', '300'].includes(t.w)) add(pg, 'WARN', `Newsreader ${t.w} asked for (only the 200/300 cuts load, so it draws 300; set 200/300): ${t.el}`);
    // SVG text sizes are in drawing units, so SVG labels are skipped
    if (t.fam === 'IBM Plex Mono' && t.fs > 12.5 && !/^(text|tspan)/.test(t.el)) add(pg, 'FAIL', `Plex Mono at ${t.fs}px (brand: mono only for small credits, numbers and dimensions; body text is Newsreader): ${t.el}`);
    const drawingRed = t.col === 'rgb(150, 40, 28)' && /^(text|tspan)/.test(t.el);  // dimension red on SVG drawings
    if (!okInk(t.col) && !drawingRed && !(allow.darkHeader && /^a\b/.test(t.el) && /^rgba?\(255, 2[45]\d/.test(t.col))) add(pg, 'FAIL', `text colour ${t.col} (brand: grey ink, nav mauve): ${t.el}`);
    if (t.bg && !okBg(t.bg) && !(allow.darkHeader && /^(a|header)/.test(t.el))) add(pg, 'FAIL', `text on a coloured plate ${t.bg}: ${t.el}`);
  }
  for (const b of o.boxes) add(pg, 'WARN', b);
}
// shared header: every page puts the same nav words in the same places as the home page (the owner's rule:
// buttons never jump sides between pages), with the same type. Positions are compared to "/" when it was audited.
for (const [view, hs] of Object.entries(headers)) {
  const count = {}; for (const h of Object.values(hs)) count[h] = (count[h] || 0) + 1;
  const std = hs['/'] || Object.entries(count).sort((x, y) => y[1] - x[1])[0]?.[0];
  const near = (h) => { const [n1, l1] = h.split(' :: '), [n2, l2] = std.split(' :: ');
    const A = n1.split(' | ').filter(Boolean), B = n2.split(' | ').filter(Boolean); if (A.length !== B.length || l1 !== l2) return false;
    return A.every((x, i) => { const [w1, p1] = x.split('@'), [w2, p2] = B[i].split('@'); return w1 === w2 && Math.abs(p1 - p2) <= 1; }); };
  for (const [pg, h] of Object.entries(hs)) if (!near(h))
    add(pg, 'FAIL', `${view} nav not in the home page's places: ${h}  (home: ${std})`);
}
for (const [view, hs] of Object.entries(hstyle)) {
  const count = {}; for (const h of Object.values(hs)) count[h] = (count[h] || 0) + 1;
  const common = Object.entries(count).sort((x, y) => y[1] - x[1])[0]?.[0];
  for (const [pg, h] of Object.entries(hs)) if (h !== common && !(Object.entries(ALLOW).find(([p]) => pg.startsWith(p))?.[1].darkHeader))
    add(pg, 'FAIL', `${view} nav type differs from the other pages: ${h}  (most pages: ${common})`);
}
for (const pg of pages) {
  const m = rows[pg]; if (!m) { console.log(`ok    ${pg}`); continue; }
  console.log(`\n${pg}`);
  for (const [k, n] of [...m].sort()) console.log(`  ${k}${n > 1 ? `  (x${n})` : ''}`.slice(0, 260));
}
console.log(`\n${pages.length} page(s) audited, ${fails} distinct fail(s)`);
process.exit(fails ? 1 : 0);
