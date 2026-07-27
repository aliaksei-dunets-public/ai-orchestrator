# Git Commands by Mode

Use native Git commands. Do not depend on shell-specific fallbacks unless
required by the active shell. Load only the section matching the resolved mode.

## Staged

```bash
git status --short
git diff --cached --name-status --find-renames
git diff --cached --no-ext-diff --find-renames --unified=80 -- .
```

## Working tree

```bash
git status --short
git diff --name-status --find-renames
git diff --no-ext-diff --find-renames --unified=80 -- .
git ls-files --others --exclude-standard
```

## Commit

```bash
git show --format= --name-status --find-renames <commit>
git show --format= --find-renames --unified=80 <commit> -- .
```

## Pull request / branch range

Determine the trusted base branch, fetch only when allowed, then resolve the
merge base in one command and use the returned SHA in the next commands:

```bash
git merge-base HEAD <trusted-base>
git diff --name-status --find-renames <merge-base-sha>..HEAD
git diff --find-renames --unified=80 <merge-base-sha>..HEAD -- .
```

## Full

```bash
git ls-files --cached --others --exclude-standard
```

## Exclusions

Exclude `.git`, dependency caches, build outputs, minified bundles, generated
artifacts, and vendored code unless the change directly affects them or the user
explicitly requests them.
