# python api reference

oxidize can be used as a Python library. below is the complete API for every public module, class, function, and type.

## package: oxidize

```python
import oxidize
oxidize.__version__  # "0.2.0"
```

---

## oxidize.objects.types

core object types, hashing, and serialization.

### ObjectType

```python
class ObjectType(str, Enum):
    BLOB = "blob"
    TREE = "tree"
    COMMIT = "commit"
```

enum for the three object types in the store.

### hash_object

```python
def hash_object(type: ObjectType, data: bytes) -> str
```

computes the SHA-256 hash of an object.

**hash formula:** `sha256("{type.value} {len(data)}\x00" + data)`

**returns:** 64-character hex digest string.

**example:**
```python
from oxidize.objects.types import ObjectType, hash_object
oid = hash_object(ObjectType.BLOB, b"hello world")
# oid = "a948904f2f0f479b8f8564e9d7e22c28..."
```

### Blob

```python
@dataclass(frozen=True)
class Blob:
    data: bytes
    oid: str  # auto-computed, not in __init__
```

represents a file's raw content.

| method | signature | description |
|--------|-----------|-------------|
| `serialize` | `serialize() -> bytes` | returns `self.data` |
| `deserialize` | `deserialize(cls, data: bytes) -> Blob` | classmethod, creates Blob from raw bytes |

**example:**
```python
from oxidize.objects.types import Blob
blob = Blob(b"hello world")
print(blob.oid)  # "a948904f2f0f479b8f8564e9d7e22c28..."
print(blob.data)  # b"hello world"

# roundtrip
raw = blob.serialize()
blob2 = Blob.deserialize(raw)
assert blob.oid == blob2.oid
```

### FileMode

```python
class FileMode(str, Enum):
    REGULAR = "100644"
    EXECUTABLE = "100755"
    DIRECTORY = "040000"
```

| classmethod | signature | description |
|-------------|-----------|-------------|
| `from_stat` | `from_stat(cls, st_mode: int) -> FileMode` | converts OS stat mode to FileMode |

**example:**
```python
from oxidize.objects.types import FileMode
import os
mode = FileMode.from_stat(os.stat("script.py").st_mode)
# FileMode.REGULAR or FileMode.EXECUTABLE
```

### TreeEntry

```python
@dataclass(frozen=True)
class TreeEntry:
    name: str
    oid: str
    mode: FileMode
```

a single entry in a tree object (a file or subdirectory reference).

### Tree

```python
@dataclass
class Tree:
    entries: list[TreeEntry]  # default: []
    oid: str                  # auto-computed
```

a directory snapshot containing named entries.

| method | signature | description |
|--------|-----------|-------------|
| `add` | `add(entry: TreeEntry) -> None` | appends entry, sorts by name, recomputes oid |
| `serialize` | `serialize() -> bytes` | binary format: `"{mode} {name}\0{oid_bytes}"` per entry |
| `deserialize` | `deserialize(cls, data: bytes) -> Tree` | classmethod, parses binary format |
| `__iter__` | `__iter__() -> Iterator[TreeEntry]` | iterate over entries |

entries are always sorted by name after `add()`.

**example:**
```python
from oxidize.objects.types import Tree, TreeEntry, FileMode
tree = Tree()
tree.add(TreeEntry("main.py", "abc123...", FileMode.REGULAR))
tree.add(TreeEntry("utils.py", "def456...", FileMode.REGULAR))
print(tree.oid)  # auto-computed hash
for entry in tree:
    print(entry.name, entry.oid)
```

### Author

```python
@dataclass
class Author:
    name: str
    email: str
    timestamp: int   # default: int(time.time())
    tz_offset: str   # default: "+0000"
```

| method | signature | description |
|--------|-----------|-------------|
| `__str__` | `__str__() -> str` | formats as `"Name <email> timestamp tz_offset"` |
| `from_str` | `from_str(cls, s: str) -> Author` | classmethod, parses that format back |

**example:**
```python
from oxidize.objects.types import Author
author = Author("Jane", "jane@example.com")
print(str(author))  # "Jane <jane@example.com> 1697000000 +0000"
author2 = Author.from_str(str(author))
```

### Commit

```python
@dataclass
class Commit:
    tree_oid: str
    author: Author
    committer: Author
    message: str
    parents: list[str]    # default: []
    agent: str | None     # default: None
    oid: str              # auto-computed
```

