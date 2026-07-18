from __future__ import annotations

from pathlib import Path

from oxidize.core.config import Config
from oxidize.core.ignores import IgnoreMatcher
from oxidize.core.refs import RefStore
from oxidize.index.staging import Index
from oxidize.storage.database import ObjectDatabase

OXIDIZE_DIR = ".oxidize"
OXIGNORE_FILE = ".oxignore"


class RepositoryNotFound(Exception):
    pass


class Repository:
    def __init__(self, work_tree: Path) -> None:
        self.work_tree = work_tree
        self.oxidize_dir = work_tree / OXIDIZE_DIR
        self.db = ObjectDatabase.filesystem(self.oxidize_dir / "objects")
        self.refs = RefStore(self.oxidize_dir)
        self.index = Index(self.oxidize_dir / "index.json")
        self.config = Config(self.oxidize_dir / "config")
        self._ignore_matcher: IgnoreMatcher | None = None

    @classmethod
    def init(cls, path: Path) -> "Repository":
        repo = cls(path)
        oxidize_dir = repo.oxidize_dir
        if (oxidize_dir / "HEAD").exists():
            raise FileExistsError(f"repository already exists at {path}")
        for subdir in ["objects", "refs/heads", "refs/tags"]:
            (oxidize_dir / subdir).mkdir(parents=True, exist_ok=True)
        repo.refs.set_head_branch("main")
        oxignore = path / OXIGNORE_FILE
        if not oxignore.exists():
            oxignore.write_text(IgnoreMatcher.starter_content())
        return repo

    @classmethod
    def discover(cls, start: Path | None = None) -> "Repository":
        path = (start or Path.cwd()).resolve()
        for directory in [path, *path.parents]:
            if (directory / OXIDIZE_DIR).is_dir():
                return cls(directory)
        raise RepositoryNotFound(
            "not an oxidize repository (or any parent up to mount point) "
            "-- did you mean `oxidize init`?"
        )

    def resolve_ref(self, ref: str) -> str | None:
        if len(ref) == 64 and all(c in "0123456789abcdef" for c in ref):
            return ref if self.db.exists(ref) else None
        return self.refs.read(ref) or self.refs.read(f"refs/heads/{ref}")

    def is_empty(self) -> bool:
        return self.refs.head() is None

    @property
    def ignore_matcher(self) -> IgnoreMatcher:
        if self._ignore_matcher is None:
            self._ignore_matcher = IgnoreMatcher.from_repo(self)
        return self._ignore_matcher

    def reload_ignores(self) -> IgnoreMatcher:
        self._ignore_matcher = IgnoreMatcher.from_repo(self)
        return self._ignore_matcher
