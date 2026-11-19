# The make-and-check loop for site changes

Nothing goes to the owner, and no PR opens, until the page has passed this loop.

## 1. Shoot "before"
```
node scripts/shoot.mjs --site <repo> --out <dir> --prefix before- /page
```
Builds the site to a temp folder, serves it locally, scrolls the page so lazy images and 3D viewers load, and saves full-page screenshots at 1440 x 900 (desktop) and 390 x 844 (phone). It also reports console errors, any 404, broken images, 3D viewers that didn't load, and a page that scrolls sideways on phone. Exit code 2 means it found something.

Options: `--scale 2` for screenshots a person will see, `--only desktop|phone`, `--wait 4000` for heavy models, `--no-build` to reuse the last build. Needs Node with Playwright; on a cloud machine it is usually already installed.

## 2. Make the change, then lint
```
python3 scripts/lint_page.py --site <repo> page
```
Errors must be fixed (missing files, links to pages that don't exist, images without alt, a viewer without viewer.js). Read every warning for the page you touched.

## 3. Shoot "after" and look
Open both widths and look at them as the owner would. Compare against:
- the brand (brand-on-the-web.md): fonts, weights, greys, gaps, no boxes or shadows;
- the neighbouring pages on the site (same title size, same caption style, same gaps);
- any reference the owner named, and the "before" shot.

Write down every problem as a list: alignment, cropping, text too small or too faint, captions that wrap badly, a viewer framed too tight, a drawing whose labels are unreadable on phone, a gap that's bigger on one side, anything that moved that shouldn't have.

## 3b. Theme audit across the whole site
```
node scripts/theme_audit.mjs --site <repo>
```
Builds the site and opens **every** page at 1440 and 390, reads what the browser actually draws (computed styles, not the source) and flags: fonts other than Newsreader / Plex Mono, Newsreader asked for at 400+, text colours outside the grey inks and nav colours, text on coloured plates, a page background that isn't white, boxes with a border all round, rounded corners, shadows and gradients, and any page whose header (nav labels, order, logo position, nav size and colour, bar colour) differs from the rest. Run it for every PR, not just the page you touched: a change to `site.css`, `site.json` or the home page's own header reaches pages you never opened. A FAIL is fixed before the PR, or added to `ALLOW` in the script with the reason once it is approved (the moth custom theme, drawn app screens). Exit code 1 means a FAIL.

## 3b2. Layout at every width
```
node scripts/layout_check.mjs --site <repo> /page        # or --all
```
Window widths 390, 768, 1024, 1280, 1440 (and 1440 at 2x), 1680, 1920. Flags CLIP (an element past the window edge, or cut off by an ancestor with overflow hidden), SCROLL (sideways scroll) and ALIGN (items of one grid or flex row starting more than 80 px and 20% of the row apart). Decorative backdrops marked aria-hidden are skipped. A 3D viewer next to drawings and a spec column is the classic ALIGN failure: align the row to the top and give the viewer the drawings' height, and put long spec lists in their own full-width row.

## 3c. Latest version everywhere
```
python3 scripts/version_check.py --site <repo>
python3 scripts/source_check.py --site <repo> --projects <project files root> --write-lock   # pages older than their project sources, and files older than the newest model version (tools/sources.json); refreshes tools/versions.lock.json for the build gate
```
Lists every page that uses a model or render when the same folder holds a later version of it (v6s next to v6w, r9 next to r10), and every STALE still, PDF or video whose version token is older than the newest GLB of the same project on that page (moth-v6pa-*.jpg beside moth-case-v7c-lite.glb). Intentional history (iteration option labels, drawings confirmed current) goes in the script's ALLOW list with the reason. the owner's rule: every page, card and 3D tile shows the latest version of its project. Also compare the project's own files (CAD, renders, GLBs in the project folder) with what the site holds; a newer version there means the site gets it in the same session.

Version lines in `tools/sources.json` (per page): `{"line": "case", "model": "<glob of the full models in the project files>", "match": "<regex for the site files that follow it>"}`. The newest version token the glob finds (v7e > v7d > v7 > v6s) is "current". A glob that finds nothing fails too. The build gate (`version_gate()` in the site's build.py) checks every page against every line, so home cards and category tiles are held to the same version as the project page.

## 3d. Wood and flicker on 3D models
```
python3 scripts/glb_grain_check.py model.glb        # UVs: grain along every part
python3 scripts/glb_texture_check.py model.glb      # the texture itself: straight grain along U, not flat-sawn figure
blender -b -P scripts/glb_zfight_check.py -- model.glb   # coincident surfaces of different materials (flicker)
blender -b -P scripts/glb_zfight_fix.py -- in.glb out.glb # sink covered vertices (--delete removes faces: tore thin parts once)
blender -b -P scripts/glb_fidelity_check.py -- full.glb web.glb   # every part of the web model against the full model: crushed, torn, missing
```
Then look at the model in the viewer up close from three sides: numbers alone passed a swirly texture once.

## 4. Fix and repeat
Fix the list, shoot again, look again. Repeat until a pass finds nothing. Then check one level wider: the index page that links to it, and the home page if it changed.

## 5. Show
Post the passing desktop and phone screenshots (at `--scale 2`) with the PR. Keep them in the project's files next to the work (`<project>/site-checks/`).

## Things that only show up in a real browser
- 3D viewers: check the model's starting angle, that it isn't clipped, and that it loads on phone. Drag it once.
- Motion (the home page plumb line, fades): take a short screen recording or several screenshots at different scroll positions; one still won't show it. Headless SwiftShader runs slowly, so physics takes far longer to settle than on a real device: wait 30 s or force the end state (for example add `.on`) to shoot it.
- The live site after deploy: `https://<site>/<page>` (Cloudflare can take a minute; reload without cache).
