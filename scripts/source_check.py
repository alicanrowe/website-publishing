#!/usr/bin/env python3
"""List pages that are older than the project files they are built from.

version_check.py only compares files inside the site repo, so a page can pass it while the
project's own outputs (new renders, a re-audited buy list, a rewritten build guide) have moved
on. This script reads tools/sources.json in the site repo, which maps each page to the source
files it is built from, and flags every source changed after the page's last commit.

  python3 scripts/source_check.py --site <repo> --projects <project files root>
Exit code 1 when a page is behind its sources.

tools/sources.json:
  {"pages": {"dancers": {"sources": ["shop-bots/*/site/*.jpg", "shop-bots/*/build_guide.md", ...],
                         "ignore": ["shop-bots/_old/*"]}}}
Globs are relative to --projects. Add a page's entry when you first build it from project files.
"""
import argparse, glob, json, os, subprocess, sys, time

ap = argparse.ArgumentParser()
ap.add_argument('--site', required=True)
ap.add_argument('--projects', required=True)
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
print(f'{behind} page(s) behind their sources' if behind else 'every mapped page is newer than its sources')
sys.exit(1 if behind else 0)
