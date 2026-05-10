from __future__ import annotations

from pathlib import Path

from oxide.core.config import Config
from oxide.core.refs import RefStore
from oxide.index.staging import Index
from oxide.storage.database import ObjectDatabase

OXIDE_DIR = ".oxide"


class RepositoryNotFound(Exception):
    pass


class Repository:
    def __init__(self, work_tree: Path) -> None:
        self.work_tree = work_tree
        self.oxide_dir = work_tree / OXIDE_DIR
        self.db = ObjectDatabase.filesystem(self.oxide_dir / "objects")
        self.refs = RefStore(self.oxide_dir)
        self.index = Index(self.oxide_dir / "index.json")
        self.config = Config(self.oxide_dir / "config")

    @classmethod
    def init(cls, path: Path) -> "Repository":
        repo = cls(path)
        oxide_dir = repo.oxide_dir
        if (oxide_dir / "HEAD").exists():
            raise FileExistsError(f"repository already exists at {path}")
        for subdir in ["objects", "refs/heads", "refs/tags"]:
            (oxide_dir / subdir).mkdir(parents=True, exist_ok=True)
        repo.refs.set_head_branch("main")
        return repo

    @classmethod
    def discover(cls, start: Path | None = None) -> "Repository":
        path = (start or Path.cwd()).resolve()
        for directory in [path, *path.parents]:
            if (directory / OXIDE_DIR).is_dir():
                return cls(directory)
        raise RepositoryNotFound("not an oxide repository (or any parent up to mount point)")

    def resolve_ref(self, ref: str) -> str | None:
        if len(ref) == 64 and all(c in "0123456789abcdef" for c in ref):
            return ref if self.db.exists(ref) else None
        return self.refs.read(ref) or self.refs.read(f"refs/heads/{ref}")

    def is_empty(self) -> bool:
        return self.refs.head() is None
