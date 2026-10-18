# remote sync

two backends: **filesystem** (full clone/push/pull) and **github** (clone/push/pull via REST API).

```
oxidize remote clone <url> [target]
oxidize remote push  <url> [branch]
oxidize remote pull  <url> [branch]
```

## filesystem remote

`<url>` is any path to a directory. the remote is auto-initialized on first push as a bare repo.

```
oxidize remote push file:///srv/backup/myproj main
```

- objects copied by sha256 prefix, deduplicated by name
- atomic writes via temp-file-then-replace (no corrupt objects on crash)
- subtree-aware walk: nested directories are fully copied
- empty-destination fast path: first push/pull skips graph walk entirely
- `--force` overwrites divergent refs

### programmatic usage

```python
from pathlib import Path
from oxidize.network.remote import Remote

remote = Remote("file:///srv/backup")
repo = Repository(Path("."))
remote.push(repo, "main")
```

## github remote

clone/push/pull to a github repo via the Git Data REST API. no local `git` needed.

```
oxidize remote push https://github.com/user/repo.git main
```

set `OXIDIZE_GITHUB_TOKEN` in your environment (fine-grained PAT with `contents: write`).

how it works:
- oxidize objects use SHA-256, git uses SHA-1. an export map (`.oxidize/github_export_map.json`) tracks the mapping.
- blobs are pushed first (deduplicated by content). trees and commits are created via the GitHub API.
- the branch ref is updated at the end.
- 429 / 403 rate limits are retried with exponential backoff.

### programmatic usage

```python
from oxidize.network.github_remote import GitHubRemote

gh = GitHubRemote("user", "repo")
gh.push(repo, branch="main")
```

clone and pull from github are **not supported**. use `git clone` to fetch, then `oxidize` locally.

## not in v1

- remote tracking refs
- pull-request / webhook semantics
- LFS
- network transport beyond filesystem and github REST
