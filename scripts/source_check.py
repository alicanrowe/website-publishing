#!/usr/bin/env python3
"""List pages that are older than the project files they are built from.

version_check.py only compares files inside the site repo, so a page can pass it while the
project's own outputs (new renders, a re-audited buy list, a rewritten build guide) have moved
on. This script reads tools/sources.json in the site repo, which maps each page to the source
files it is built from, and flags every source changed after the page's last commit.

  python3 scripts/source_check.py --site <repo> --projects <project files root>
Exit code 1 when a page is behind its sources.

tools/sources.json:
  {"pages": {"hive": {"sources": ["shop-bots/*/site/*.jpg", "shop-bots/*/build_guide.md", ...],
                         "ignore": ["shop-bots/_old/*"]}}}
Globs are relative to --projects. Add a page's entry when you first build it from project files.

Version lines (the newest model in the project files decides what "current" means):
  {"pages": {"moth": {"versions": [
      {"line": "case",  "model": "moth-v6/glb/moth_v*.glb",        "match": "(?i)moth-case|/moth/w/|Moth_"},
      {"line": "tools", "model": "moth-v6/glb/tools_v*_parts.glb", "match": "(?i)moth-tools"}],
    "allow": [{"pattern": "ds-it-v\\d", "reason": "design-iteration labels, not versions"}]}}}
For each line the script takes the newest version token (v7e > v7d > v7 > v6s) among the files the
model glob finds, then FAILs every media file on the page (GLB, image, PDF, video) whose name matches
the line and carries an older token. A new version dropped into the project files (moth_v7f.glb) makes
the page fail with no config change. A model glob that finds nothing also FAILs: the path moved or the
files were deleted, and "nothing to compare" must never read as a pass.
--write-lock saves the newest versions to tools/versions.lock.json in the site repo; the site's build
reads it and refuses to build a page that links an older file, so a stale page can't deploy even from a
machine without the project files.
It also runs name_check.py (a page's "record": current names, retired names, old URLs) and saves the names
in the lock, so the build refuses retired names too.
"""
import argparse, glob, json, os, subprocess, sys, time

ap = argparse.ArgumentParser()
ap.add_argument('--site', required=True)
ap.add_argument('--projects', required=True)
ap.add_argument('--write-lock', action='store_true', help='save the newest versions to tools/versions.lock.json')
ap.add_argument('--slack', type=int, default=120, help='seconds of grace after the commit')
A = ap.parse_args()
cfg_path = os.path.join(A.site, 'tools', 'sources.json')
if not os.path.exists(cfg_path):
    print('no tools/sources.json: add one so pages can be checked against their sources'); sys.exit(1)
cfg = json.load(open(cfg_path))
behind = 0
for page, spec in cfg.get('pages', {}).items():
    note = os.path.join('content', page + '.md')
    out = subprocess.run(['git', '-C', A.site, 'log', '-1', '--format=%ct', '--', note], capture_output=True, text=True).stdout.strip()
    if not out:
        print(f'SKIP {page}: {note} not committed'); continue
    t = int(out)
    ign = set()
    for g in spec.get('ignore', []): ign |= set(glob.glob(os.path.join(A.projects, g)))
    newer = []
    for g in spec.get('sources', []):
        for f in glob.glob(os.path.join(A.projects, g)):
            if f in ign or not os.path.isfile(f): continue
            m = os.path.getmtime(f)
            if m > t + A.slack: newer.append((m, os.path.relpath(f, A.projects)))
    if newer:
        behind += 1
        newer.sort(reverse=True)
        print(f'BEHIND {page} (last commit {time.strftime("%Y-%m-%d %H:%M", time.gmtime(t))} UTC): {len(newer)} newer source file(s)')
        for m, f in newer[:15]: print(f'   {time.strftime("%m-%d %H:%M", time.gmtime(m))}  {f}')
        if len(newer) > 15: print(f'   ... and {len(newer) - 15} more')

import re
TOK = re.compile(r'(?<![a-z0-9])v(\d+)([a-z]*)(?![a-z])', re.I)
def tok(name):
    m = TOK.search(name)
    return (int(m.group(1)), m.group(2).lower()) if m else None
def vs(t): return f'v{t[0]}{t[1]}'
REF = re.compile(r'(?:src|data-src|data-model|poster|href)=["\']([^"\']+\.(?:glb|gltf|jpe?g|png|webp|avif|svg|pdf|mp4|webm|mov)(?:[?#][^"\']*)?)["\']', re.I)
lock, stale = {}, 0
for page, spec in cfg.get('pages', {}).items():
    lines = spec.get('versions', [])
    if not lines: continue
    note = os.path.join(A.site, 'content', page + '.md')
    body = open(note, encoding='utf-8').read() if os.path.exists(note) else ''
    refs = sorted(set(r.split('?')[0].split('#')[0] for r in REF.findall(body)))
    allow = spec.get('allow', [])
    lock[page] = {'lines': [], 'allow': [a['pattern'] for a in allow]}
    for ln in lines:
        found = [f for f in glob.glob(os.path.join(A.projects, ln['model'])) if tok(os.path.basename(f))]
        if not found:
            stale += 1; print(f'NOMODEL {page}/{ln["line"]}: {ln["model"]} finds no versioned file in the project files'); continue
        newest = max(tok(os.path.basename(f)) for f in found)
        src = max(found, key=lambda f: tok(os.path.basename(f)))
        lock[page]['lines'].append({'line': ln['line'], 'match': ln['match'], 'newest': vs(newest), 'from': os.path.relpath(src, A.projects)})
        for r in refs:
            if not re.search(ln['match'], r): continue
            t = tok(os.path.basename(r))
            if t is None or t >= newest: continue
            why = next((a['reason'] for a in allow if re.search(a['pattern'], r)), None)
            if why: print(f'   allowed {r} ({vs(t)}): {why}'); continue
            stale += 1
            print(f'STALE {page}/{ln["line"]}: {r} is {vs(t)}, the project files are at {vs(newest)} ({os.path.relpath(src, A.projects)})')
# names: a renamed project or piece must be renamed everywhere (name_check.py, the page's "record")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import name_check
nfails, nwarns, nlock = name_check.run(A.site, A.projects, cfg)
for w in nwarns: print(w)
for f in nfails: print(f)
for page, names in nlock.items():
    lock.setdefault(page, {'lines': [], 'allow': []})['names'] = names
if A.write_lock and lock:
    json.dump(lock, open(os.path.join(A.site, 'tools', 'versions.lock.json'), 'w'), indent=1)
    print('wrote tools/versions.lock.json')
print(f'{behind} page(s) behind their sources' if behind else 'every mapped page is newer than its sources')
print(f'{stale} file(s) older than the newest model version' if stale else 'every versioned file matches the newest model version')
print(f'{len(nfails)} name problem(s)' if nfails else 'every recorded page, card and link uses the current names')
sys.exit(1 if (behind or stale or nfails) else 0)
