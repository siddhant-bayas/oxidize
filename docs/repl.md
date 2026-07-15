# interactive shell (REPL)

running `oxi` with no arguments launches an interactive shell powered by prompt_toolkit.

## launching

```bash
# launch the REPL
oxi

# or with arguments, it delegates to the CLI
oxi status
oxi commit -m "msg"
```

## REPL features

| feature | description |
|---------|-------------|
| tab completion | complete commands and file paths |
| status bar | live display of branch, staged count, HEAD oid |
| command history | persisted to `~/.oxidize_history` |
| aliases | shorthand commands for common operations |
| help | built-in help command |

## prompt

```
oxi>
```

## aliases

| alias | expands to | description |
|-------|-----------|-------------|
| `s` | `status` | show working tree status |
| `c` | `commit` | create a commit |
| `a` | `add` | stage files |
| `l` | `log` | show commit history |
| `d` | `diff` | show differences |
| `q` | `exit` | quit the REPL |

**usage:**
```
oxi> s
# equivalent to: oxidize status

oxi> a main.py
# equivalent to: oxidize add main.py

oxi> c -m "my commit"
# equivalent to: oxidize commit -m "my commit"
```

## available commands

all standard CLI commands are available:

```
init        create a new repository
add         stage files
status      show working tree status
commit      create a commit
log         show commit history
diff        show differences
scan        scan for secrets
undo        reverse operations
help        show help
exit        quit the REPL
quit        quit the REPL
```

## tab completion

the REPL provides contextual tab completion:

- **commands** -- all available command names
- **file paths** -- file and directory names relative to the working tree
- **flags** -- command-specific flags (e.g. `--cached` for diff)

type a partial word and press `Tab` to complete.

## status bar

the bottom toolbar displays live information:

```
branch: main | staged: 3 | head: a1b2c3d
```

| field | description |
|-------|-------------|
| `branch` | current branch name |
| `staged` | number of files in the staging index |
| `head` | short oid of HEAD commit (or `none`) |

## history

commands are persisted to `~/.oxidize_history` (one command per line). use the up/down arrow keys to navigate history across sessions.

## exiting

```
oxi> exit
# or
oxi> quit
# or press Ctrl-D
```
