from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class OpType(str, Enum):
    ADD = "add"
    COMMIT = "commit"
    BRANCH_CREATE = "branch_create"
    BRANCH_DELETE = "branch_delete"
    STAGE_CLEAR = "stage_clear"


@dataclass
class JournalEntry:
    op: str
    timestamp: float
    data: dict[str, Any] = field(default_factory=dict)
    undo_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "op": self.op,
            "timestamp": self.timestamp,
            "data": self.data,
            "undo": self.undo_data,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> JournalEntry:
        return cls(
            op=str(d["op"]),
            timestamp=float(d["timestamp"]),
            data=dict(d.get("data", {})),
            undo_data=dict(d.get("undo", {})),
        )


class Journal:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._entries: list[JournalEntry] = []
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        data = json.loads(self._path.read_text())
        self._entries = [JournalEntry.from_dict(e) for e in data]

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps([e.to_dict() for e in self._entries], indent=2))

    def record(self, op: str, data: dict[str, Any], undo_data: dict[str, Any]) -> None:
        entry = JournalEntry(op=op, timestamp=time.time(), data=data, undo_data=undo_data)
        self._entries.append(entry)
        self._save()

    def last(self) -> JournalEntry | None:
        return self._entries[-1] if self._entries else None

    def pop_last(self) -> JournalEntry | None:
        if self._entries:
            entry = self._entries.pop()
            self._save()
            return entry
        return None

    def entries(self) -> list[JournalEntry]:
        return list(self._entries)

    def __len__(self) -> int:
        return len(self._entries)
