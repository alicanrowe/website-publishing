#!/usr/bin/env python3
"""Fail pages, cards and links whose names don't match the project's latest record.

version_check and source_check compare files. A rename (the jewelry line -> Imago, "Ring A" -> "Hairstreak ring")
changes no file the site links, so both pass while the page keeps the old name. This check reads the
project's record, a small JSON file in the project files that the thread making the change keeps current,
and holds the whole site to it.

  python3 scripts/name_check.py --site <repo> --projects <project files root>
Exit code 1 on any FAIL. source_check.py runs it too, and its --write-lock saves the names into
tools/versions.lock.json, which the site's build reads to refuse retired names and old URLs.

tools/sources.json, per page:  "imago": {"record": "jewelry/imago/RECORD.json", "sources": [...], ...}
The record:
  {"name": "Imago", "url": "/imago",
   "renamed": [{"from": "the jewelry line", "url": "/the jewelry line", "date": "2026-11-25"}],
   "pieces": [{"name": "Swallowtail cuff", "was": ["Cuff", "Moth cuff"]}, ...],
   "allow": ["formerly the jewelry line"]}          # optional: text where an old name is meant to stay
Checks:
  URL       the note's url is the record's url
  NAME      the page's visible text (title, h1, copy, alt text) carries the current name
  PIECE     every current piece name is on the page
  RETIRED   an old collection name anywhere on the site (any case), or an old piece name on the page
            (as written, after the current names are taken out, so "Swallowtail cuff" doesn't trip "Cuff")
  OLDURL    a link to an old URL anywhere (href, data-href); the redirect is for visitors, not our links
  CARD      a card linking to the page that doesn't show the current name
  REDIRECT  site.json lacks old url -> new url
A page in sources.json with no record gets a WARN: add one when the project is next touched.
"""
import argparse, glob, json, os, re, sys

TAGS = re.compile(r'<[^>]+>')
ATTR = re.compile(r'\b(?:alt|aria-label|title|data-name|data-alt|data-fact)=["\']([^"\']*)["\']', re.I)
DROP = re.compile(r'<(style|script)\b.*?</\1>', re.I | re.S)
FM = re.compile(r'^---\n(.*?)\n---\n', re.S)


def visible(md):
    """Front matter title/description, the text between tags, and the attributes people read."""
    fm = FM.match(md)
    head = ''
    if fm:
        head = ' '.join(l.split(':', 1)[1] for l in fm.group(1).splitlines() if l.split(':', 1)[0].strip() in ('title', 'description'))
        md = md[fm.end():]
    md = DROP.sub(' ', md)
    return ' '.join([head] + ATTR.findall(md) + [TAGS.sub(' ', md)])


def url_of(md, page):
    fm = FM.match(md)
    if fm:
        for l in fm.group(1).splitlines():
            if l.startswith('url:'):
                return l.split(':', 1)[1].strip().strip('"\'')
    return '/' + page


def has(text, word, case=False):
    return re.search(r'(?<![\w-])' + re.escape(word) + r'(?![\w-])', text, 0 if case else re.I) is not None


def run(site, projects, cfg):
    fails, warns, lock = [], [], {}
    notes = {os.path.basename(f)[:-3]: open(f, encoding='utf-8').read()
             for f in glob.glob(os.path.join(site, 'content', '*.md')) if not os.path.basename(f).startswith('_')}
    sitecfg = json.load(open(os.path.join(site, 'site.json')))
    redirects = {a: b for a, b in sitecfg.get('redirects', [])}
    for page, spec in cfg.get('pages', {}).items():
        if 'record' not in spec:
            warns.append(f'WARN {page}: no "record" in tools/sources.json, so a rename of this project would not be caught')
            continue
        rp = os.path.join(projects, spec['record'])
        if not os.path.exists(rp):
            fails.append(f'NORECORD {page}: {spec["record"]} is missing from the project files'); continue
        rec = json.load(open(rp))
        name, url = rec['name'], rec['url']
        allow = rec.get('allow', [])
        old = [r['from'] for r in rec.get('renamed', []) if r.get('from') and r['from'].lower() != name.lower()]
        old_urls = [r['url'] for r in rec.get('renamed', []) if r.get('url') and r['url'] != url]
        pieces = [p['name'] for p in rec.get('pieces', [])]
        was = [w for p in rec.get('pieces', []) for w in p.get('was', [])]
        lock[page] = {'name': name, 'url': url, 'retired': old, 'old_urls': old_urls, 'allow': allow}
        md = notes.get(page)
        if md is None:
            fails.append(f'NOPAGE {page}: content/{page}.md not found (rename the note with the project)'); continue
        if url_of(md, page) != url:
            fails.append(f'URL {page}: the note serves {url_of(md, page)}, the record says {url}')
        txt = visible(md)
        for a in allow: txt = txt.replace(a, ' ')
        if not has(txt, name):
            fails.append(f'NAME {page}: "{name}" is not on the page')
        for p in pieces:
            if not has(txt, p):
                fails.append(f'PIECE {page}: piece "{p}" is not on the page')
        bare = txt
        for p in sorted(pieces + [name], key=len, reverse=True):
            bare = re.sub(re.escape(p), ' ', bare, flags=re.I)
        for w in was:
            if has(bare, w, case=True):
                fails.append(f'RETIRED {page}: old piece name "{w}" is still on the page')
        for ou in old_urls:
            if redirects.get(ou) != url:
                fails.append(f'REDIRECT {page}: site.json needs ["{ou}", "{url}"]')
        if redirects.get(url):
            fails.append(f'REDIRECT {page}: site.json still sends {url} to {redirects[url]}')
        # the whole site: old names, old links, and cards that point here
        for other, body in notes.items():
            vt = visible(body)
            for a in allow: vt = vt.replace(a, ' ')
            for o in old:
                if has(vt, o):
                    fails.append(f'RETIRED {other}: old name "{o}" (now "{name}") is on the page')
            for ou in old_urls:
                if re.search(r'(?:href|data-href)=["\']' + re.escape(ou) + r'(?:[#?"\'])', body):
                    fails.append(f'OLDURL {other}: links to {ou}; link to {url}')
            for m in re.finditer(r'<a\b[^>]*href=["\']' + re.escape(url) + r'["\'][^>]*>(.*?)</a>', body, re.S):
                inner = visible(m.group(1))
                if inner.strip() and not has(inner, name):
                    fails.append(f'CARD {other}: a card links to {url} without the name "{name}"')
    return fails, warns, lock


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--site', required=True)
    ap.add_argument('--projects', required=True)
    A = ap.parse_args()
    cfg = json.load(open(os.path.join(A.site, 'tools', 'sources.json')))
    fails, warns, _ = run(A.site, A.projects, cfg)
    for w in warns: print(w)
    for f in fails: print(f)
    print(f'{len(fails)} name problem(s)' if fails else 'every recorded page, card and link uses the current names')
    sys.exit(1 if fails else 0)
