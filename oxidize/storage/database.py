from __future__ import annotations

from pathlib import Path

from oxidize.objects.types import Blob, Commit, ObjectType, Tree
from oxidize.storage.backend import FilesystemBackend, StorageBackend


class ObjectDatabase:
    def __init__(self, backend: StorageBackend) -> None:
        self._backend = backend

    @classmethod
    def filesystem(cls, objects_dir: Path) -> "ObjectDatabase":
        return cls(FilesystemBackend(objects_dir))

    def store_blob(self, data: bytes) -> str:
        return self._backend.write(ObjectType.BLOB, data)

    def store_tree(self, tree: Tree) -> str:
        return self._backend.write(ObjectType.TREE, tree.serialize())

    def store_commit(self, commit: Commit) -> str:
        return self._backend.write(ObjectType.COMMIT, commit.serialize())

    def load_blob(self, oid: str) -> Blob:
        type_, data = self._backend.read(oid)
        if type_ != ObjectType.BLOB:
            raise TypeError(f"expected blob, got {type_}")
        return Blob.deserialize(data)

    def load_tree(self, oid: str) -> Tree:
        type_, data = self._backend.read(oid)
        if type_ != ObjectType.TREE:
            raise TypeError(f"expected tree, got {type_}")
        return Tree.deserialize(data)

    def load_commit(self, oid: str) -> Commit:
        type_, data = self._backend.read(oid)
        if type_ != ObjectType.COMMIT:
            raise TypeError(f"expected commit, got {type_}")
        return Commit.deserialize(data)

    def exists(self, oid: str) -> bool:
        return self._backend.exists(oid)
