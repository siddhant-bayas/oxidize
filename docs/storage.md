# object storage internals

oxidize uses a content-addressable object store, similar to git's but using SHA-256.

## object types

| type | stores | content |
|------|--------|---------|
| `blob` | file content | raw bytes of a file |
| `tree` | directory snapshot | list of entries (name, oid, mode) |
| `commit` | snapshot + metadata | tree oid, parent(s), author, message, agent |

## object IDs (oids)

every object is identified by a SHA-256 hash computed as:

```
oid = sha256("type len\0" + data)
```

where:
- `type` is `blob`, `tree`, or `commit`
- `len` is the byte length of the data
- `\0` is a null byte
- `data` is the serialized object content

this means **identical content always produces the same oid** regardless of filename or location.

## on-disk format

objects are stored at:

```
.oxidize/objects/<first-2-hex-chars>/<remaining-hex-chars>
```

for example, oid `a1b2c3d4e5f6...` becomes:

```
.oxidize/objects/a1/b2c3d4e5f6...
```

each file contains zlib-compressed data:

```
zlib.compress("type len\0" + data)
```

## object formats

### blob

the simplest object. `serialize()` returns the raw file bytes.

```
data = file_content
```

### tree

a directory listing. serialized as a sequence of entries:

```
{mode} {name}\0{oid_hex_bytes}
```

for each entry, where:
- `mode` is `100644` (regular), `100755` (executable), or `040000` (directory)
- `name` is the filename
- `\0` is a null byte separator
- `oid_hex_bytes` is the 64-character oid as raw bytes

entries are sorted by name.

### commit

a text-based format:

```
tree {tree_oid}
parent {parent_oid}
agent {agent_name}
author {Author string}
committer {Author string}

{commit message}
```

- `tree` line references the tree object oid
- `parent` lines reference parent commit oids (0 for initial commit, 1 for normal, 2+ for merges)
- `agent` line is optional (only present if `--agent` was used)
- `author` and `committer` use the format: `Name <email> timestamp tz_offset`
- blank line separates header from message

## storage backend

the default `FilesystemBackend` stores objects on disk. but `StorageBackend` is abstract -- you can implement custom backends:

```python
from oxidize.storage.backend import StorageBackend
from oxidize.objects.types import ObjectType

class InMemoryBackend(StorageBackend):
    def __init__(self):
        self._store = {}
    
    def read(self, oid):
        return self._store[oid]
    
    def write(self, type, data):
        from oxidize.objects.types import hash_object
        oid = hash_object(type, data)
        self._store[oid] = (type, data)
        return oid
    
    def exists(self, oid):
        return oid in self._store
```

## deduplication

because objects are content-addressed, identical content is stored only once. if you add two files with the same content, they share the same blob object.

```bash
echo "hello" > a.txt
echo "hello" > b.txt
oxidize add a.txt b.txt
# only one blob is created in the object store
# both index entries point to the same oid
```

## dependency order

the modules are layered with a strict dependency order (no circular imports):

```
objects -> storage -> index -> core -> cli
```

- **objects** -- types, hashing, serialization (no dependencies on other oxidize modules)
- **storage** -- backends and database (depends on objects)
- **index** -- staging area (depends on storage)
- **core** -- repository, refs, config (depends on storage and index)
- **cli** -- commands and REPL (depends on core and everything below)
