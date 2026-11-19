# How the site is built

## Repo layout
| Path | What |
|---|---|
| `content/*.md` | One note per page. Notes starting with `_` are not published (`_How to edit.md` is the editing guide). |
| `content/img/<page>/` | Images for that page, lowercase-with-dashes names. |
| `content/files/` | Videos, PDFs, zips, anything that isn't an image. |
| `static/assets/` | `site.css`, `site.js`, `viewer.js` (3D), fonts, logo, vendored libraries (`vendor/`: model-viewer, meshopt decoder). |
| `static/3d/<page>/` | GLB models for the 3D viewer, served at `/3d/<page>/…`. |
| `site.json` | Site name, origin, nav items, redirects. |
| `tools/build.py` | The builder. |
| `preview/` | Reference screenshots of key pages. |

The content folder is also an Obsidian vault: the owner edits words there, so keep notes readable in Obsidian (sections, plain Markdown where possible).

## Build
```
pip install -r requirements.txt        # markdown, Pillow
python3 tools/build.py                  # writes dist/
SITE_OUT=/tmp/site python3 tools/build.py   # build somewhere else
python3 -m http.server -d dist          # preview at localhost:8000
```
The build copies `static/` and `content/files/` as they are, copies `content/img/` through the image optimiser (see media.md), renders every note, cache-busts `/assets/*.css|js` with a content hash, and writes `404.html`, `_redirects` (from `site.json`), `sitemap.xml` and `robots.txt`.

## A note
```
---
title: "mouthpad"
url: "/mouthpad"
nav: "robotics"
description: "One sentence for search results and link previews."
---
```
- `title`: the browser tab reads `title — the owner rowe`.
- `url`: the address. Sub-pages use a path (`/digital/syd`). Changing a live URL means adding the old one to `redirects` in `site.json`.
- `nav`: which nav label is highlighted (must match a label in `site.json`).
- `draft: true` hides the page. `unlisted: true` builds it but leaves it out of nav and sitemap, with `noindex`.
- `layout: raw`: the note is a complete HTML document written as is (only the home page uses this). No header, nav or footer is added for you.

## Sections
The body is a run of sections, each opened by an Obsidian comment line (hidden in Reading view):

| Marker | Renders |
|---|---|
| `%% text %%` | Markdown in a `.ar-text` column. The first `# Heading` is the page title. Text before any marker is text too. |
| `%% gallery grid cols=3 gap=12 ratio=4:3 %%` | One `![alt](img/…)` per line. `masonry` instead of `grid` keeps each image's shape; `inset` adds side margins. Add `<!-- 1600x1200 -->` after an image to give it width and height. |
| `%% portfolio %%` | The tile grid used on index pages: `[![Name](img/…)](/url)` then indented spec lines. |
| `%% html %%` | Hand-built HTML, written as is. Relative `img/` and `files/` paths are made absolute for you. |
| `%% text area=1/2/3/4 %%` | Places a section in a grid area (rarely used). |

## One project, one place per page
Never show the same project twice on one page. If a project is already in the hero or a band at the top, it stays out of the grid groups below, even when it belongs to that group. Small text links ("designed with…", "all skills") are fine; a second tile, band or hero is not. `lint_page.py` errors when two sections link tiles to the same page (anchors such as `/nine-rests#rest` count as `/nine-rests`).

## Hand-built pages
Most project pages (moth, mouthpad, dancers, the robot project, k) are mostly `%% html %%` with one `<style>` block near the top.
- Give every class on the page a short page prefix (`mp-` for mouthpad, `ds-` for moth) so rules can't leak into other pages or the shared CSS.
- Use the theme variables already in `site.css` (`--ar-ink`, `--ar-mono`, `--ar-serif`, `--ar-nav`, `--ar-image-fill`) rather than typing colours and fonts again.
- Change a rule where it is. Appending another override for the same selector (with `!important`) is how the moth page ended up with six `.ds-stand` rules fighting each other. `lint_page.py` warns at three.
- Words stay editable: keep copy in plain `<p>` tags, not inside SVG paths or images.

## 3D viewer (`/assets/viewer.js`)
Load the script once on the page: `<script src="/assets/viewer.js" defer></script>`. Each viewer:
```html
<div class="ar3d pp-3d" style="--h:min(64vh,560px)" data-src="/3d/page/model.glb"
     data-orbit="35deg 75deg auto" data-spin="slow" data-alt="What the model shows, in a sentence">
  <div class="ar3d-stage"></div>
  <div class="ar3d-cap"><span class="ar3d-name">Caption</span><span>Drag to turn</span></div>
</div>
```
model-viewer only loads when a viewer nears the screen. Options: `data-orbit` (start camera), `data-maxorbit`, `data-spin` (`off`, `slow`, default fast), `data-anim` (a clip name in the GLB; `data-then` plays a second clip after it), `data-ring` (JSON list of names: the moth tool ring). `--h` sets the stage height. The box gets `is-ready` once the model has loaded.
