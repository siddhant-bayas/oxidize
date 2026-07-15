# notebook support

oxidize treats Jupyter notebooks (`.ipynb` files) as structured documents, not plain text. this enables cell-level diffs and automatic output stripping.

## requirements

install the notebook extras:

```bash
pip install "pyoxidize[notebook]"
```

this installs `nbformat>=5.9`.

## features

| feature | description |
|---------|-------------|
| cell-level diffing | compare notebooks cell by cell, not line by line |
| output stripping | remove cell outputs and execution counts before diffing |
| text-level diff | fall back to concatenating all cell sources for line diffs |

## usage

### cell-level diff

```python
from pathlib import Path
from oxidize.notebook.differ import NotebookDiffer

changes = NotebookDiffer.diff_cells(
    Path("old_version.ipynb"),
    Path("new_version.ipynb")
)

for change in changes:
    print(change)
```

each change is a dict with:
- `type` -- one of: `added`, `deleted`, `modified`, `unchanged`
- `old_cell` -- the old cell data (if applicable)
- `new_cell` -- the new cell data (if applicable)
- `summary` -- text summary of what changed

### text-level diff

```python
from pathlib import Path
from oxidize.notebook.differ import NotebookDiffer

diff = NotebookDiffer.diff_text(
    Path("old_version.ipynb"),
    Path("new_version.ipynb")
)

for line in diff:
    print(line)
```

this concatenates all cell sources and runs a standard Myers diff.

### strip outputs

```python
import json
from oxidize.notebook.differ import strip_outputs

with open("notebook.ipynb") as f:
    nb = json.load(f)

clean_nb = strip_outputs(nb)

with open("notebook_clean.ipynb", "w") as f:
    json.dump(clean_nb, f, indent=1)
```

`strip_outputs()` returns a copy of the notebook data with:
- all code cell outputs cleared (`outputs = []`)
- execution counts set to `None`

this is useful for diffing -- outputs are noisy and change every time you run a cell.

### reading notebooks

```python
from pathlib import Path
from oxidize.notebook.differ import NotebookReader

reader = NotebookReader(Path("notebook.ipynb"))

# get all cell sources
for i, source in enumerate(reader.cell_sources()):
    print(f"Cell {i}: {source[:50]}...")

# get metadata
print(reader.metadata)
```

### NotebookReader

| property | type | description |
|----------|------|-------------|
| `cells` | `list` | raw cell objects from the notebook |
| `metadata` | `dict` | notebook metadata |

| method | signature | description |
|--------|-----------|-------------|
| `cell_sources` | `cell_sources() -> list[str]` | source text of each cell |
| `source_text` | `source_text(cell) -> str` | extract source from a cell (handles both list-of-strings and string formats) |

## how notebook diffs work

`.ipynb` files are JSON. each notebook contains:

```json
{
  "cells": [
    {
      "cell_type": "code",
      "source": ["print('hello')\n", "print('world')"],
      "outputs": [{"text": ["hello\n", "world\n"]}],
      "execution_count": 5
    }
  ],
  "metadata": {...},
  "nbformat": 4,
  "nbformat_minor": 5
}
```

oxidize's notebook differ:

1. reads and parses the JSON
2. extracts cell sources (handles both `["line1\n", "line2"]` and `"line1\nline2"` formats)
3. compares cells by content
4. reports added, deleted, modified, and unchanged cells

## example output

```
cell-level diff between old.ipynb and new.ipynb:

added cell 2:
    import pandas as pd
    df = pd.read_csv("data.csv")

modified cell 4:
    old: plt.plot(x, y)
    new: plt.plot(x, y, label="data")

deleted cell 6:
    # old unused cell
```