| method | signature | description |
|--------|-----------|-------------|
| `serialize` | `serialize() -> bytes` | text format: `tree <oid>\nparent <oid>\nauthor ...\n\nmessage` |
| `deserialize` | `deserialize(cls, data: bytes) -> Commit` | classmethod, parses text format |

**serialized format example:**
```
tree a1b2c3d4...
parent e5f6a7b8...
author Jane <jane@example.com> 1697000000 +0000
committer Jane <jane@example.com> 1697000000 +0000

initial commit
```

---

## oxidize.storage.backend

abstract and concrete storage backends.

### StorageBackend (ABC)

```python
class StorageBackend(ABC):
    @abstractmethod
    def read(self, oid: str) -> tuple[ObjectType, bytes]
    @abstractmethod
    def write(self, type: ObjectType, data: bytes) -> str
    @abstractmethod
    def exists(self, oid: str) -> bool
```

interface for object storage. implement this to create custom backends (database, S3, in-memory, etc.).

| method | signature | description |
|--------|-----------|-------------|
| `read` | `read(oid: str) -> tuple[ObjectType, bytes]` | read object by oid, return type + raw data |
| `write` | `write(type: ObjectType, data: bytes) -> str` | write object, return oid |
| `exists` | `exists(oid: str) -> bool` | check if object exists |

### FilesystemBackend

```python
class FilesystemBackend(StorageBackend):
    def __init__(self, objects_dir: Path)
```

default backend storing objects on the filesystem.

**storage layout:** `objects_dir / oid[:2] / oid[2:]` (git-style split).

objects are zlib-compressed. the on-disk format is `zlib.compress("type len\0" + data)`.

**example:**
```python
from pathlib import Path
from oxidize.storage.backend import FilesystemBackend
from oxidize.objects.types import ObjectType

backend = FilesystemBackend(Path(".oxidize/objects"))
oid = backend.write(ObjectType.BLOB, b"hello")
data = backend.read(oid)  # (ObjectType.BLOB, b"hello")
print(backend.exists(oid))  # True
```

---

## oxidize.storage.database

high-level object database.

### ObjectDatabase

```python
class ObjectDatabase:
    def __init__(self, backend: StorageBackend)
```

| classmethod | signature | description |
|-------------|-----------|-------------|
| `filesystem` | `filesystem(cls, objects_dir: Path) -> ObjectDatabase` | create database backed by filesystem |

| method | signature | description |
|--------|-----------|-------------|
| `store_blob` | `store_blob(data: bytes) -> str` | store blob, return oid |
| `store_tree` | `store_tree(tree: Tree) -> str` | serialize and store tree |
| `store_commit` | `store_commit(commit: Commit) -> str` | serialize and store commit |
| `load_blob` | `load_blob(oid: str) -> Blob` | load blob (raises `TypeError` if wrong type) |
| `load_tree` | `load_tree(oid: str) -> Tree` | load and deserialize tree |
| `load_commit` | `load_commit(oid: str) -> Commit` | load and deserialize commit |
| `exists` | `exists(oid: str) -> bool` | check existence |

**example:**
```python
from pathlib import Path
from oxidize.storage.database import ObjectDatabase

db = ObjectDatabase.filesystem(Path(".oxidize/objects"))
oid = db.store_blob(b"hello world")
blob = db.load_blob(oid)
print(blob.data)  # b"hello world"
```

---

## oxidize.index.staging

staging area (index) management.

### IndexEntry

```python
@dataclass
class IndexEntry:
    path: str
    oid: str
    mode: str
    size: int
    mtime: float
```

| method | signature | description |
|--------|-----------|-------------|
| `is_stale` | `is_stale(disk_path: Path) -> bool` | checks if file changed on disk (mtime + size) |

### Index

```python
class Index:
    def __init__(self, index_path: Path)
```

backed by a JSON file at `index_path`.

| method | signature | description |
|--------|-----------|-------------|
| `add` | `add(path: str, oid: str, disk_path: Path) -> None` | record file with mode/size/mtime |
| `remove` | `remove(path: str) -> None` | remove entry |
| `get` | `get(path: str) -> IndexEntry \| None` | retrieve entry |
| `entries` | `entries() -> list[IndexEntry]` | all entries |
| `clear` | `clear() -> None` | remove all entries |
| `__contains__` | `__contains__(path: str) -> bool` | check if path is staged |
| `__len__` | `__len__() -> int` | number of staged files |

