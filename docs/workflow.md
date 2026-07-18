# workflow commands

commands for everyday work that is not directly a commit.

## stash

shelf the current index, work on something else, then re-apply later.

```
oxidize stash                          # save with no message
oxidize stash save "feature-x"         # save with a message
oxidize stash list                     # show all stashes
oxidize stash pop <name|index>         # reapply into the index
```

stashes live in `.oxidize/stashes/` as snapshot dirs. They survive across reboots but are not part of commit history.

## bisect

binary-search your commit history to find a regression.

```
oxidize bisect start
oxidize bisect bad HEAD
oxidize bisect good v1.0
# …walk through candidates…
oxidize bisect reset
```

state persists to `.oxidize/bisect.json`. Pass `bad` and `good` directly to `start` to skip the first round:

```
oxidize bisect start main broken-commit
```

## hooks

shell hooks triggered by oxidize events. Stored under `.oxidize/hooks/<name>` (with any extension oxidize recognises, e.g. `.sh`, `.py`, `.bat`, `.cmd`).

```bash
oxidize hooks list
oxidize hooks install pre-commit      # scaffolds .oxidize/hooks/pre-commit.sh
oxidize hooks run pre-commit          # manual run, exit code echoed back
```

canonical hook names: `pre-commit`, `post-commit`, `pre-add`, `post-add`, `pre-merge`, `post-merge`.

exit code `0` allows the operation to proceed, non-zero blocks it with a printed error.

## tags

lightweight refs that point at immutable commits.

```bash
oxidize tag create v1.0                # tag HEAD
oxidize tag create v1.0 main           # tag a specific ref
oxidize tag list                       # list known tags
oxidize tag list --verify              # check each points to a real object
oxidize tag delete v1.0
```

## show

display a commit header. Useful as a complement to `log`.

```bash
oxidize show                           # HEAD
oxidize show <ref>                     # any branch / tag / commit oid
```

## blame

line-by-line annotation showing which commit last touched each line.

```bash
oxidize blame src/main.py
```

> ℹ semantic rename-aware blame is on the roadmap.

## notebook-diff

rich-rendered cell-by-cell diff for `.ipynb` files.

```bash
oxidize notebook-diff old.ipynb new.ipynb
oxidize notebook-diff v1.ipynb v2.ipynb --render
```
