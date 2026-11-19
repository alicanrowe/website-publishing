---
name: website-publishing
description: Use when adding or changing anything on the owner's site (the site-repo repo): a new project page, renders, a 3D viewer, dimension drawings, a spec table, photos, the home page or nav. Covers page structure, the brand theme on the web, the inline render/viewer/drawing layout, image and 3D optimisation, the screenshot check loop, and the PR and deploy flow.
metadata:
  author: Alican Rowe (@alicanrowe)
---

# Publishing to the owner's site

The site is plain files: Markdown notes in `content/`, built to static HTML by `tools/build.py`, hosted on Cloudflare Pages, which rebuilds on every push to `main`. Skills that make the work (furniture CAD, metal casting, concrete molds, robotics) hand their outputs to this skill for the site part.

## Before you touch a page
1. Pull the latest `main` (other sessions edit the site the same day) and work on your own branch.
2. Read `references/site-structure.md` (how a note becomes a page) and `references/brand-on-the-web.md` (fonts, colours, spacing, what never goes on the site).
3. Changing an existing page: read the whole note first. Hand-built pages carry their own `<style>` block; find the rule you need and change it there.
4. Screenshot the page as it is now (`--prefix before-`), so you have something to compare against.

## Standing rule: on theme and up to date (the owner)
The whole site stays on the brand theme, and every project page matches the latest version of that project: renders, 3D previews, specs, drawings and animations. When a project gets a new version anywhere (CAD, renders, a GLB in the project's files), the site's page, its home and category cards, and its 3D tile move to it in the same session. Before any site PR, run `theme_audit.mjs` on the whole site (no FAILs), `scripts/version_check.py` (a page using an older file than the repo already holds, and STALE: a still, PDF or video whose version is older than the 3D model on the same page, e.g. a v6 render beside a v7c GLB) and `scripts/source_check.py --projects <project files>` (a page whose source files in the project changed after the page's last commit: renders, buy lists, guides, firmware notes). `version_check` alone can't see a project that moved on outside the repo. Every page built from project files has an entry in the repo's `tools/sources.json`; add one when you build a page, and when a project gets a new pass (an audit, a redesign), rebuild every part of its page from the new outputs, not just the images.

## Making the change
- New project page: follow `references/adding-a-page.md` and start from `templates/project-page.md`.
- A piece with a model: render, 3D viewer and dimension drawing sit inline, side by side, with the spec table under them (`references/inline-layout.md`). Never put the viewer and its drawing in separate sections.
- Images, video and GLBs: size and compress them before committing (`references/media.md`). Full-size originals stay outside the repo.
- Someone else's image (a maker's product photo, a reference): their largest original, credited and linked in a mono caption under it.
- Show each project once per page: nothing in a grid that is already in the hero or a band above it.
- Project cards everywhere are the home page card: a 4:5 window on the cyc, the name in caps on the left and one fact in mono on the right (`.ar-cards` / `.ar-card`, or `%% portfolio %%`; see `references/inline-layout.md`). A project with a 3D model gets the model in its card, as on the home page.
- One header on every page, laid out as on the home page: work nav on the left, logo in the centre, studio nav on the right, a burger on phones. Nav buttons never move between pages. Every category in the nav links to its own page (`/sculpture`, `/robotics`), never to the home page or an anchor on it.
- Sculpture vs furniture: the owner's carved and cast pieces are sculpture even when they're usable (Studio Shrine Bench, Nine Rests sawhorses, the Moth case). The Furniture tab is only for Core Studio Furniture work. Ask before moving a piece between sections. On the home page, sculpture projects sit in the Sculpture group, never in a section of their own.
- Retired: Wood Lenses (removed 2026-11-18 at the owner's request; `/wood-lenses` redirects to `/robotics`; backup in the project files and git history). Don't bring it back unless the owner asks.
- No outside artists' names or inspiration credits on public pages. Credit only the maker of a photo or product that appears on the page.
- Renders for the site run on cloud machines (this session, RenderBeamer, GarageFarm), never on the owner's Mac; the Mac is only for downloads and moving files.
- When a project moves to a new version, every still on its page is re-rendered from the new model or taken down the same day. An old render stays up only in a section that says it's history (iterations, prototypes). Removed features go with their renders and captions (the Moth tool box, the stainless sheets).
- Every page is on the one site theme (shared light header, Newsreader 200/300, Plex Mono only for small numbers and dimensions, white page). There are no per-page custom themes: the Moth night band, script title and dark header were retired on 19 Nov 2026 at the owner's request. Don't add an exception to `theme_audit.mjs` ALLOW to get a page through.
- Only show finished work: final renders and site stills go up once the design is locked. A page about something unbuilt says so at the top.

## Check before the PR (make-and-check loop)
1. `python3 scripts/lint_page.py --site <repo> <page>`: no errors; read every warning on the page you touched.
2. `node scripts/shoot.mjs --site <repo> --out <dir> /<url>`: builds the site and screenshots the page at 1440 and 390 wide, and reports console errors, 404s, broken images, viewers that didn't load and sideways scroll on phone.
3. `node scripts/layout_check.mjs --site <repo> /<url>`: opens the page at 390, 768, 1024, 1280, 1440 (also at 2x), 1680 and 1920 wide. It flags anything that runs past the window edge or is cut off by its container, sideways scroll, and grid or flex rows whose items start more than 80 px apart (a viewer high and drawings far down beside it). No lines allowed.
4. Every 3D model with wood on the page: `python3 scripts/glb_grain_check.py model.glb` (decode meshopt first, see the script). Grain must run along every part. A web GLB exported from procedural grain has no real UVs, and an auto-unwrap lays the grain diagonally; fix with `scripts/glb_regrain.py`.
5. `node scripts/theme_audit.mjs --site <repo>`: every page on the site, checked against the brand theme in the browser. No FAIL lines (see `references/check-loop.md`).
6. Look at both screenshots against the brand, the page's neighbours on the site, and any reference the owner named. Write down everything that's off, fix it, shoot again. Repeat until nothing is on the list (`references/check-loop.md`).
7. Only screenshots that passed go to the owner.

## PR and deploy
Open a PR from your branch with before/after screenshots at both widths, then follow `references/pr-and-deploy.md`. When the checks pass, merge it yourself without asking (the owner's standing rule since 18 Nov 2026). Merging to `main` publishes the site in about a minute. Then run `node scripts/theme_audit.mjs --site <repo> --live https://alicanrowe.com /<url>`, which loads the published page cache-busted like a hard refresh. Check the live page at both widths, then send the owner the link. A page is done when the live audit passes, not when the branch does.

## Keep this skill improving
When a site change goes wrong, or the owner corrects something on a page, write the lesson into the matching reference (and `references/lessons.md`, dated) in the same session, add a check to `scripts/lint_page.py` if a script could have caught it, then commit and push to this skill's repo. No private data: no emails, home paths, client names or unpublished prices.