**example:**
```python
from pathlib import Path
from oxidize.index.staging import Index

index = Index(Path(".oxidize/index.json"))
index.add("main.py", "abc123...", Path("main.py"))
print(len(index))        # 1
print("main.py" in index) # True
entry = index.get("main.py")
index.clear()
print(len(index))        # 0
```

---

## oxidize.core.repository

high-level repository interface.

### RepositoryNotFound

```python
class RepositoryNotFound(Exception)
```

raised when no `.oxidize/` directory is found.

### Repository

```python
class Repository:
    def __init__(self, work_tree: Path)
```

| attribute | type | description |
|-----------|------|-------------|
| `work_tree` | `Path` | working tree root |
| `oxidize_dir` | `Path` | `.oxidize/` directory |
| `db` | `ObjectDatabase` | object database |
| `refs` | `RefStore` | reference store |
| `index` | `Index` | staging area |
| `config` | `Config` | configuration |

| classmethod | signature | description |
|-------------|-----------|-------------|
| `init` | `init(cls, path: Path) -> Repository` | create new repository |
| `discover` | `discover(cls, start: Path \| None = None) -> Repository` | find existing repo by walking up |

| method | signature | description |
|--------|-----------|-------------|
| `resolve_ref` | `resolve_ref(ref: str) -> str \| None` | resolve ref name to oid |
| `is_empty` | `is_empty() -> bool` | True if HEAD is None |

**example:**
```python
from pathlib import Path
from oxidize.core.repository import Repository

# create new repo
repo = Repository.init(Path("./my-project"))

# or discover existing
repo = Repository.discover(Path("./my-project/src"))

print(repo.work_tree)
print(repo.resolve_ref("main"))
print(repo.is_empty())  # True (no commits yet)
```

---

## oxidize.core.refs

reference management.

### RefStore

```python
class RefStore:
    def __init__(self, git_dir: Path)  # the .oxidize/ directory
```

| method | signature | description |
|--------|-----------|-------------|
| `read` | `read(name: str) -> str \| None` | read a ref, resolves symbolic refs |
| `write` | `write(name: str, oid: str) -> None` | write a ref file |
| `head` | `head() -> str \| None` | read HEAD (follows symref to return oid) |
| `set_head_branch` | `set_head_branch(branch: str) -> None` | set HEAD to `ref: refs/heads/{branch}` |
| `current_branch` | `current_branch() -> str \| None` | branch name from HEAD, or None if detached |
| `update_head` | `update_head(oid: str) -> None` | update HEAD (follows symref or writes detached) |
| `list_branches` | `list_branches() -> list[str]` | list all branch names |

---

## oxidize.core.config

configuration file management.

### Config

```python
class Config:
    def __init__(self, path: Path)
```

| method | signature | description |
|--------|-----------|-------------|
| `get` | `get(section: str, key: str, fallback: str \| None = None) -> str \| None` | read config value |
| `set` | `set(section: str, key: str, value: str) -> None` | write config value |

| property | type | description |
|----------|------|-------------|
| `user_name` | `str` | `[user] name` or `"Unknown"` |
| `user_email` | `str` | `[user] email` or `"unknown@example.com"` |

---

## oxidize.diff.engine

line-level diff engine.

### LineOp

```python
class LineOp(str, Enum):
    EQUAL = "equal"
    INSERT = "insert"
    DELETE = "delete"
```

### DiffLine

```python
@dataclass(frozen=True)
class DiffLine:
    op: LineOp
    content: str
    old_lineno: int | None
    new_lineno: int | None
```

### diff_lines

```python
def diff_lines(old: str, new: str) -> list[DiffLine]
```

computes a Myers diff between two strings. splits into lines and returns a list of `DiffLine` objects.

**example:**
```python
from oxidize.diff.engine import diff_lines, LineOp
changes = diff_lines("hello\nworld\n", "hello\nthere\nworld\n")
for line in changes:
    if line.op == LineOp.INSERT:
        print(f"+ {line.content}")
    elif line.op == LineOp.DELETE:
        print(f"- {line.content}")
```

---

## oxidize.merge.structured

structured data merging for JSON/YAML/TOML.

### deep_merge

```python
def deep_merge(base: dict, head: dict) -> dict
```

