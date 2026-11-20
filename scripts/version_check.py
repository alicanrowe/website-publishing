#!/usr/bin/env python3
"""List pages that show an older version of a model or render than the site already holds.

Looks at every media path a page uses (src, data-src, data-model, poster, markdown images).
When a file name carries a version (v6s, v6w, r9, -v2, _1117b ...) and the same folder holds
a file with the same stem and a later version, the page is flagged. Run before every site PR
(the owner's rule: every page matches the latest version of its project).

  python3 scripts/version_check.py --site <repo>
Exit code 1 when something is behind.
"""
import argparse, os, re, sys

ap = argparse.ArgumentParser()
ap.add_argument('--site', required=True)
A = ap.parse_args()
CONTENT, STATIC = os.path.join(A.site, 'content'), os.path.join(A.site, 'static')
VER = re.compile(r'(?P<stem>[a-z].*?)(?P<sep>[-_]?)(?P<v>(?:v|r)\d+[a-z]?|\d{4}[a-z])(?P<rest>(?:[-_](?:lite|web|on|off|hero|tile|white|\d+))*)(?P<ext>\.[a-z0-9]+)$', re.I)

def key(v):
    m = re.match(r'([a-z]?)(\d+)([a-z]?)', v.lower())
    return (int(m.group(2)), m.group(3)) if m else (0, '')

def find(ref):
    r = ref.split('?')[0].split('#')[0].lstrip('/')
    for root in (CONTENT, STATIC):
        p = os.path.join(root, r)
        if os.path.exists(p): return p
    return None

behind = 0
for f in sorted(os.listdir(CONTENT)):
    if not f.endswith('.md'): continue
    body = open(os.path.join(CONTENT, f), encoding='utf-8').read()
    refs = set(re.findall(r'(?:src|data-src|data-model|poster)=["\']([^"\']+)', body))
    refs |= set(re.findall(r'!\[[^\]]*\]\(([^)\s]+)\)', body))
    for ref in sorted(refs):
        path = find(ref)
        if not path: continue
        d, name = os.path.split(path)
        m = VER.match(name)
        if not m: continue
        newer = []
        for other in os.listdir(d):
            o = VER.match(other)
            if o and o.group('stem') == m.group('stem') and o.group('ext') == m.group('ext') \
               and o.group('rest') == m.group('rest') and key(o.group('v')) > key(m.group('v')):
                newer.append(other)
        if newer:
            behind += 1
            print(f'BEHIND {f}: {ref} -> newer in the same folder: {", ".join(sorted(newer))}')

# Render freshness: a still on a page must not be older than the model the same page shows.
# The page's newest model version (from its .glb files, e.g. moth-case-v7c-lite.glb -> v7c) is compared
# with the version token in each image name in the same project folder (moth-v6pa-k01.jpg -> v6pa).
# Files that carry an older token on purpose. Add one only with the reason and who confirmed it.
ALLOW = [
    (r'/moth/w/ds-it-v\d-', 'Design iteration variants V1..V8 on the Moth page: option labels, not versions'),
    (r'files/moth/Moth_(full_size_[a-z0-9_]+|parts_full_size|joinery_and_assemblies)_v6s', 'case drawings still current for v7c (Moth build thread, 19 Nov 2026); replace when the stand drawings are redone'),
]
# Allow lists in the site's tools/sources.json (the build gate's exceptions) count here too, so an exception is written once.
try:
    import json as _json
    _src = _json.load(open(os.path.join(os.path.dirname(CONTENT.rstrip('/')), 'tools', 'sources.json')))
    for _pg in _src.get('pages', {}).values():
        ALLOW += [(a['pattern'], a.get('reason', '')) for a in _pg.get('allow', [])]
except (OSError, ValueError):
    pass
TOK = re.compile(r'(?<![a-z0-9])v(\d+)([a-z]*)', re.I)
def tok(name):
    m = TOK.search(name)
    return (int(m.group(1)), m.group(2).lower()) if m else None
for f in sorted(os.listdir(CONTENT)):
    if not f.endswith('.md'): continue
    body = open(os.path.join(CONTENT, f), encoding='utf-8').read()
    refs = set(re.findall(r'(?:src|data-src|data-model|poster|href)=["\']([^"\']+)', body))
    models = {}
    for ref in refs:
        if ref.split('?')[0].endswith('.glb'):
            t = tok(os.path.basename(ref))
            proj = ref.strip('/').split('/')[1] if ref.strip('/').count('/') >= 2 else ''
            if t and proj: models[proj] = max(models.get(proj, t), t)
    for ref in sorted(refs):
        r = ref.split('?')[0]
        if not re.search(r'\.(jpe?g|png|webp|avif|svg|pdf|mp4)$', r, re.I): continue
        parts = r.strip('/').split('/')
        proj = next((p for p in parts if p in models), None)
        t = tok(os.path.basename(r))
        if proj and t and t < models[proj] and not any(re.search(p, ref) for p, _ in ALLOW):
            behind += 1
            print(f'STALE {f}: {ref} is v{t[0]}{t[1]}, older than the v{models[proj][0]}{models[proj][1]} model on the same page')
print(f'{behind} reference(s) behind' if behind else 'all pages use the newest version the site holds')
sys.exit(1 if behind else 0)
