from __future__ import annotations

import json
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

from oxidize.core.repository import Repository


class Stash:
    def __init__(self, stash_dir: Path) -> None:
        self._dir = stash_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def save(self, repo: Repository, message: str | None = None) -> str:
        name = f"stash-{int(time.time())}-{uuid.uuid4().hex[:6]}"
        target = self._dir / name
        target.mkdir(parents=True)

        index: list[dict[str, Any]] = []
        for entry in list(repo.index.entries()):
            src = repo.work_tree / entry.path
            try:
                blob_target = target / entry.path
                blob_target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, blob_target)
            except OSError:
                pass
            index.append({
                "path": entry.path,
                "oid": entry.oid,
                "mode": entry.mode,
                "size": entry.size,
                "mtime": entry.mtime,
            })

        meta = {
            "name": name,
            "created_at": time.time(),
            "message": message or "",
            "index": index,
        }
        (target / "meta.json").write_text(json.dumps(meta, indent=2))

        repo.index.clear()
        return name

    def list(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for meta_file in sorted(self._dir.glob("stash-*/meta.json")):
            try:
                items.append(json.loads(meta_file.read_text()))
            except (OSError, json.JSONDecodeError):
                continue
        return items

    def pop(self, name: str, repo: Repository) -> bool:
        target = self._dir / name
        if not target.is_dir():
            return False
        meta_path = target / "meta.json"
        meta = json.loads(meta_path.read_text())
        for entry in meta["index"]:
            src = target / entry["path"]
            dst = repo.work_tree / entry["path"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            from oxidize.index.staging import IndexEntry
            repo.index._entries[entry["path"]] = IndexEntry(
                path=entry["path"],
                oid=entry["oid"],
                mode=entry["mode"],
                size=entry["size"],
                mtime=entry["mtime"],
            )
        repo.index._save()
        shutil.rmtree(target)
        return True
