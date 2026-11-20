#!/usr/bin/env python3
"""Check the owner's site page notes before a PR.

    python3 scripts/lint_page.py --site /path/to/site-repo mouthpad moth
    python3 scripts/lint_page.py --site /path/to/site-repo --all

Flags (exit 1 if any ERROR):
  ERROR  front matter missing title or url, or url clashes with another page
  ERROR  image, video, GLB or file the page points to doesn't exist
  ERROR  <img> without alt
  ERROR  .ar3d viewer on a page that doesn't load /assets/viewer.js
  WARN   <img> without width and height (layout jumps while loading)
  WARN   image in content/img wider than 2000 px or over 1.5 MB (the build shrinks it,
         but the repo carries the full file; keep originals outside the repo)
  WARN   GLB over 3 MB, or without meshopt compression
  WARN   video over 15 MB
  WARN   the same CSS selector defined 3+ times in the page (patch the rule, don't stack overrides)
  WARN   style rules in the page that don't start with a page prefix (they can leak into other pages)
  ERROR  the same project shown twice on one page (two tiles, bands or heroes in different
         sections linking to the same page; anchors like /nine-rests#rest count as /nine-rests)
  WARN   brand slips: font-weight 400+ on Newsreader text, Jost, pure #000 body text, rounded corners, box shadows
  ERROR  (site-wide, every run) a home page section and its category page disagree: a piece on the
         category page (e.g. /sculpture) that the home page doesn't show anywhere (its section, the
         hero or a band), or pieces in the home section in a different order from the category page
  WARN   (site-wide) a piece in a home section that its category page doesn't list
"""
import argparse, os, re, sys, json, collections

ap = argparse.ArgumentParser()
ap.add_argument('--site', default='.')
ap.add_argument('--all', action='store_true')
ap.add_argument('pages', nargs='*')
A = ap.parse_args()
SITE = os.path.abspath(A.site)
CONTENT = os.path.join(SITE, 'content')
STATIC = os.path.join(SITE, 'static')

try:
    from PIL import Image
except ImportError:
    Image = None

def fm(text):
    meta = {}
    if text.startswith('---'):
        end = text.find('\n---', 3)
        for line in text[3:end].strip().splitlines():
            if ':' in line:
                k, v = line.split(':', 1); meta[k.strip()] = v.strip().strip('"\'')
        text = text[end + 4:]
    return meta, text

notes = sorted(f for f in os.listdir(CONTENT) if f.endswith('.md') and not f.startswith('_'))
urls = collections.Counter()
for f in notes:
    m, _ = fm(open(os.path.join(CONTENT, f), encoding='utf-8').read())
    urls[m.get('url') or '/' + f[:-3]] += 1

# site-wide: every nav item opens its own page; only the logo goes home
for n in json.load(open(os.path.join(SITE, 'site.json'))).get('nav', []):
    if n.get('url', '').rstrip('/') == '':
        print(f"ERROR site.json: nav item '{n.get('label')}' links to the home page; give it its own page")
        errors_site = True

# site-wide: each home page section lists the same pieces, in the same order, as its category page
# (the jewelry line was on /sculpture but missing from the home Sculpture row, 2026-11-20)
def proj(ref):
    ref = ref.split('?')[0].split('#')[0].rstrip('/')
    return ref if ref.startswith('/') and ref.count('/') == 1 and ref else None

home_note = next((f for f in notes if (fm(open(os.path.join(CONTENT, f), encoding='utf-8').read())[0].get('url') or '').rstrip('/') == ''), None)
by_url = {}
for f in notes:
    m, b = fm(open(os.path.join(CONTENT, f), encoding='utf-8').read())
    by_url[(m.get('url') or '/' + f[:-3]).rstrip('/')] = (f, b)
if home_note:
    home = by_url[''][1]
    home = re.sub(r'<nav\b.*?</nav>', '', home, flags=re.S)
    everywhere = {proj(r) for r in re.findall(r'(?:href|data-href)="([^"]+)"', home)} - {None}
    secs = list(re.finditer(r'<div class="sec"[^>]*>\s*<a[^>]*href="([^"]+)"', home))
    for i, sm in enumerate(secs):
        cat = proj(sm.group(1))
        if cat not in by_url: continue
        chunk = home[sm.end(): secs[i + 1].start() if i + 1 < len(secs) else len(home)]
        row = []
        for r in re.findall(r'(?:href|data-href)="([^"]+)"', chunk):
            p = proj(r)
            if p and p != cat and p not in row: row.append(p)
        cf, cb = by_url[cat]
        tab = []
        for r in re.findall(r'class="ar-(?:card|cap)" href="([^"]+)"', cb):
            p = proj(r)
            if p and p != cat and p not in tab: tab.append(p)
        if not tab: continue
        for p in tab:
            if p not in everywhere:
                print(f"ERROR home.md: {p} is on {cat} ({cf}) but not on the home page; add it to the {cat} section in the same place")
                errors_site = True
        for p in row:
            if p not in tab:
                print(f"WARN  home.md: {p} is in the home {cat} section but not on {cat} ({cf})")
        shared = [p for p in row if p in tab]
        want = [p for p in tab if p in shared]
        if shared != want:
            print(f"ERROR home.md: home {cat} section order {' , '.join(shared)} differs from {cf}: {' , '.join(want)}")
            errors_site = True