merges `head` into `base` recursively. returns a new dict (does not mutate inputs).

### three_way_merge

```python
def three_way_merge(base: dict, ours: dict, theirs: dict) -> tuple[dict, list[str]]
```

three-way merge at the key level.

**returns:** `(merged_result, list_of_conflict_keys)`

**conflict resolution rules:**
- only one side changed: take that side
- neither changed: keep base
- both changed to same value: no conflict
- both changed differently: conflict (reports key, keeps ours, recurses for nested dicts)
- both added same key with same value: no conflict
- both deleted key: removed

**example:**
```python
from oxidize.merge.structured import three_way_merge

base  = {"db": {"host": "localhost", "port": 5432}, "debug": False}
ours  = {"db": {"host": "localhost", "port": 5433}, "debug": False}
theirs = {"db": {"host": "localhost", "port": 5432}, "debug": True}

merged, conflicts = three_way_merge(base, ours, theirs)
# merged = {"db": {"host": "localhost", "port": 5433}, "debug": True}
# conflicts = [] (port conflict resolved: only ours changed it)
```

---

## oxidize.notebook.differ

Jupyter notebook support.

### NotebookReader

```python
class NotebookReader:
    def __init__(self, path: Path)
```

| property | type | description |
|----------|------|-------------|
| `cells` | `list` | raw cell objects |
| `metadata` | `dict` | notebook metadata |

| method | signature | description |
|--------|-----------|-------------|
| `cell_sources` | `cell_sources() -> list[str]` | source text of each cell |
| `source_text` | `source_text(cell) -> str` | extract source from a cell (handles list and string formats) |

### strip_outputs

```python
def strip_outputs(raw: dict) -> dict
```

returns a copy of notebook data with code cell outputs cleared and execution counts set to `None`.

### NotebookDiffer

| static method | signature | description |
|---------------|-----------|-------------|
| `diff_cells` | `diff_cells(old_path, new_path) -> list[dict]` | cell-level diff (added/deleted/modified/unchanged) |
| `diff_text` | `diff_text(old_path, new_path) -> list[DiffLine]` | text-level diff of concatenated cell sources |

**example:**
```python
from pathlib import Path
from oxidize.notebook.differ import NotebookDiffer, strip_outputs

# cell-level diff
changes = NotebookDiffer.diff_cells(Path("old.ipynb"), Path("new.ipynb"))
for change in changes:
    print(change)

# strip outputs before committing
import json
with open("notebook.ipynb") as f:
    nb = json.load(f)
clean = strip_outputs(nb)
```

---

## oxidize.semantic.entities

AST entity extraction (regex-based).

### EntityType

```python
class EntityType(str, Enum):
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    ASSIGNMENT = "assignment"
```

### Entity

```python
@dataclass(frozen=True)
class Entity:
    name: str
    entity_type: EntityType
    start_line: int
    end_line: int
    body_hash: str
    source: str
```

| method | signature | description |
|--------|-----------|-------------|
| `structural_hash` | `structural_hash() -> str` | SHA-256 of `"{entity_type}:{body_hash}"` |

### extract_entities

```python
def extract_entities(source: str) -> list[Entity]
```

parses Python source code using regex to extract functions, classes, and methods. identifies `def` and `class` statements, extracts their bodies by tracking indentation.

### EntitySnapshot

```python
@dataclass
class EntitySnapshot:
    entities: list[Entity]
```

| method | signature | description |
|--------|-----------|-------------|
| `by_name` | `by_name() -> dict[str, Entity]` | lookup by name |
| `by_hash` | `by_hash() -> dict[str, list[Entity]]` | lookup by structural hash (for rename detection) |

---

## oxidize.semantic.differ

AST-aware semantic diffing.

### SemanticChange

```python
@dataclass(frozen=True)
class SemanticChange:
    change_type: str    # "added", "deleted", "modified", "renamed"
    entity_name: str
    entity_type: EntityType
    detail: str
```

### semantic_diff

```python
def semantic_diff(old_source: str, new_source: str) -> list[SemanticChange]
```

compares two Python source files at the entity level. detects:
- **added** -- new functions/classes
- **deleted** -- removed functions/classes
- **modified** -- body changed
- **renamed** -- same structural hash, different name

### format_semantic_diff

```python
def format_semantic_diff(changes: list[SemanticChange]) -> str
```

