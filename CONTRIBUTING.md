# Contributing

## Commit identity

Every commit in this repository is authored and committed as the owner:

```
git config user.name  "<Owner Name>"
git config user.email "<owner's GitHub noreply email>"
```

- Use the GitHub noreply address above, never a personal email.
- Commits made with Claude end with one trailer, and nothing else: `Co-Authored-By: Claude <noreply@anthropic.com>`. No `Claude-Session:` lines or "Generated with" footers.
- Set the identity per repository (`git config`, not `--global`) before the first commit, and check it with `git log -1 --format='%an <%ae> | %cn <%ce>'` before pushing.
