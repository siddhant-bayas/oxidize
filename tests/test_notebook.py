from __future__ import annotations

import json
import tempfile
from pathlib import Path

from oxidize.notebook.differ import NotebookDiffer, NotebookReader, strip_outputs


def _make_notebook(cells: list[dict]) -> dict:
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {"kernelspec": {"display_name": "Python 3"}},
        "cells": cells,
    }


def _make_code_cell(source: str) -> dict:
    return {
        "cell_type": "code",
        "metadata": {},
        "source": source,
        "execution_count": 5,
        "outputs": [{"output_type": "stream", "name": "stdout", "text": "hello"}],
    }


def _make_md_cell(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source,
    }


def test_notebook_reader() -> None:
    nb = _make_notebook(
        [
            _make_md_cell("# Title"),
            _make_code_cell("print('hello')"),
        ]
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ipynb", delete=False) as f:
        json.dump(nb, f)
        f.flush()
        reader = NotebookReader(Path(f.name))
        assert len(reader.cells) == 2
        assert reader.cells[0]["cell_type"] == "markdown"
        assert reader.cells[1]["cell_type"] == "code"


def test_strip_outputs() -> None:
    nb = _make_notebook([_make_code_cell("x = 1")])
    stripped = strip_outputs(nb)
    cell = stripped["cells"][0]
    assert cell["outputs"] == []
    assert cell["execution_count"] is None


def test_diff_cells_added() -> None:
    old_nb = _make_notebook([])
    new_nb = _make_notebook([_make_code_cell("x = 1")])

    with tempfile.NamedTemporaryFile(mode="w", suffix=".ipynb", delete=False) as f1:
        json.dump(old_nb, f1)
        old_path = Path(f1.name)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ipynb", delete=False) as f2:
        json.dump(new_nb, f2)
        new_path = Path(f2.name)

    diffs = NotebookDiffer.diff_cells(old_path, new_path)
    assert len(diffs) == 1
    assert diffs[0]["type"] == "added"


def test_diff_cells_modified() -> None:
    old_nb = _make_notebook([_make_code_cell("x = 1")])
    new_nb = _make_notebook([_make_code_cell("x = 2")])

    with tempfile.NamedTemporaryFile(mode="w", suffix=".ipynb", delete=False) as f1:
        json.dump(old_nb, f1)
        old_path = Path(f1.name)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ipynb", delete=False) as f2:
        json.dump(new_nb, f2)
        new_path = Path(f2.name)

    diffs = NotebookDiffer.diff_cells(old_path, new_path)
    assert len(diffs) == 1
    assert diffs[0]["type"] == "modified"


def test_diff_cells_deleted() -> None:
    old_nb = _make_notebook([_make_code_cell("x = 1")])
    new_nb = _make_notebook([])

    with tempfile.NamedTemporaryFile(mode="w", suffix=".ipynb", delete=False) as f1:
        json.dump(old_nb, f1)
        old_path = Path(f1.name)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ipynb", delete=False) as f2:
        json.dump(new_nb, f2)
        new_path = Path(f2.name)

    diffs = NotebookDiffer.diff_cells(old_path, new_path)
    assert len(diffs) == 1
    assert diffs[0]["type"] == "deleted"
