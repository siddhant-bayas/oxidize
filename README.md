# oxidize

a content-addressable, semantic-aware version control system -- built from scratch in a weekend, kept (painfully) honest since.

[![ci](https://github.com/siddhant-bayas/oxidize/actions/workflows/ci.yml/badge.svg)](https://github.com/siddhant-bayas/oxidize/actions/workflows/ci.yml)
[![pypi](https://img.shields.io/pypi/v/pyoxidize)](https://pypi.org/project/pyoxidize/)
[![python](https://img.shields.io/badge/python-3.11%2B-blue)](https://pypi.org/project/pyoxidize/)
[![size](https://img.shields.io/badge/pip_install_size-tiny-blue)](#install--dependencies)

## install

```bash
pip install pyoxidize                       # core
pip install "pyoxidize[semantic]"           # tree-sitter AST diffs
pip install "pyoxidize[notebook]"           # jupyter integration
pip install "pyoxidize[dev]"                # pytest, mypy, ruff
```

optional extras add `tree-sitter`, `nbformat`, etc. core itself pulls in only `click`, `rich`, `prompt_toolkit`, `deepmerge`, `pathspec` -- no native bindings, no large free-threaded runtime.

## why not just use git?

| need | git | oxidize |
|------|-----|---------|
| commit / branch / merge | ✅ | ✅ |
| real structured merge for json/yaml/toml/inipath | ❌ (line-level) | ✅ |
| cell-level notebook diffs | ❌ | ✅ |
| AST-aware diffs (function renames) | ❌ | ✅ (opt-in via the `semantic` extra) |
| secret scanning before commit | ❌ (out-of-tree tooling) | ✅ 21 patterns |
| ai-agent provenance per commit | ❌ | ✅ `oxidize log --agent ...` |
| interactive REPL with status bar | ❌ | ✅ |
| safe undo of every operation | ❌ | ✅ |
| local-self-contained footprint | ⚠ git + curl + ssh | ✅ one pip package |
| LFS over network | ✅ | ⏳ (filesystem remote only) |

oxidize is **not** a git replacement for big teams or monorepos. it's a focused, single-binary, Python-venv-friendly alternative for personal and small-team projects where the semantic and provenance extras matter more than SSH-authenticated push.

## feature status

| feature | status | since |
|---------|--------|-------|
| content-addressable store, blob/tree/commit | stable | v0.1.0 |
| recursive-tree directories | stable | v0.1.0 |
| `.oxignore` with full `.gitignore` syntax | stable | v0.1.0 |
| secret scanner (23 patterns) | stable | v0.1.0 |
| structured data merge | stable | v0.1.0 |
| notebook cell-level diff | stable | v0.1.0 |
| interactive REPL (`oxi`) | stable | v0.1.0 |
| safe undo (journaled) | stable | v0.1.0 |
| branches / tags / checkout / 3-way merge | stable | v0.1.0 |
| conflict resolution UI (`oxidize resolve`) | stable | v0.1.0 |
| ai-agent provenance + filtering | stable | v0.1.0 |
| ai-agent detection env-var coverage | stable | v0.1.0 |
| stash | beta | v0.1.0 |
| bisect | beta | v0.1.0 |
| hooks (`pre-commit`, etc) | beta | v0.1.0 |
| blame (line-level) | beta | v0.1.0 |
| remote sync (filesystem only) | beta | v0.1.0 |
| semantic diffs (AST-aware, `tree-sitter`) | alpha | v0.2.1 |
| ai-agent prose locking + qa | (planning) | -- |
| network remotes (http, ssh) | not yet | -- |
| LFS-style large-file extension | not yet | -- |
| submodule support | not yet | -- |

## quick start

```bash
oxidize init                            # create .oxidize/ and a starter .oxignore
oxi add main.py                         # stage a single file (or use the alias)
oxi add .                               # stage everything (respects .oxignore)
oxi add -f .env.local                   # force-add an ignored file
oxi status                              # working tree vs index vs HEAD
oxi commit -m "first commit" --agent claude-code
oxi branch create feature               # branch off HEAD
oxi checkout feature                    # switch branches
oxi merge main                          # three-way merge
oxidize remote push file:///backup main # filesystem remote
oxi bisect start v1.0 broken            # binary-search regressions
oxi                                     # drop into the interactive REPL
```

## the REPL

```
oxi> status
On branch main
  staged:
    hello.py
  modified:
    README.md
    (main) main | staged:1 | HEAD:9ecfb22c | Ctrl-D exit | help for commands
```

launching `oxi` with no args opens a prompt_toolkit REPL with tab completion, history (`~/.oxidize_history`), and a live status bar showing the current branch, staged count, and short HEAD. every command above also works inside it.

## features (the headline ones)

* **content-addressable object store** -- SHA-256, zlib-compressed, deduplicated
* **recursive tree objects** -- proper nested directory tracking
* **interactive REPL** -- `oxi` launches a shell with tab completion, live status bar, command history
* **secret scanning** -- detects 21 types of API keys, tokens, and credentials before commit
* **structured data merge** -- JSON/YAML/TOML merge at the key level, not text lines
* **notebook-aware versioning** -- cell-level diffs for `.ipynb` files
* **AI agent provenance** -- track which agent/tool wrote what code
* **built-in undo** -- every operation is safely reversible
* **branches, tags, checkout, merge, resolve** -- full VCS primitives
* **stash / bisect / hooks** -- everyday workflow commands
* **filesystem remote sync** -- bare-repo clone/push/pull (network protocols coming)
* **semantic diffs (alpha)** -- AST-aware diffs via the `semantic` extra

## docs

* [Getting Started](docs/getting-started.md) -- installation, quick start, basic workflow
* [CLI Reference](docs/cli-reference.md) -- every command, flag, and parameter
* [Configuration](docs/configuration.md) -- config files, environment variables
* [Interactive Shell](docs/repl.md) -- the `oxi` REPL
* [Ignores](docs/ignores.md) -- `.oxignore` patterns, builtins, force usage
* [Branching & Merging](docs/branching.md) -- branches, checkout, 3-way merge, conflicts
* [Workflow Commands](docs/workflow.md) -- stash, bisect, hooks, tags, blame, notebook-diff
* [Remote Sync](docs/remote.md) -- filesystem-only clone/push/pull (beta)
* [Undo System](docs/undo.md) -- reversing operations
* [Semantic Diffs](docs/semantic-diffs.md) -- AST-aware diffs
* [Notebook Support](docs/notebook-support.md) -- Jupyter notebook versioning
* [Structured Merge](docs/merge.md) -- key-level data merging
* [Changelog](CHANGELOG.md)
* [Agent Provenance](docs/provenance.md) -- AI agent tracking
* [Object Storage](docs/storage.md) -- storage internals
* [Python API Reference](docs/api-reference.md) -- complete Python API
* [Architecture](docs/architecture.md) -- system design and internals
* [Contributing](docs/CONTRIBUTING.md) -- development setup and guidelines

## how it works

every file you add gets hashed using SHA-256 and stored as a blob inside `.oxidize/objects/`

a commit is just:

* a snapshot of the file tree (with proper subtrees for nested dirs)
* metadata (author, timestamp, agent provenance)
* a pointer to the previous commit(s)

```txt
files -> blobs -> tree -> commit -> commit -> commit
                                     ^
                                    HEAD
```

## structure

```txt
oxidize/
  objects/       blob tree commit types and serialization
  storage/       content-addressable object store
  index/         staging area
  core/          repo context refs config ignores
  diff/          myers diff engine
  merge/         structured + text merge
  notebook/      ipynb cell-level support
  semantic/      ast-aware diffs via tree-sitter
  security/      secret scanning
  provenance/    ai agent tracking
  undo/          operation journal and reversal
  workflow/      stash, bisect, hooks, blame
  network/       filesystem remote sync
  staging/       stash
  cli/           click commands and prompt_toolkit repl
```

## contributing

see [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)

## license

MIT

~ written by a guy who discovered hashing yesterday
