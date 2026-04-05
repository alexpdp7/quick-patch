# Quick patch

> [!CAUTION]
> This is vulnerable to path traversal.
> Do not expose this.

A non-functional-yet prototype web application about making quick patches to a Git repository.

Create a bare Git repo, for example with:

```
git clone --bare $SOME_REPO $PATH
```

Start a test web server pointing to the bare Git repo:

```
REPO=$PATH DEFAULT_BRANCH=$DEFAULT_BRANCH python3 quick_patch.py
```

Browse to <http://localhost:8000/$SOME_PATH_IN_THE_REPO>.

## Full explanation

I am trying to move away from GitHub and Git forges in general to simpler web hosting. (For example, using [cgit](https://git.zx2c4.com/cgit/about/)).

One feature I miss is that I could create URLs pointing to the edit feature on GitHub.

For example, I generate my blog using a static site generator.
I can add a link to each blog entry that pops us an editor so that people with a GitHub account can send a typo fix that I can apply with very few steps.

This projects tries to replicate this feature, lifting the GitHub account requirement.

However, I have not figured out how to ship the patch in a convenient way for submitter and maintainer.
Some ideas in my head are:

* Using `mailto:` links
* Armoring the patch with Base64 encoding
* Dropping format patches or even work trees/branches somewhere in the filesystem

Contact me (or send a patch) if you have an idea.
