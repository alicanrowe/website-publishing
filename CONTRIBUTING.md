# Contributing

## Commit identity

Every commit in this repository is authored and committed as alican:

```
git config user.name  "Alican Rowe"
git config user.email "357772129+alicanrowe@users.noreply.github.com"
```

- Use the GitHub noreply address above, never a personal email.
- Claude may be credited as a co-author with exactly one trailer at the end of the message: `Co-Authored-By: Claude <noreply@anthropic.com>`. Leave out `Claude-Session:` lines and "Generated with" footers.
- Never make Claude the author or committer, and don't rewrite history to change attribution.
- Set the identity per repository (`git config`, not `--global`) before the first commit, and check it with `git log -1 --format='%an <%ae> | %cn <%ce>'` before pushing.