targets = notes if A.all else [p if p.endswith('.md') else p + '.md' for p in A.pages]
if not targets:
    ap.error('name pages (e.g. mouthpad) or pass --all')

errors = 0
if 'errors_site' in globals(): errors += 1
def say(level, page, msg):
    global errors
    if level == 'ERROR': errors += 1
    print(f'{level:5} {page}: {msg}')

def resolve(ref):
    ref = ref.split('?')[0].split('#')[0]
    if re.match(r'^(https?:|mailto:|data:|//)', ref) or not ref or ref.startswith('#'):
        return None
    r = ref.lstrip('/')
    for root in (CONTENT, STATIC):
        if os.path.exists(os.path.join(root, r)):
            return os.path.join(root, r)
    # build.py publishes big opaque PNGs as .jpg; either spelling is fine
    if r.endswith('.jpg') and os.path.exists(os.path.join(CONTENT, r[:-4] + '.png')):
        return os.path.join(CONTENT, r[:-4] + '.png')
    return False

seen_media = set()
for f in targets:
    path = os.path.join(CONTENT, f)
    if not os.path.exists(path):
        say('ERROR', f, 'no such note'); continue
    meta, body = fm(open(path, encoding='utf-8').read())
    for k in ('title', 'url'):
        if not meta.get(k): say('ERROR', f, f'front matter has no {k}')
    u = meta.get('url') or '/' + f[:-3]
    if urls[u] > 1: say('ERROR', f, f'url {u} is used by {urls[u]} pages')
    raw = meta.get('layout') == 'raw'

    refs = set(re.findall(r'(?:src|href|poster|data-src)=["\']([^"\']+)["\']', body))
    refs |= set(m for _, m in re.findall(r'!\[([^\]]*)\]\(([^)\s]+)\)', body))
    redirects = {a for a, _ in json.load(open(os.path.join(SITE, 'site.json'))).get('redirects', [])}
    for r in sorted(refs):
        clean = r.split('#')[0].split('?')[0]
        if not clean or ' ' in r or re.match(r'^(https?:|mailto:|tel:|data:|//)', r):
            continue
        if not re.search(r'\.[a-z0-9]{2,5}$', clean, re.I):
            # a link to another page: check it is a page (or a redirect)
            if clean.startswith('/') and clean.rstrip('/') not in {x.rstrip('/') for x in urls} | redirects and clean != '/':
                say('ERROR', f, f'link to a page that does not exist: {r}')
            continue
        hit = resolve(clean)
        if hit is False:
            say('ERROR', f, f'missing file: {r}')
        elif hit:
            seen_media.add(hit)

    for tag in re.findall(r'<img\b[^>]*>', body, re.I):
        src = re.search(r'src=["\']([^"\']+)', tag)
        s = src.group(1) if src else '?'
        if not re.search(r'\balt=', tag): say('ERROR', f, f'<img> without alt: {s}')
        if not (re.search(r'\bwidth=', tag) and re.search(r'\bheight=', tag)) and 'aria-hidden' not in tag:
            say('WARN', f, f'<img> without width/height: {s}')

    # never show the same project twice on one page: count, per linked page, the sections
    # (hero, band, grid group, %% block) that hold a tile linking to it
    main = re.sub(r'<header\b.*?</header>|<footer\b.*?</footer>|<nav\b.*?</nav>', '', body, flags=re.S)
    chunks = re.split(r'<section\b|<div class="sec\b|^%%[^\n]*%%\s*$', main, flags=re.M)
    where = collections.defaultdict(set)
    tile = re.compile(r'<(?:a|div)\b[^>]*class="[^"]*\b(?:cell|panel|tile|ar-cell|ar-tile|nr9-c|card|ar-cap)\b[^"]*"[^>]*>'
                      r'(?:\s*<div[^>]*data-href="([^"]+)")?', re.S)
    for i, ch in enumerate(chunks):
        for m in tile.finditer(ch):
            tag = m.group(0)
            h = re.search(r'\b(?:href|data-href)="(/[^"#?]*)', tag)
            h = h.group(1) if h else (m.group(1) or '').split('#')[0]
            if h and h not in ('/',) and h.rstrip('/') != u.rstrip('/'):
                where[h.rstrip('/')].add(i)
    for h, secs in sorted(where.items()):
        if len(secs) > 1:
            say('ERROR', f, f'{h} is shown in {len(secs)} places on this page (show each project once)')

    # project lists use the home page card everywhere: .ar-cards / .ar-card (or %% portfolio %%, which
    # builds them). The older tile styles (rb-grid, ar-cell, ar-tile, ar-portfolio) look different from home.
    if not raw:
        for old in ('rb-grid', 'ar-cell', 'ar-tile', 'ar-portfolio'):
            if re.search(r'class="[^"]*\b' + old + r'\b', body):
                say('ERROR', f, f'project tiles use the old "{old}" style; use the home page card (.ar-cards > .ar-card, see inline-layout.md)')

    # no outside artists or inspiration credits on public pages (the owner's rule)
    text = re.sub(r'<[^>]+>', ' ', re.sub(r'<(style|script)\b.*?</\1>|<!--.*?-->', ' ', body, flags=re.S))
    for m in re.finditer(r'\b(inspired by|inspirations?:|inspiration from|homage to|in the style of|influenced by|after the work of|a nod to|tribute to)\b', text, re.I):
        say('WARN', f, f'"{text[max(0, m.start() - 40):m.end() + 40].strip()}": no outside artists or inspiration credits on public pages')

    # a hand-built header (layout: raw) follows the same rule: words in a <nav> never link to "/"
    for nav in re.findall(r'<nav\b.*?</nav>', body, re.S):
        for a in re.finditer(r'<a\b[^>]*href="/"[^>]*>([^<]+)</a>', nav):
            say('ERROR', f, f'nav item "{a.group(1).strip()}" links to the home page; link its own page')

    if 'class="ar3d' in body and '/assets/viewer.js' not in body:
        say('ERROR', f, '3D viewer (.ar3d) but no <script src="/assets/viewer.js" defer>')

    css = '\n'.join(re.findall(r'<style[^>]*>(.*?)</style>', body, re.S))
    css_nomedia = re.sub(r'@media[^{]*\{', '', css)
    sel = collections.Counter()
    prefixes = collections.Counter()
    for block in re.findall(r'([^{}]+)\{[^{}]*\}', css_nomedia):
        for s in block.split(','):
            s = s.strip()
            if not s or s.startswith('@') or re.match(r'^(from|to|\d+%)$', s): continue
            sel[s] += 1
            m = re.match(r'^(?:html\s+body\s+)?\.([a-z0-9]+)-', s)
            prefixes[m.group(1) if m else s.split()[0]] += 1
    for s, n in sel.items():
        if n >= 3: say('WARN', f, f'selector defined {n} times: {s[:70]}')
    if not raw:
        shared = {k: v for k, v in prefixes.items() if not re.match(r'^[a-z0-9]+$', k) and not k.startswith(('.ar-', '.ar3d'))}
        loose = [k for k in shared if re.match(r'^(html|body|a|p|h\d|img|figure|table|td|th|main|header|footer|\*)\b', k)]
        for k in loose[:6]:
            say('WARN', f, f'unprefixed rule "{k}" can restyle the whole page; scope it under the page wrapper')

    if re.search(r"font-family:\s*['\"]?Jost", css): say('WARN', f, 'Jost is not a site font')
    if re.search(r'border-radius:\s*[1-9]', css) and 'ar3dspin' not in css: say('WARN', f, 'rounded corners (brand: none)')
    if re.search(r'box-shadow:\s*(?!none)', css): say('WARN', f, 'box shadow (brand: none)')
    for m in re.finditer(r'font:\s*(\d{3})\s[^;]*var\(--(?:ar-)?serif\)', css):
        if int(m.group(1)) >= 400: say('WARN', f, f'Newsreader at weight {m.group(1)} (site loads 200/300 only)')

for p in sorted(seen_media):
    ext = p.lower().rsplit('.', 1)[-1]
    size = os.path.getsize(p)
    rel = os.path.relpath(p, SITE)
    if ext in ('jpg', 'jpeg', 'png', 'webp') and Image:
        try:
            w = Image.open(p).width
            if w > 2000 or size > 1_500_000:
                say('WARN', rel, f'{w}px wide, {size/1e6:.1f} MB: resize to 2000 px max before committing')
        except Exception:
            pass
    elif ext == 'glb':
        head = open(p, 'rb').read(200_000)
        if size > 3_000_000: say('WARN', rel, f'GLB is {size/1e6:.1f} MB (aim under 3 MB)')
        if b'EXT_meshopt_compression' not in head and b'KHR_draco' not in head:
            say('WARN', rel, 'GLB not compressed (gltfpack -cc)')
    elif ext in ('mp4', 'webm', 'mov') and size > 15_000_000:
        say('WARN', rel, f'video is {size/1e6:.0f} MB (aim under 15 MB)')

print(f'{len(targets)} page(s) checked, {errors} error(s)')
sys.exit(1 if errors else 0)
