# architecture

## overview

oxidize is a version control system built from scratch in python. it uses content-addressable storage (SHA-256), a commit DAG, and a staging index -- similar to git in spirit but with additional features: semantic awareness, built-in undo, an interactive shell, secret scanning, notebook-aware versioning, structured data merging, and AI agent provenance tracking.

## object model

```
commit -> tree -> blob(s)
  |
parents[]
```

every object is hashed as `sha256("type len\0" + data)`. identical content always produces identical oids regardless of when or where it was stored.

### object types

| type | stores | serialization |
|------|--------|---------------|
| `blob` | raw file content | raw bytes |
| `tree` | directory snapshot | binary: `"{mode} {name}\0{oid_bytes}"` per entry |
| `commit` | snapshot + metadata | text: tree/parent/agent/author/committer header + message |

## storage

the default backend stores objects at `.oxidize/objects/xx/yyyy...` where `xx` is the first two hex chars of the oid. objects are zlib-compressed.

`StorageBackend` is an abstract class with three methods: `read`, `write`, `exists`. swap in a database, S3, or in-memory backend by implementing these.

## index

the staging area is a JSON file at `.oxidize/index.json`. each entry records the file path, oid, mode, size, and mtime. staleness detection compares mtime and size against the current filesystem state -- same heuristic git uses for its cache invalidation.

## refs

references live as plain text files under `.oxidize/refs/heads/`. HEAD is either a symref (`ref: refs/heads/main`) or a detached oid. this is identical to git's ref layout and intentionally compatible.

## dependency order

```
objects -> storage -> index -> core -> cli
```

no layer imports from a layer above it. the cli is a pure dispatch layer.

```
oxidize/
  objects/       blob tree commit types and serialization
  storage/       content-addressable object store (abstract backend + filesystem impl)
  index/         staging area with staleness detection
  core/          repository context, refs, config
  diff/          myers diff engine (O(ND))
  merge/         structured data merge (json/yaml/toml key-level)
  notebook/      ipynb cell-level support
  semantic/      ast-aware diffs via regex extraction
  security/      secret scanning (21 patterns)
  provenance/    ai agent tracking
  undo/          operation journal and reversal
  cli/           click commands and prompt_toolkit repl
```

## data flow

```
files -> blobs -> tree -> commit -> commit -> commit
                                            ^
                                           HEAD
```

1. `oxidize add` reads files, stores as blobs, records in index
2. `oxidize commit` builds a tree from index entries, creates a commit pointing to that tree
3. HEAD is updated to the new commit
4. index is cleared

## cli and interactive shell

both `oxidize` and `oxi` are entry points that accept the same subcommands.

- `oxidize` maps to the click group in `cli/main.py`
- `oxi` maps to `cli/repl.py` which checks `sys.argv` -- if arguments are present it delegates to the click group, otherwise it launches the prompt_toolkit-based REPL

### repl features

- tab completion for commands, file paths, and branch names
- live status bar showing branch, staged count, and untracked count
- command history persisted to `~/.oxidize_history`
- aliases: `s` -> status, `c` -> commit, `a` -> add, `l` -> log, `d` -> diff

## security / secret scanning

`oxidize scan` detects API keys, tokens, private keys, and credentials using 21 regex patterns. runs on the working directory or staged files. covers AWS, GCP, Azure, GitHub, GitLab, Slack, Stripe, OpenAI, Anthropic, and generic patterns.

## structured data merge

for JSON, YAML, and TOML files, merge operates at the key level instead of text lines. three-way merge: base + ours + theirs. conflicts only when both sides changed the same key to different values.

## notebook support

`.ipynb` files are treated as structured documents, not text blobs. cell-level diffing, automatic output stripping, and execution count removal keep diffs clean.

## semantic diffs (experimental)

uses regex-based extraction to parse source code into entities (functions, classes, methods). diffs at the entity level. can track renames by comparing structural hashes.

## AI agent provenance

commits can be tagged with agent metadata (`--agent "claude-code"`). the provenance journal tracks which agent/tool/prompt produced each change. auto-detection via environment variables.

## undo system

every mutation writes to `.oxidize/journal.json`. `oxidize undo` reverses the last operation. supported: commit (restore HEAD), add (remove from index), branch create (delete ref), branch delete (restore ref).

## CI/CD

- **ci.yml** -- runs on push/PR to main. lint (ruff), typecheck (mypy), tests (pytest) across python 3.11, 3.12, 3.13. builds the package.
- **pypi.yml** -- triggers on GitHub release publish. builds and uploads to PyPI via trusted publishing (OIDC).
