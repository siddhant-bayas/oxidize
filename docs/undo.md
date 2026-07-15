# undo system

every mutation in oxidize is recorded to a journal, making operations safely reversible.

## usage

```bash
# undo the last operation
oxidize undo

# same as above
oxidize undo last

# undo multiple operations at once
oxidize undo count 3

# view the full journal
oxidize undo journal
```

## how it works

### the journal

every operation (add, commit, branch create/delete) writes an entry to `.oxidize/journal.json`. each entry contains:

| field | description |
|-------|-------------|
| `op` | operation type (`add`, `commit`, `branch_create`, `branch_delete`) |
| `timestamp` | when the operation occurred |
| `data` | operation-specific data (what was done) |
| `undo` | data needed to reverse the operation |

### what gets recorded

| operation | data recorded | undo data |
|-----------|--------------|-----------|
| `commit` | commit oid, message | previous HEAD oid (to restore to) |
| `add` | file paths, their oids | paths to remove from index |
| `branch_create` | branch name, oid | branch name and oid (to delete) |
| `branch_delete` | branch name, oid | branch name and oid (to restore) |

### undo logic

when you run `oxidize undo`, it pops the most recent journal entry and reverses it:

| operation undone | what happens |
|-----------------|-------------|
| `commit` | HEAD is restored to the previous commit's oid. if it was the initial commit, HEAD and the branch ref are removed. |
| `add` | the specified files are removed from the staging index |
| `branch_create` | the branch ref file is deleted |
| `branch_delete` | the branch ref file is restored with its original oid |

## examples

### undo a commit

```bash
oxidize init
echo "hello" > hello.py
oxidize add hello.py
oxidize commit -m "add hello"

oxidize log
# shows one commit

oxidize undo
# undone: commit abc123

oxidize log
# no commits (head is gone)
```

### undo multiple operations

```bash
# make several commits
oxidize commit -m "first"
oxidize commit -m "second"
oxidize commit -m "third"

# undo last 2
oxidize undo count 2
# undone: commit third
# undone: commit second

oxidize log
# only shows "first"
```

### undo an add

```bash
oxidize add main.py utils.py
oxidize status
# staged: main.py, utils.py

oxidize undo
# undone: add

oxidize status
# nothing staged
```

### view the journal

```bash
oxidize undo journal
# shows all recorded operations with timestamps
```

## using programmatically

```python
from pathlib import Path
from oxidize.core.repository import Repository
from oxidize.undo.reverser import UndoManager

repo = Repository.discover(Path("."))
undo_mgr = UndoManager(repo)

# record operations
undo_mgr.record_commit("new_commit_oid", "previous_head_oid")
undo_mgr.record_add(["file.py"], ["file_oid"])

# undo
results = undo_mgr.undo(count=1)
print(results)  # ["undone: commit new_commit_oid"]
```

## limitations

- undo only reverses the specific operation types listed above
- if you modify files on disk after staging, undo won't revert disk changes (it only affects the index and refs)
- the journal grows over time -- there is no built-in compaction
