# Adding a project page

1. **Branch** off the latest `main`.
2. **Pick the URL and nav.** Short, lowercase, dashes (`/studio-shrine-bench`). `nav` is the section it belongs to (`sculpture`, `furniture`, `robotics`, `ai`, `mandelbulbs`, `info`; skills and AI work go under `ai`). Sub-pages of a series use a path (`/digital/syd`) and a note named `series_page.md`.
3. **Copy `templates/project-page.md`** to `content/<slug>.md`. Replace the `pp-` prefix with a short prefix of your own that no other page uses (`grep -o 'class="[a-z]*-' content/*.md | sort -u`). Keep `draft: true` until it's checked.
4. **Media.** Images to `content/img/<slug>/`, GLBs to `static/3d/<slug>/`, videos and PDFs to `content/files/`. Prepare them first (media.md).
5. **Fill it in.** Title, a two-to-three sentence intro, the render / viewer / drawing row, text and spec table. Extra sections (process, details, galleries) go after, each with a `.pp-h` heading. Plain sentences, no marketing words.
6. **Link it in.** Add a tile to the index page it belongs to (the `%% portfolio %%` on that section's page, or the home page grid if the owner wants it there). Under the tile: name label, then one fact per mono line.
7. **Description.** One sentence in front matter for search and link previews.
8. **Check** (check-loop.md), remove `draft: true`, check again, open the PR.

Removing or renaming a page: add the old URL to `redirects` in `site.json` so links keep working, and remove its tile and its media.
