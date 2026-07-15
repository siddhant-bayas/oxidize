from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from oxidize.objects.types import FileMode


@dataclass
class IndexEntry:
    path: str
    oid: str
    mode: str
    size: int
    mtime: float

    def is_stale(self, disk_path: Path) -> bool:
        try:
            s = disk_path.stat()
            return s.st_mtime != self.mtime or s.st_size != self.size
        except FileNotFoundError:
            return True


class Index:
    def __init__(self, index_path: Path) -> None:
        self._path = index_path
        self._entries: dict[str, IndexEntry] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        data = json.loads(self._path.read_text())
        for entry in data:
            e = IndexEntry(**entry)
            self._entries[e.path] = e

    def _save(self) -> None:
        self._path.write_text(json.dumps([asdict(e) for e in self._entries.values()], indent=2))

    def add(self, path: str, oid: str, disk_path: Path) -> None:
        s = disk_path.stat()
        mode = FileMode.from_stat(s.st_mode)
        self._entries[path] = IndexEntry(
            path=path,
            oid=oid,
            mode=mode.value,
            size=s.st_size,
            mtime=s.st_mtime,
        )
        self._save()

    def remove(self, path: str) -> None:
        self._entries.pop(path, None)
        self._save()

    def get(self, path: str) -> IndexEntry | None:
        return self._entries.get(path)

    def entries(self) -> list[IndexEntry]:
        return list(self._entries.values())

    def clear(self) -> None:
        self._entries.clear()
        self._save()

    def __contains__(self, path: str) -> bool:
        return path in self._entries

    def __len__(self) -> int:
        return len(self._entries)
