# oxidize

a version control system built from scratch with semantic awareness, built-in undo, and an interactive shell

[![ci](https://github.com/siddhant-bayas/oxidize/actions/workflows/ci.yml/badge.svg)](https://github.com/siddhant-bayas/oxidize/actions/workflows/ci.yml)
[![pypi](https://img.shields.io/pypi/v/pyoxidize)](https://pypi.org/project/pyoxidize/)
[![python](https://img.shields.io/pypi/pyversions/pyoxidize)](https://pypi.org/project/pyoxidize/)

## what it does

tracks file snapshots using content-addressable storage (SHA-256), a commit DAG, and a staging index -- but unlike git it also understands your code's structure.

```bash
# install
pip install pyoxidize

# or with extras
pip install "pyoxidize[semantic]"     # ast-aware semantic diffs
pip install "pyoxidize[notebook]"     # jupyter notebook support
pip install "pyoxidize[dev]"          # dev tools (pytest, mypy, ruff)

# basic usage
oxidize init
oxidize add file.py
oxidize status
oxidize commit -m "first commit"
oxidize log

# or use oxi (shorter alias)
oxi init
oxi add file.py
oxi status
oxi commit -m "first commit"
oxi log

# interactive shell (no args launches the REPL)
oxi
```

## features

* **content-addressable object store** -- SHA-256, zlib-compressed, deduplicated
* **recursive tree objects** -- proper nested directory tracking
* **interactive REPL** -- `oxi` launches a shell with tab completion, live status bar, command history
* **secret scanning** -- detects 21 types of API keys, tokens, and credentials before commit
* **structured data merge** -- JSON/YAML/TOML merge at the key level, not text lines
* **notebook-aware versioning** -- cell-level diffs for `.ipynb` files, auto-strip outputs
* **AI agent provenance** -- track which agent/tool wrote what code
* **built-in undo** -- every operation is safely reversible
* **semantic diffs (experimental)** -- AST-aware diffs that understand function renames

## docs

* [Getting Started](docs/getting-started.md) -- installation, quick start, basic workflow
* [CLI Reference](docs/cli-reference.md) -- every command, flag, and parameter
* [Configuration](docs/configuration.md) -- config files, environment variables
* [Interactive Shell](docs/repl.md) -- the `oxi` REPL
* [Security Scanning](docs/security.md) -- secret detection patterns and usage
* [Undo System](docs/undo.md) -- reversing operations
* [Semantic Diffs](docs/semantic-diffs.md) -- AST-aware diffs
* [Notebook Support](docs/notebook-support.md) -- Jupyter notebook versioning
* [Structured Merge](docs/merge.md) -- key-level data merging
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
* a pointer to the previous commit

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
  core/          repo context refs config
  diff/          myers diff engine
  merge/         structured data merge (json/yaml/toml)
  notebook/      ipynb cell-level support
  semantic/      ast-aware diffs via tree-sitter
  security/      secret scanning
  provenance/    ai agent tracking
  undo/          operation journal and reversal
  cli/           click commands and prompt_toolkit repl
```

## contributing

see [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)

## license

MIT

~ written by a guy who discovered hashing yesterday
