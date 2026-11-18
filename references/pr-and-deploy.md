# PR and deploy

## Branch and commit
- Start from the latest `main`; several sessions change the site on the same day. Fetch again right before opening the PR and merge `main` in if it moved.
- One PR per change alican asked for. Don't fold unrelated fixes in.
- Commit message: page name, colon, what changed, in plain words (`MouthPad: add Augmental's product photo, credited, under The base`).
- Never commit `dist/`, `.imgcache/` or originals; `.gitignore` already excludes them.

## The PR
- Title like the commit.
- Body: what changed and where on the page, image sizes and sources, which widths were checked, and the before/after screenshots at desktop and phone.
- Follow any attribution lines and assignee or reviewer steps the session asks for.
- If the PR changes shared files (`static/assets/site.css`, `site.js`, `viewer.js`, `tools/build.py`, `site.json`), say so and screenshot two or three other pages that use them too.

## Deploy
Cloudflare Pages builds `main` with `pip install -r requirements.txt && python3 tools/build.py`, output `dist`, Python 3.12. Merging is publishing: the page is live about a minute later. Pull requests may get a Cloudflare preview link; use it for the final check when it's there.

After merge, open the live page at both widths and confirm the change is there and nothing else moved. If something broke, a revert PR is the fastest fix.

## Who merges
alican merges. A session can open, update and mark a PR ready, but merging (publishing) waits for alican, unless alican asked for that exact change to go live.
