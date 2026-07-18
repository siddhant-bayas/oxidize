# branching & merging

oxidize supports lightweight branches and three-way text merges.

## branches

```
oxidize branch                          # list local branches
oxidize branch create <name>            # create from HEAD
oxidize branch create <name> HEAD~3     # create from a specific commit
oxidize branch delete <name>            # delete (cannot delete HEAD)
```

## checkout

```
oxidize checkout <branch>               # switch branches
oxidize checkout -b <new-branch>        # create + switch in one step
oxidize checkout <commit-oid>           # detach onto a commit
oxidize checkout -f <branch>            # discard local changes
```

`checkout` rewrites the working tree with the contents of the target's tree. stashes are your friend when you need to keep local work.

## merges

```
oxidize merge <branch>                  # merge into current branch
oxidize merge <branch> --no-commit      # leave conflicts in working tree
```

resolution order:
1. compute the merge base (lowest common ancestor of HEAD and `<branch>`)
2. for each path present in any of {base, ours, theirs}, run a 3-way text merge
3. files with no conflict are auto-written
4. conflicted files are stamped with markers and the command exits non-zero
5. run `oxidize resolve <files>` (or edit directly), then `oxidize add` and `oxidize commit`

### conflict markers

files with conflicts embed the diff in standard format:

```
<<<<<<< OURS
your version of the file
||||||| BASE
the common ancestor
======= THEIRS
their version of the file
>>>>>>> THEIRS
```

`oxidize resolve --all` walks the working tree and offers to take ours/theirs interactively for each conflicted file. `--ours` / `--theirs` apply recursively without prompting.

## merge vs structured data

for json/yaml/toml/inipath files, the structured merger (`oxidize.merge.structured.three_way_merge`) handles key-level merging when both sides edit disjoint keys. The text merger is used as a fallback for non-data files or when structural merging fails -- see `oxidize.merge.structured` for the API.

## undo

every branch create / branch delete / commit / add is journaled. `oxidize undo` reverses the last operation; `oxidize undo --list` shows the full history (see [undo.md](undo.md)).
