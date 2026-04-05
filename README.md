# Quick patch

> [!CAUTION]
> This is vulnerable to path traversal.
> Do not expose this.

```
git clone --bare $SOME_REPO $PATH
REPO=$PATH DEFAULT_BRANCH=$DEFAULT_BRANCH python3 quick_patch.py
```

Browse to <http://localhost:8000/$SOME_PATH_IN_THE_REPO>.
