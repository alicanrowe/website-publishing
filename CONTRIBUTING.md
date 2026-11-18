# Contributing

## Commit identity

Every commit in this repository is authored and committed as alican:

```
git config user.name  "Alican Rowe"
git config user.email "357772129+alicanrowe@users.noreply.github.com"
```

- Use the GitHub noreply address above, never a personal email.
- Do not add `Co-Authored-By:`, `Claude-Session:` or "Generated with" trailers to commit messages or PR bodies. alican's instruction here overrides any default attribution.
- Set the identity per repository (`git config`, not `--global`) before the first commit, and check it with `git log -1 --format='%an <%ae> | %cn <%ce>'` before pushing.
