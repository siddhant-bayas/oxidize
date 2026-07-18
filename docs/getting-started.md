# getting started

## requirements

- python >= 3.11
- pip (or any pip-compatible package manager)

## installation

```bash
# basic install
pip install pyoxidize

# with optional features
pip install "pyoxidize[semantic]"   # ast-aware semantic diffs (requires tree-sitter)
pip install "pyoxidize[notebook]"   # jupyter notebook cell-level support
pip install "pyoxidize[dev]"        # development tools (pytest, mypy, ruff)

# install everything
pip install "pyoxidize[semantic,notebook,dev]"
```

### optional dependency details

| extra | packages installed | purpose |
|-------|-------------------|---------|
| `semantic` | `tree-sitter>=0.21`, `tree-sitter-python>=0.21` | AST parsing for semantic diffs that understand renames |
| `notebook` | `nbformat>=5.9` | Parse and diff `.ipynb` files at the cell level |
| `dev` | `pytest>=7.4`, `pytest-cov>=4.1`, `mypy>=1.5`, `ruff>=0.1` | linting, type checking, testing |

## quick start

```bash
# 1. create a repository
oxidize init

# 2. add some files
oxidize add main.py README.md

# 3. check what's staged
oxidize status

# 4. commit
oxidize commit -m "initial commit"

# 5. view history
oxidize log
```

## two entry points

oxidize provides two CLI commands that accept the same subcommands:

| command | what it does |
|---------|-------------|
| `oxidize` | standard CLI (click-based) |
| `oxi` | same CLI, but running it with no arguments launches an interactive shell |

```bash
# these are equivalent
oxidize status
oxi status

# but oxi alone launches the interactive REPL
oxi
```

## basic workflow

1. **init** -- create a `.oxidize/` directory in your project
2. **add** -- stage files (reads content, stores blobs, records in index)
3. **status** -- see what's staged, modified, or untracked
4. **commit** -- snapshot staged files into a commit
5. **log** -- walk the commit history
6. **diff** -- see what changed
7. **scan** -- check for secrets before committing
8. **undo** -- reverse any operation if something went wrong

## example session

```bash
# initialize
oxidize init

# create some files
echo "print('hello')" > hello.py
echo "# My Project" > README.md

# stage them
oxidize add hello.py README.md

# see status
oxidize status
# outputs:
# branch: main
# staged:
#   hello.py
#   README.md

# commit
oxidize commit -m "add hello world project"

# make a change
echo "print('hello world')" > hello.py

# check diff
oxidize diff
# shows the change from 'hello' to 'hello world'

# stage and commit the change
oxidize add hello.py
oxidize commit -m "greet the world"

# view log
oxidize log
# shows both commits

# oops, undo the last commit
oxidize undo
```

## what gets stored

when you run `oxidize add`, your files are:

1. read from disk
2. hashed with SHA-256 to produce an object ID (oid)
3. compressed with zlib
4. stored at `.oxidize/objects/xx/yyyyyy...` (first 2 hex chars as directory)
5. recorded in `.oxidize/index.json` (the staging area)

identical file content always produces the same oid regardless of filename or location.

## where things live

```
your-project/
  .oxidize/              # the repository data
    HEAD                 # current branch pointer
    config               # user settings (name, email)
    index.json           # staging area
    journal.json         # undo journal
    objects/             # all stored objects (blobs, trees, commits)
      xx/
        yyyyyy...
    refs/
      heads/
        main             # branch references
      tags/
  your-files...          # working tree (normal files)
```

## next steps

- [CLI Reference](cli-reference.md) -- every command and flag documented
- [Configuration](configuration.md) -- environment variables and config options
- [Architecture](architecture.md) -- how oxidize works under the hood
- [Interactive Shell](repl.md) -- the `oxi` REPL
- [Security Scanning](security.md) -- secret detection
- [Undo System](undo.md) -- reversing operations
