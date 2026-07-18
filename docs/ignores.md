# ignores

oxidize reads a `.oxignore` file at the repository root to decide which files should never be tracked. the syntax and behavior mirror git's `.gitignore`, with a small set of oxidize-specific builtins.

## the file

```text
<work_tree>/.oxignore
```

written automatically by `oxidize init` if it does not exist. delete it to disable, or edit it any time.

## pattern grammar

each non-empty, non-comment line is a glob, evaluated against the relative path from the repository root (forward slashes, even on windows).

| syntax | meaning | example |
|--------|---------|---------|
| `name` | match a file or directory anywhere in the tree | `secrets.env` |
| `/name` | anchored to the repo root | `/.env` |
| `dir/` | match a directory and everything inside it | `build/`, `dist/` |
| `*.ext` | wildcard | `*.log`, `*.pyc` |
| `**/name` | match at any depth | `**/__pycache__/` |
| `!pattern` | negation -- re-include a file matched by an earlier rule | `*.log`, `!errors.log` |
| `#...` | comment | `# python build output` |
| blank line | ignored | |

patterns follow the same rules as `.gitignore` -- the underlying matcher is `pathspec.PathSpec` with the `gitwildmatch` style.

## builtins

two patterns are always active and **cannot** be unignored via `!` rules:

| pattern | reason |
|---------|--------|
| `.git/` | cooperates with git users; oxidize stores its own data under `.oxidize/` |
| `.oxidize/` | internal object store must never be staged |

trying to write `!.git/` in your `.oxignore` is a no-op.

## commands affected

| command | behavior |
|---------|----------|
| `oxidize add <paths>` | ignored files skipped; printed as `ignored: <path>` |
| `oxidize add -f <paths>` | bypasses `.oxignore` for this invocation |
| `oxidize status` | ignored files are never shown |
| `oxidize scan` | skipped, but `--no-oxignore` bypasses for a one-shot audit |
| `oxidize scan --staged` | ignored staged files are skipped |
| `oxidize ignores list` | prints effective patterns (builtins + `.oxignore`) |
| `oxidize ignores check <p>` | tests paths; exits `1` if any are ignored (CI use) |

## starter file

`oxidize init` writes this if no `.oxignore` already exists:

```gitignore
# python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.egg-info/
.eggs/

# virtualenvs
.venv/
venv/
env/

# build output
dist/
build/

# testing / linting caches
.mypy_cache/
.pytest_cache/
.ruff_cache/
.coverage
htmlcov/

# environment
.env
.env.*

# editor / OS
.vscode/
.idea/
.DS_Store
```

delete the file, edit entries inline, or drop your own rules in any time -- changes take effect on the next `oxidize add`, `status`, or `scan` invocation.

## programmatic access

```python
from pathlib import Path
from oxidize.core.ignores import IgnoreMatcher

patterns = IgnoreMatcher.starter_content().splitlines()
matcher = IgnoreMatcher(patterns, Path("."))
matcher.is_ignored("build/app.o")     # True
matcher.is_ignored("src/main.py")     # False
matcher.is_ignored(".oxidize/HEAD")   # True (builtin)
```
