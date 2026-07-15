# structured data merge

for JSON, YAML, and TOML files, oxidize merges at the key level instead of treating them as text lines. this produces cleaner, more meaningful merges.

## usage

```python
from oxidize.merge.structured import deep_merge, three_way_merge
```

## deep merge

merge two dictionaries recursively:

```python
from oxidize.merge.structured import deep_merge

base = {
    "database": {
        "host": "localhost",
        "port": 5432
    },
    "debug": False
}

head = {
    "database": {
        "port": 5433
    },
    "debug": True
}

result = deep_merge(base, head)
# {
#     "database": {"host": "localhost", "port": 5433},
#     "debug": True
# }
```

`deep_merge(base, head)` merges `head` into `base` recursively. the result is a new dict -- neither input is mutated.

## three-way merge

the real power: merge with conflict detection using a common ancestor:

```python
from oxidize.merge.structured import three_way_merge

base = {
    "database": {"host": "localhost", "port": 5432},
    "debug": False,
    "name": "myapp"
}

ours = {
    "database": {"host": "localhost", "port": 5433},  # we changed port
    "debug": False,
    "name": "myapp"
}

theirs = {
    "database": {"host": "localhost", "port": 5432},  # they didn't change port
    "debug": True,                                      # they changed debug
    "name": "myapp"
}

merged, conflicts = three_way_merge(base, ours, theirs)
# merged = {"database": {"host": "localhost", "port": 5433}, "debug": True, "name": "myapp"}
# conflicts = []  (no conflicts -- only one side changed each key)
```

### return value

`three_way_merge(base, ours, theirs)` returns a tuple:
- `(merged_dict, conflict_keys_list)`

### conflict resolution rules

| scenario | result |
|----------|--------|
| only one side changed a key | take that side's value |
| neither side changed | keep base value |
| both changed to same value | no conflict, take the value |
| both changed differently | **conflict** -- reports the key, keeps `ours` value |
| both added same key with same value | no conflict |
| both deleted a key | key is removed |
| nested dicts with conflict | recursively merges and reports nested conflict keys |

### conflict example

```python
base  = {"setting": "value1"}
ours  = {"setting": "value2"}   # we changed it
theirs = {"setting": "value3"}  # they changed it differently

merged, conflicts = three_way_merge(base, ours, theirs)
# merged = {"setting": "value2"}  (keeps ours)
# conflicts = ["setting"]
```

### nested conflict example

```python
base  = {"db": {"host": "localhost", "port": 5432}}
ours  = {"db": {"host": "localhost", "port": 5433}}
theirs = {"db": {"host": "production", "port": 5432}}

merged, conflicts = three_way_merge(base, ours, theirs)
# merged = {"db": {"host": "production", "port": 5433}}
# conflicts = ["db.host"]  (nested conflict)
```

## when to use structured merge

structured merge is ideal for:

- `settings.json` / `config.json` files
- `pyproject.toml` / `Cargo.toml` / `package.json`
- `.yaml` / `.yml` configuration files
- any structured data where key-level merging makes more sense than line-level

for source code and plain text files, use the standard `oxidize diff` (Myers algorithm) instead.
