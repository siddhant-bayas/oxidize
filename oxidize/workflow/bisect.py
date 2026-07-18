from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from oxidize.core.repository import Repository


class BisectState:
    FILE = "bisect.json"

    def __init__(self, path: Path) -> None:
        self._path = path
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self._path.is_file():
            self._data = json.loads(self._path.read_text())

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2))

    def reset(self) -> None:
        self._data = {}
        self.save()

    def start(self, good: str, bad: str) -> None:
        self._data = {
            "good": good,
            "bad": bad,
            "candidates": [__import__("oxidize.workflow.bisect", fromlist=["midpoint"]).midpoint],
        }
        self.save()

    def mark(self, state: str, current: str) -> dict[str, Any]:
        history: list[dict[str, str]] = self._data.setdefault("history", [])
        if state not in ("good", "bad"):
            raise ValueError(state)
        history.append({"commit": current, "mark": state})
        cands = list(self._data.setdefault("candidates", []))
        cands = [c for c in cands if c != current]
        if not cands:
            return {"found": current, "done": True}
        next_c = cands[0]
        self._data["candidates"] = cands
        self.save()
        return {"next": next_c, "done": False}

    def status(self) -> dict[str, Any]:
        return dict(self._data)


def walk(repo: Repository, oid: str, depth: int = 0, max_depth: int = 8) -> list[str]:
    return _list_commits(repo, oid, set(), depth, max_depth)


def _list_commits(repo: Repository, oid: str, seen: set[str], depth: int, max_depth: int) -> list[str]:
    if depth > max_depth or oid in seen:
        return []
    seen.add(oid)
    out = [oid]
    try:
        commit = repo.db.load_commit(oid)
    except Exception:
        return out
    for parent_oid in commit.parents:
        out.extend(_list_commits(repo, parent_oid, seen, depth + 1, max_depth))
    return out


def midpoint(repo: Repository, good: str, bad: str) -> str:
    """
    walks the DAG from bad toward good, returns the commit roughly halfway along
    (longest-path / 2 commits back from bad).
    """
    history = walk(repo, bad)
    reverse = list(reversed(history))
    g_positions = [i for i, h in enumerate(reverse) if h == good]
    if not g_positions:
        return bad
    g = g_positions[0]
    halfway = (g + len(reverse) - 1) // 2
    return reverse[halfway if halfway < len(reverse) else len(reverse) - 1]


def _repo_for(state: "BisectState") -> Repository:
    """stub: bisect module doesn't hold a repo handle; callers should pass one explicitly."""
    raise RuntimeError("bisect requires a Repository; pass it explicitly to midpoint()")
