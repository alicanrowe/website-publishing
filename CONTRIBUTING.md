# Contributing

## Commit identity

Changes go in as pull requests that are merged right away (merge commit, not squash).

Every commit is authored and committed as the owner, with Claude as co-author when Claude helped:

```
git config user.name  "<Owner Name>"
git config user.email "<owner's GitHub noreply email>"
git -c commit.gpgsign=false commit ...
```

- The message ends with one trailer, and nothing else: `Co-Authored-By: Claude <noreply@anthropic.com>`. No `Claude-Session:` lines or "Generated with" footers.
- Never a personal email; always the noreply address above.
- Set the identity per repository (`git config`, not `--global`) and check it with `git log -1 --format='%an <%ae> | %cn <%ce>'` before pushing.
