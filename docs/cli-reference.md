# cli reference

all commands work with both `oxidize` and `oxi` entry points.

```
oxidize [OPTIONS] COMMAND [ARGS]...
oxi    [OPTIONS] COMMAND [ARGS]...
```

## global options

| flag | description |
|------|-------------|
| `--version` | show version and exit |

---

## oxidize init

create a new oxidize repository.

```
oxidize init [PATH]
```

| argument | required | default | description |
|----------|----------|---------|-------------|
| `PATH` | no | `.` (current directory) | path where the repository should be created |

**what it does:**
- creates `.oxidize/` directory
- creates `objects/`, `refs/heads/`, `refs/tags/` subdirectories
- writes `HEAD` pointing to `refs/heads/main`
- initializes empty `index.json`
- writes a starter `.oxignore` with Python-appropriate defaults (only if no `.oxignore` already exists)

**errors:**
- `FileExistsError` if `.oxidize/` already exists at the target path

**examples:**
```bash
oxidize init                      # init in current directory
oxidize init my-project           # init in my-project/
oxidize init /path/to/project     # init at absolute path
```

---

## oxidize add

stage files for the next commit.

```
oxidize add [OPTIONS] <PATHS...>
```

| argument/flag | required | description |
|---------------|----------|-------------|
| `PATHS` | yes (one or more) | file or directory paths to stage (must exist) |
| `-f`, `--force` | no | bypass `.oxignore` rules for this invocation |

**what it does:**
- reads each file from disk
- computes SHA-256 hash, stores as a blob object (zlib-compressed)
- records the entry in the staging index with path, oid, mode, size, and mtime
- if a directory is given, recursively adds all files inside it
- files matching `.oxignore` patterns are skipped (printed as `ignored: <path>`)
- prints `staged: <path>` for each staged file

**examples:**
```bash
oxidize add main.py              # stage a single file
oxidize add main.py utils.py     # stage multiple files
oxidize add src/                 # stage all files in src/ recursively
oxidize add .                    # stage everything in the working tree
oxidize add -f .env.local        # stage an ignored file anyway
```

**notes:**
- files that don't exist will cause an error
- directories are traversed recursively
- each file gets its own blob object with a unique oid
- `.git/` and `.oxidize/` are always ignored (cannot be un-ignored)

---

## oxidize status

show the working tree status.

```
oxidize status
```

**no arguments or options.**

**what it displays:**

| section | color | meaning |
|---------|-------|---------|
| current branch | -- | the branch HEAD points to |
| staged | green | files in the index (ready to commit) |
| modified | yellow | files on disk that differ from their staged version |
| untracked | dim | files on disk not in the index |
| (ignored) | -- | files matching `.oxignore` patterns are never shown |

