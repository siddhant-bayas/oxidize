# remote sync

> ⚠ remote support is **filesystem-only** for now. Network protocols (HTTP, SSH) are not implemented yet.

```
oxidize remote clone <url> [target]    # "clone" from a bare directory
oxidize remote push <url> [branch]     # copy objects + refs to the remote
oxidize remote pull <url> [branch]     # fetch from the remote
```

`<url>` accepts any path that resolves to a directory containing `.oxidize/` (or to a bare directory with `HEAD` and `refs/`). A bare directory is auto-initialised on first push.

```
oxidize remote push file:///srv/oxidize/myproj main
```

**scope of v1**:
- objects are copied by sha256-prefix directory (`<aa>/<rest>`), de-duplicated by name
- `refs/heads/<branch>` is mirrored; one side per push unless `--force`
- `--force` overwrites divergent refs

**not in this scope**:
- remote tracking refs (`refs/remotes/<name>/*`)
- pull-request / webhook semantics
- LFS-style large-file hand-off
- any network transport beyond the local filesystem

`oxidize.network.remote.Remote` is the underlying class. Use it programmatically:

```python
from pathlib import Path
from oxidize.core.repository import Repository
from oxidize.network.remote import Remote

src = Repository(Path("."))
dst = Repository(Path("/backup"))
remote = Remote("/backup")
remote.push(src, "main")
remote.pull(dst, "main")
```
