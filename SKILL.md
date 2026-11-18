---
name: website-publishing
description: Use when adding or changing anything on alicanrowe.com (the alicanrowe-site repo): a new project page, renders, a 3D viewer, dimension drawings, a spec table, photos, the home page or nav. Covers page structure, the brand theme on the web, the inline render/viewer/drawing layout, image and 3D optimisation, the screenshot check loop, and the PR and deploy flow.
metadata:
  author: Alican Rowe (@alicanrowe)
---

# Publishing to alicanrowe.com

The site is plain files: Markdown notes in `content/`, built to static HTML by `tools/build.py`, hosted on Cloudflare Pages, which rebuilds on every push to `main`. Skills that make the work (furniture CAD, metal casting, concrete molds, robotics) hand their outputs to this skill for the site part.

## Before you touch a page
1. Pull the latest `main` (other sessions edit the site the same day) and work on your own branch.
2. Read `references/site-structure.md` (how a note becomes a page) and `references/brand-on-the-web.md` (fonts, colours, spacing, what never goes on the site).
3. Changing an existing page: read the whole note first. Hand-built pages carry their own `<style>` block; find the rule you need and change it there.
4. Screenshot the page as it is now (`--prefix before-`), so you have something to compare against.

## Making the change
- New project page: follow `references/adding-a-page.md` and start from `templates/project-page.md`.
- A piece with a model: render, 3D viewer and dimension drawing sit inline, side by side, with the spec table under them (`references/inline-layout.md`). Never put the viewer and its drawing in separate sections.
- Images, video and GLBs: size and compress them before committing (`references/media.md`). Full-size originals stay outside the repo.
- Someone else's image (a maker's product photo, a reference): their largest original, credited and linked in a mono caption under it.
- Only show finished work: final renders and site stills go up once the design is locked. A page about something unbuilt says so at the top.

## Check before the PR (make-and-check loop)
1. `python3 scripts/lint_page.py --site <repo> <page>`: no errors; read every warning on the page you touched.
2. `node scripts/shoot.mjs --site <repo> --out <dir> /<url>`: builds the site and screenshots the page at 1440 and 390 wide, and reports console errors, 404s, broken images, viewers that didn't load and sideways scroll on phone.
3. Look at both screenshots against the brand, the page's neighbours on the site, and any reference alican named. Write down everything that's off, fix it, shoot again. Repeat until nothing is on the list (`references/check-loop.md`).
4. Only screenshots that passed go to alican.

## PR and deploy
Open a PR from your branch with before/after screenshots at both widths, then follow `references/pr-and-deploy.md`. Merging to `main` publishes the site in about a minute; check the live page once it's up.

## Keep this skill improving
When a site change goes wrong, or alican corrects something on a page, write the lesson into the matching reference (and `references/lessons.md`, dated) in the same session, add a check to `scripts/lint_page.py` if a script could have caught it, then commit and push to this skill's repo. No private data: no emails, home paths, client names or unpublished prices.
