# oxidize

a version control system built from scratch with semantic awareness built-in undo and an interactive shell

[![ci](https://github.com/siddhant-bayas/oxidize/actions/workflows/ci.yml/badge.svg)](https://github.com/siddhant-bayas/oxidize/actions/workflows/ci.yml)
[![pypi](https://img.shields.io/pypi/v/pyoxidize)](https://pypi.org/project/pyoxidize/)
[![python](https://img.shields.io/pypi/pyversions/pyoxidize)](https://pypi.org/project/pyoxidize/)

## what it does

tracks file snapshots using content-addressable storage (sha-256) a commit dag and a staging index but unlike git it also understands your codes structure

```bash
# install
pip install pyoxidize

# or with extras
pip install "pyoxidize[semantic]"
pip install "pyoxidize[notebook]"
pip install "pyoxidize[dev]"

# usage
oxidize init
oxidize add file.py
oxidize status
oxidize commit -m "first commit"
oxidize log

# or use oxi as a shorter alias for everything
oxi init
oxi add file.py
oxi status
oxi commit -m "first commit"
oxi log

# interactive shell (no args launches the repl)
oxi
```

both `oxidize` and `oxi` accept the same subcommands

## features

* content-addressable object store -- sha-256 zlib-compressed deduplicated
* recursive tree objects -- proper nested directory tracking
* interactive repl -- oxi launches a shell with tab completion live status bar command history
* secret scanning -- detects api keys tokens and credentials before commit
* structured data merge -- json/yaml/toml merge at the key level not text lines
* notebook-aware versioning -- cell-level diffs for ipynb files auto-strip outputs
* ai agent provenance -- track which agent/tool wrote what code
* built-in undo -- every operation is safely reversible
* semantic diffs (experimental) -- ast-aware diffs that understand function renames

## how it works

every file you add gets hashed using sha-256 and stored as a blob inside .oxidize/objects/

a commit is just

* a snapshot of the file tree (with proper subtrees for nested dirs)
* metadata (author timestamp agent provenance)
* a pointer to the previous commit

```txt
files -> blobs -> tree -> commit -> commit -> commit
                                     ^
                                    head
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

see [docs/contributing.md](docs/contributing.md)

## license

mit

~ written by a guy who discovered hashing yesterday
