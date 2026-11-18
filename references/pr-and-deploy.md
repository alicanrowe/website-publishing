# PR and deploy

## Branch and commit
- Commit as alican, per repo (not `--global`): `git config user.name "Alican Rowe"`, `git config user.email "357772129+alicanrowe@users.noreply.github.com"`, `git config commit.gpgsign false`. No session links or "generated with" footers; check with `git log -1 --format='%an <%ae> | %cn <%ce>'` before pushing. The site repo's CONTRIBUTING.md has the same rule.
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
The session that opened the PR merges it when it is ready, without asking. This is alican's standing rule (18 Nov 2026: "merge without asking forever"). Ready means: the checks in SKILL.md passed (lint, shoot, theme_audit with no FAIL), the screenshots were looked at and the fix list is empty, and the branch is up to date with `main`. Then merge, open the live page at both widths, and tell alican it is live with the link. Don't wait for a reply first, and don't ask "shall I merge?".

Still stop and ask before merging only when the PR does something alican didn't ask for (see the scope rule in SKILL.md) or a check is still failing. A merge is easy to undo with a revert PR, so when unsure whether something looks right, merge, say what you're unsure of, and revert if alican says so.
