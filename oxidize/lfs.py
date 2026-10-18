from __future__ import annotations

import hashlib
import os
from pathlib import Path

from oxidize.core.repository import Repository


def threshold() -> int:
    raw = os.environ.get("OXIDIZE_LFS_THRESHOLD")
    if raw:
        try:
            return int(raw)
        except ValueError:
            pass
    return 1024 * 1024


def is_large(data: bytes) -> bool:
    return len(data) >= threshold()


def _lfs_path(repo: Repository, content_hash: str) -> Path:
    root = repo.oxidize_dir / "lfs" / "objects"
    return root / content_hash[:2] / content_hash[2:]


def store(repo: Repository, data: bytes) -> tuple[str, str]:
    content_hash = hashlib.sha256(data).hexdigest()
    target = _lfs_path(repo, content_hash)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_bytes(data)
    pointer = f"version https://oxidize.com/lfs/v1\noid sha256:{content_hash}\nsize {len(data)}\n"
    oid = repo.db.store_blob(pointer.encode())
    return oid, content_hash


def is_pointer(data: bytes) -> bool:
    return data.startswith(b"version https://oxidize.com/lfs/v1")


def parse_pointer(data: bytes) -> str | None:
    if not is_pointer(data):
        return None
    for line in data.decode(errors="replace").splitlines():
        if line.startswith("oid "):
            parts = line.split()
            if len(parts) == 2 and parts[1].startswith("sha256:"):
                return parts[1].split(":", 1)[1]
    return None


def resolve_data(repo: Repository, data: bytes) -> bytes:
    content_hash = parse_pointer(data)
    if content_hash is None:
        return data
    target = _lfs_path(repo, content_hash)
    if target.exists():
        return target.read_bytes()
    return data


def load_blob_data(repo: Repository, oid: str) -> bytes:
    blob = repo.db.load_blob(oid)
    return resolve_data(repo, blob.data)