**staleness detection:**
uses mtime + size comparison (same heuristic as git's cache invalidation) to detect modifications without re-hashing files.

**examples:**
```
branch: main

staged:
  hello.py
  README.md

modified:
  hello.py

untracked:
  notes.txt
```

---

## oxidize ignores

inspect and test `.oxignore` rules.

```
oxidize ignores SUBCOMMAND
```

### subcommands

| subcommand | description |
|------------|-------------|
| `oxidize ignores list` | print every effective pattern (builtins first, then `.oxignore`) |
| `oxidize ignores check <PATHS...>` | test paths; exits `0` if all tracked, `1` if any ignored |

**ignores list output:**
```
builtins (always active):
  .git/
  .oxidize/

.oxignore patterns:
  __pycache__/
  *.pyc
  .env
```

**ignores check output:**
```
  main.py: tracked
  secret.env: ignored
```

**examples:**
```bash
oxidize ignores list                    # show rules
oxidize ignores check .env              # what would happen to `.env`?
oxidize ignores check src/ config.json  # check multiple paths
```

**see also:** [Ignores](ignores.md) for the full pattern grammar.

---

## oxidize commit

create a new commit from staged files.

```
oxidize commit [OPTIONS]
```

| flag | required | default | description |
|------|----------|---------|-------------|
| `-m`, `--message` | yes | -- | commit message |
| `--agent` | no | `None` | agent/tool name that produced this change |

**what it does:**
1. reads all entries from the staging index
2. builds a tree object (with proper subtrees for nested directories)
3. creates a commit object containing:
   - tree oid (snapshot of all staged files)
   - author (from env vars or config)
   - committer (same as author)
   - commit message
   - parent commit oid(s)
   - optional agent tag
4. stores the commit object
5. updates HEAD to point to the new commit
6. clears the staging index

**author resolution order:**
1. environment variables `OXIDE_AUTHOR_NAME` / `OXIDE_AUTHOR_EMAIL`
2. config file `[user] name` / `[user] email`
3. fallback: `"Unknown"` / `"unknown@example.com"`

**output format:**
```
[branch short_oid] [agent] message
```

**examples:**
```bash
oxidize commit -m "initial commit"
oxidize commit -m "fix bug" --agent "claude-code"
oxidize commit -m "add feature" --agent "cursor"
```

---

## oxidize log

show commit history.

```
oxidize log [OPTIONS]
```

| flag | required | default | description |
|------|----------|---------|-------------|
| `-n`, `--count` | no | `20` | maximum number of commits to display |

**what it displays for each commit:**
- commit oid (yellow, shortened)
- author name and email
- commit date
- commit message

**examples:**
```bash
oxidize log              # show last 20 commits
oxidize log -n 5         # show last 5 commits
oxidize log -n 1         # show only the latest commit
```

---

## oxidize diff

show differences between versions.

```
oxidize diff [OPTIONS] [PATHS...]
```

| argument/flag | required | default | description |
|---------------|----------|---------|-------------|
| `PATHS` | no | all files | specific files or directories to diff |
| `--cached` | no | `false` | show staged changes (index vs HEAD) instead of working tree vs index |

**two modes:**

| mode | what it compares | when to use |
|------|-----------------|-------------|
| default | working tree files vs staged blobs | see what you'd stage next |
| `--cached` | staged index entries vs HEAD tree | see what you'd commit |

**output:**
- uses `rich` console for colored output
- green = insertions
- red = deletions

**diff algorithm:**
Myers diff (O(ND) where D is edit distance).

**examples:**
```bash
oxidize diff                    # diff all working tree vs index
oxidize diff main.py            # diff specific file
oxidize diff src/               # diff all files in src/
oxidize diff --cached           # diff index vs HEAD (staged changes)
oxidize diff --cached main.py   # diff specific staged file
```

---

## oxidize scan

scan for secrets and credentials (respects `.oxignore`).

```
oxidize scan [OPTIONS] [PATHS...]
```

| argument/flag | required | default | description |
|---------------|----------|---------|-------------|
| `PATHS` | no | entire working directory | files or directories to scan |
| `--staged` | no | `false` | scan only files currently in the staging index |
| `--no-oxignore` | no | `false` | bypass `.oxignore` rules for this invocation (you should rarely need this) |

**what it detects (21 patterns):**

| category | patterns |
|----------|----------|
| cloud | AWS Access Key, AWS Secret Key, GCP API Key, Google OAuth Token |
| code hosting | GitHub PAT (`ghp_...`), GitHub Fine-Grained PAT (`github_pat_...`), GitLab PAT |
| communication | Slack Token, Slack Webhook, Twilio SID |
| payments | Stripe Secret Key |
| ai/ml | OpenAI API Key, OpenAI Project Key, Anthropic API Key, HuggingFace Token |
| email | SendGrid API, Mailgun API |
| generic | API Key, Private Key Block (RSA/EC/DSA/OPENSSH), JWT Token, Bearer Token, Generic Password |
| database | Connection String (postgres, mysql, mongodb, redis, amqp) |

**ignore rules:**
- the working directory has a hardcoded skip-list (`.oxidize/`, `.git/`, `__pycache__/`, `node_modules/`, `.venv/`, `venv/`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `*.egg-info/`, `dist/`, `build/`)
- **then** `.oxignore` filters further (the same patterns that `add`/`status` skip apply here too)
- pass `--no-oxignore` to scan *every* file regardless of `.oxignore` rules (useful for audits)

**output format:**
```
[type] file:line -- matched text
```

**examples:**
```bash
oxidize scan                     # scan entire working directory
oxidize scan main.py             # scan specific file
oxidize scan src/ lib/           # scan multiple paths
oxidize scan --staged            # scan only staged files
oxidize scan --no-oxignore       # audit everything; ignore .oxignore
```

**when secrets are found:**
the scanner prints each finding with the type, file path, line number, and the matched text. it does NOT block the operation -- it's informational.

---

## oxidize undo

reverse operations.

```
oxidize undo [SUBCOMMAND]
```

### subcommands

| subcommand | description |
|------------|-------------|
| `oxidize undo` or `oxidize undo last` | undo the most recent operation |
| `oxidize undo count N` | undo the last N operations |
| `oxidize undo journal` | display the full operation journal |

**supported undoable operations:**

| operation | what undo does |
|-----------|---------------|
| `commit` | restores HEAD to the previous commit (or removes HEAD for initial commit) |
| `add` | removes the files from the staging index |
| `branch_create` | deletes the branch ref file |
| `branch_delete` | restores the branch ref to its original oid |

**examples:**
```bash
oxidize undo                # undo last operation
oxidize undo last           # same as above
oxidize undo count 3        # undo last 3 operations
oxidize undo journal        # show the journal of recorded operations
```

**journal format:**
the journal is stored at `.oxidize/journal.json` as a JSON array of entries, each containing:
- `op` -- operation type (`add`, `commit`, `branch_create`, `branch_delete`)
- `timestamp` -- unix timestamp
- `data` -- operation-specific data
- `undo` -- data needed to reverse the operation

---

## command summary

| command | syntax | key flags |
|---------|--------|-----------|
| `init` | `oxidize init [PATH]` | -- |
| `add` | `oxidize add <PATHS...>` | -- |
| `status` | `oxidize status` | -- |
| `commit` | `oxidize commit -m MSG` | `--agent NAME` |
| `log` | `oxidize log` | `-n N` |
| `diff` | `oxidize diff [PATHS...]` | `--cached` |
| `scan` | `oxidize scan [PATHS...]` | `--staged` |
| `undo` | `oxidize undo [SUBCOMMAND]` | `count N`, `journal` |
