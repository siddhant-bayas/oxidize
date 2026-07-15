from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from oxidize.diff.engine import DiffLine, LineOp, diff_lines


class NotebookReader:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        self._cells: list[dict[str, Any]] = list(self._raw.get("cells", []))

    @property
    def cells(self) -> list[dict[str, Any]]:
        return self._cells

    @property
    def metadata(self) -> dict[str, Any]:
        m = self._raw.get("metadata", {})
        return dict(m) if isinstance(m, dict) else {}

    def cell_sources(self) -> list[str]:
        return [str(c.get("source", "")) for c in self._cells]

    def source_text(self, cell: dict[str, object]) -> str:
        src = cell.get("source", [])
        if isinstance(src, list):
            return "".join(str(s) for s in src)
        return str(src)


def strip_outputs(raw: dict[str, Any]) -> dict[str, Any]:
    result = dict(raw)
    cells: list[dict[str, Any]] = []
    for cell in result.get("cells", []):
        if not isinstance(cell, dict):
            continue
        c: dict[str, Any] = dict(cell)
        if c.get("cell_type") == "code":
            c["outputs"] = []
            c["execution_count"] = None
        cells.append(c)
    result["cells"] = cells
    return result


class NotebookDiffer:
    @staticmethod
    def diff_cells(old_path: Path, new_path: Path) -> list[dict[str, str | int]]:
        old_nb = NotebookReader(old_path)
        new_nb = NotebookReader(new_path)
        old_sources = old_nb.cell_sources()
        new_sources = new_nb.cell_sources()

        results: list[dict[str, str | int]] = []
        max_len = max(len(old_sources), len(new_sources))

        for i in range(max_len):
            old_text = old_sources[i] if i < len(old_sources) else None
            new_text = new_sources[i] if i < len(new_sources) else None

            if old_text is None:
                results.append(
                    {"cell": i + 1, "type": "added", "summary": _summarize(new_text or "")}
                )
            elif new_text is None:
                results.append({"cell": i + 1, "type": "deleted", "summary": _summarize(old_text)})
            elif old_text != new_text:
                results.append(
                    {
                        "cell": i + 1,
                        "type": "modified",
                        "summary": _summarize_diff(old_text, new_text),
                    }
                )
            else:
                results.append({"cell": i + 1, "type": "unchanged"})
        return results

    @staticmethod
    def diff_text(old_path: Path, new_path: Path) -> list[DiffLine]:
        old_nb = NotebookReader(old_path)
        new_nb = NotebookReader(new_path)
        old_text = "\n".join(old_nb.source_text(c) for c in old_nb.cells)
        new_text = "\n".join(new_nb.source_text(c) for c in new_nb.cells)
        return diff_lines(old_text, new_text)


def _summarize(text: str) -> str:
    first_line = text.strip().split("\n")[0][:60]
    return first_line or "(empty)"


def _summarize_diff(old: str, new: str) -> str:
    d = diff_lines(old, new)
    changes = sum(1 for dl in d if dl.op != LineOp.EQUAL)
    return f"{changes} line(s) changed"
