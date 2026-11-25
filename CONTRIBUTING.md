# Contributing

## Commit identity

Changes go in as pull requests that are merged right away (merge commit, not squash).

Commits made with Claude are authored by Claude and committed as the owner, with the owner as co-author:

```
GIT_AUTHOR_NAME="Claude" GIT_AUTHOR_EMAIL="noreply@anthropic.com" git commit ...
git config user.name  "<Owner Name>"
git config user.email "<owner's GitHub noreply email>"
```

- The message ends with one trailer, and nothing else: `Co-Authored-By: Alican Rowe <357772129+alicanrowe@users.noreply.github.com>`. No `Claude-Session:` lines or "Generated with" footers.
- Commits the owner makes by hand are authored and committed as the owner with the noreply address above, never a personal email.
- Set the identity per repository (`git config`, not `--global`) and check it with `git log -1 --format='%an <%ae> | %cn <%ce>'` before pushing.