formats changes with icons: `+` added, `-` deleted, `~` modified, `>` renamed.

**example:**
```python
from oxidize.semantic.differ import semantic_diff, format_semantic_diff

old = "def greet():\n    return 'hello'\n"
new = "def greet_user():\n    return 'hello'\n"

changes = semantic_diff(old, new)
print(format_semantic_diff(changes))
# > renamed function greet -> greet_user
```

---

## oxidize.security.scanner

secret and credential detection.

### scan_text

```python
def scan_text(text: str, filepath: str = "<input>") -> list[dict]
```

scans a text string for secrets. returns list of `{type, file, line, match}`.

### scan_file

```python
def scan_file(path: Path, root: Path) -> list[dict]
```

reads a file and scans it.

### scan_directory

```python
def scan_directory(root: Path) -> list[dict]
```

recursively scans all files in a directory, ignoring known non-relevant dirs.

**see [security.md](security.md) for the full list of detected patterns.**

---

## oxidize.provenance.agent

AI agent provenance tracking.

### AgentRecord

```python
@dataclass
class AgentRecord:
    agent: str
    timestamp: float
    commit_oid: str
    message: str
    prompt_id: str | None
```

| method | signature | description |
|--------|-----------|-------------|
| `to_dict` | `to_dict() -> dict` | serialize to dict |
| `from_dict` | `from_dict(cls, d: dict) -> AgentRecord` | classmethod, deserialize from dict |

### ProvenanceStore

```python
class ProvenanceStore:
    def __init__(self, path: Path)
```

| method | signature | description |
|--------|-----------|-------------|
| `record` | `record(agent: str, commit_oid: str, message: str, prompt_id: str \| None = None) -> None` | record an agent action |
| `by_agent` | `by_agent(agent: str) -> list[AgentRecord]` | filter records by agent name |
| `all_agents` | `all_agents() -> list[str]` | list all agent names |
| `all_records` | `all_records() -> list[AgentRecord]` | all records |

### detect_agent

```python
def detect_agent() -> str | None
```

checks environment variables to auto-detect the running agent. returns agent name or `None`.

---

## oxidize.undo.journal

operation journal for undo support.

### OpType

```python
class OpType(str, Enum):
    ADD = "add"
    COMMIT = "commit"
    BRANCH_CREATE = "branch_create"
    BRANCH_DELETE = "branch_delete"
    STAGE_CLEAR = "stage_clear"
```

### JournalEntry

```python
@dataclass
class JournalEntry:
    op: str
    timestamp: float
    data: dict[str, Any]
    undo_data: dict[str, Any]
```

### Journal

```python
class Journal:
    def __init__(self, path: Path)
```

| method | signature | description |
|--------|-----------|-------------|
| `record` | `record(op: str, data: dict, undo_data: dict) -> None` | add an entry |
| `last` | `last() -> JournalEntry \| None` | get last entry |
| `pop_last` | `pop_last() -> JournalEntry \| None` | remove and return last entry |
| `entries` | `entries() -> list[JournalEntry]` | all entries |
| `__len__` | `__len__() -> int` | number of entries |

---

## oxidize.undo.reverser

undo manager.

### UndoManager

```python
class UndoManager:
    def __init__(self, repo: Repository)
```

| property | type | description |
|----------|------|-------------|
| `journal` | `Journal` | the operation journal |

**recording methods:**

| method | signature | description |
|--------|-----------|-------------|
| `record_add` | `record_add(paths: list[str], oids: list[str]) -> None` | record an add operation |
| `record_commit` | `record_commit(commit_oid: str, prev_head: str \| None) -> None` | record a commit |
| `record_branch_create` | `record_branch_create(branch: str, oid: str) -> None` | record branch creation |
| `record_branch_delete` | `record_branch_delete(branch: str, oid: str) -> None` | record branch deletion |

**undo method:**

| method | signature | description |
|--------|-----------|-------------|
| `undo` | `undo(count: int = 1) -> list[str]` | pop entries and apply reversal logic, return list of undone operation descriptions |

**undo logic per operation type:**

| operation | reversal |
|-----------|----------|
| `commit` | restores HEAD to `restore_to` OID (or removes HEAD/ref for initial commit) |
| `add` | removes paths from staging index |
| `branch_create` | deletes the branch ref file |
| `branch_delete` | restores the branch ref with its original oid |
