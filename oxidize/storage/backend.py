from __future__ import annotations

import zlib
from abc import ABC, abstractmethod
from pathlib import Path

from oxidize.objects.types import ObjectType


class StorageBackend(ABC):
    @abstractmethod
    def read(self, oid: str) -> tuple[ObjectType, bytes]: ...

    @abstractmethod
    def write(self, type: ObjectType, data: bytes) -> str: ...

    @abstractmethod
    def exists(self, oid: str) -> bool: ...


class FilesystemBackend(StorageBackend):
    def __init__(self, objects_dir: Path) -> None:
        self._root = objects_dir
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, oid: str) -> Path:
        return self._root / oid[:2] / oid[2:]

    def read(self, oid: str) -> tuple[ObjectType, bytes]:
        path = self._path(oid)
        if not path.exists():
            raise KeyError(f"object not found: {oid}")
        raw = zlib.decompress(path.read_bytes())
        null = raw.index(b"\x00")
        header = raw[:null].decode()
        type_str, _ = header.split(" ", 1)
        return ObjectType(type_str), raw[null + 1 :]

    def write(self, type: ObjectType, data: bytes) -> str:
        from oxidize.objects.types import hash_object

        oid = hash_object(type, data)
        path = self._path(oid)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            header = f"{type.value} {len(data)}\x00".encode()
            path.write_bytes(zlib.compress(header + data))
        return oid

    def exists(self, oid: str) -> bool:
        return self._path(oid).exists()
