# configuration

## config file

oxidize stores configuration in `.oxidize/config` using INI format.

### [user] section

| key | description | default |
|-----|-------------|---------|
| `name` | author name used in commits | `Unknown` |
| `email` | author email used in commits | `unknown@example.com` |

**example config file:**
```ini
[user]
name = Jane Doe
email = jane@example.com
```

### environment variables

environment variables override the config file.

| variable | purpose | overrides |
|----------|---------|-----------|
| `OXIDE_AUTHOR_NAME` | author name for commits | `[user] name` |
| `OXIDE_AUTHOR_EMAIL` | author email for commits | `[user] email` |

**resolution order for author info:**
1. `OXIDE_AUTHOR_NAME` / `OXIDE_AUTHOR_EMAIL` env vars (highest priority)
2. `[user] name` / `[user] email` in `.oxidize/config`
3. `"Unknown"` / `"unknown@example.com"` (fallback)

**examples:**
```bash
# set env vars for a session
export OXIDE_AUTHOR_NAME="Jane Doe"
export OXIDE_AUTHOR_EMAIL="jane@example.com"
oxidize commit -m "my commit"

# or set once in config
oxidize init
# then edit .oxidize/config manually
```

### agent detection environment variables

these are checked automatically to tag commits with agent provenance:

| variable | detected agent |
|----------|---------------|
| `CLAUDE_CODE` | `claude-code` |
| `GITHUB_COPILOT` | `github-copilot` |
| `CODEX_AGENT` | `codex` |
| `AIDER` | `aider` |

**note:** agent detection is optional. you can also manually specify the agent with `--agent` on the commit command.

## repository data files

all repository data lives under `.oxidize/`:

| file | format | purpose |
|------|--------|---------|
| `HEAD` | text | current branch pointer (e.g. `ref: refs/heads/main`) |
| `config` | INI | user settings |
| `index.json` | JSON array | staging area |
| `journal.json` | JSON array | undo journal |
| `objects/` | zlib-compressed files | all stored objects (blobs, trees, commits) |
| `refs/heads/` | text files | branch references (contain oids) |
| `refs/tags/` | text files | tag references |

## object storage layout

objects are stored at `.oxidize/objects/<first-2-hex-chars>/<remaining-hex-chars>`.

```
.oxidize/objects/
  a1/
    bcdef0123456789...    # blob, tree, or commit object
  f3/
    2109876543210abc...    # another object
```

each file contains `zlib.compress("type len\0" + data)` where type is `blob`, `tree`, or `commit`.

## index format

`.oxidize/index.json` is a JSON array of entry objects:

```json
[
  {
    "path": "main.py",
    "oid": "a1b2c3d4e5f6...",
    "mode": "100644",
    "size": 1024,
    "mtime": 1697000000.0
  }
]
```

| field | type | description |
|-------|------|-------------|
| `path` | string | relative file path from repository root |
| `oid` | string | SHA-256 hash of the blob |
| `mode` | string | file mode (`100644` regular, `100755` executable, `040000` directory) |
| `size` | int | file size in bytes |
| `mtime` | float | last modification time (unix timestamp) |

## journal format

`.oxidize/journal.json` is a JSON array of journal entries:

```json
[
  {
    "op": "commit",
    "timestamp": 1697000000.0,
    "data": {
      "commit_oid": "abc123..."
    },
    "undo": {
      "restore_to": "previous_head_oid_or_null"
    }
  }
]
```

| field | type | description |
|-------|------|-------------|
| `op` | string | operation type: `add`, `commit`, `branch_create`, `branch_delete` |
| `timestamp` | float | unix timestamp when operation occurred |
| `data` | object | operation-specific data (paths, oids, branch names) |
| `undo` | object | data needed to reverse the operation |

## history file

the interactive REPL persists command history to `~/.oxidize_history`.

this is a plain text file (one command per line) used by prompt_toolkit's `FileHistory`.
