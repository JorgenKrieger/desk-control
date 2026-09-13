# git hooks

`pre-commit` runs [gitleaks](https://github.com/gitleaks/gitleaks) against
staged changes before every commit, so a secret can't accidentally get
committed. Requires `gitleaks` installed locally (`brew install gitleaks`).

`.git/hooks` isn't version-controlled, so this only takes effect once per
clone:

```bash
git config core.hooksPath .githooks
```
