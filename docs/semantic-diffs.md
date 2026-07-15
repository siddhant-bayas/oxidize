# semantic diffs (experimental)

semantic diffs understand your code's structure. instead of comparing text line-by-line, they parse your source code into an AST and compare functions, classes, and methods.

## requirements

install the semantic extras:

```bash
pip install "pyoxidize[semantic]"
```

this installs `py-tree-sitter` and `tree-sitter-python`.

## how it works

1. **extract entities** -- parse Python source code to identify functions, classes, and methods
2. **compute structural hashes** -- hash each entity's body to detect changes
3. **compare** -- match entities by name and structural hash
4. **detect renames** -- if two entities have the same body hash but different names, it's a rename

## entity types

| type | description |
|------|-------------|
| `function` | top-level `def` statements |
| `class` | top-level `class` statements |
| `method` | `def` statements indented inside a class |
| `assignment` | detected but not yet fully tracked |

## usage

### from Python

```python
from oxidize.semantic.differ import semantic_diff, format_semantic_diff

old_source = """
def greet():
    return "hello"

class Calculator:
    def add(self, a, b):
        return a + b
"""

new_source = """
def greet_user():
    return "hello world"

class Calculator:
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b
"""

changes = semantic_diff(old_source, new_source)
print(format_semantic_diff(changes))
```

**output:**
```
> renamed function greet -> greet_user
+ added method Calculator.subtract
~ modified class Calculator (body changed)
```

### change types

| icon | type | meaning |
|------|------|---------|
| `+` | added | new entity appeared |
| `-` | deleted | entity was removed |
| `~` | modified | entity body changed |
| `>` | renamed | same body, different name |

## rename detection

rename detection works by comparing structural hashes. if two entities have:

- **different names** but
- **identical body hashes**

then the differ considers it a rename rather than a delete + add.

this is useful for tracking refactors like:

```python
# old
def process_data(data):
    return transform(data)

# new  
def transform_data(data):    # renamed
    return transform(data)    # body unchanged
```

the semantic diff will report: `> renamed function process_data -> transform_data`

## using the entity API directly

```python
from oxidize.semantic.entities import extract_entities, EntitySnapshot

source = """
def foo():
    pass

class Bar:
    def baz(self):
        pass
"""

entities = extract_entities(source)
snapshot = EntitySnapshot(entities)

# lookup by name
foo = snapshot.by_name()["foo"]

# lookup by structural hash (find all entities with same body)
by_hash = snapshot.by_hash()
```

### Entity properties

| field | type | description |
|-------|------|-------------|
| `name` | `str` | function/class/method name |
| `entity_type` | `EntityType` | function, class, method, or assignment |
| `start_line` | `int` | first line number (1-indexed) |
| `end_line` | `int` | last line number |
| `body_hash` | `str` | SHA-256 of body (truncated to 16 hex chars) |
| `source` | `str` | full source text of the entity |

## limitations

- currently only supports Python source files
- uses regex-based extraction (not full AST parsing) for the entity extraction
- tree-sitter integration is available via the `semantic` extras for more robust parsing
- does not track imports, decorators, or module-level variables
- assignment detection is present but not fully integrated into the diff
