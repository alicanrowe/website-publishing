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
print(f'{behind} reference(s) behind' if behind else 'all pages use the newest version the site holds')
sys.exit(1 if behind else 0)
