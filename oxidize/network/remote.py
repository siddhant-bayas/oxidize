from __future__ import annotations

import shutil
from functools import partial
from pathlib import Path

from oxidize.core.repository import Repository
from oxidize.objects.types import FileMode
from oxidize.storage.backend import _atomic_write
from oxidize.storage.database import ObjectDatabase


class TransferError(Exception):
    pass


def _has_objects(objects_dir: Path) -> bool:
    if not objects_dir.exists():
        return False
    for prefix_dir in objects_dir.iterdir():
        if prefix_dir.is_dir():
            for _ in prefix_dir.iterdir():
                return True
    return False


def _bulk_copy_objects(src_root: Path, dst_root: Path) -> None:
    src_objects = src_root / "objects"
    dst_objects = dst_root
    if not src_objects.exists():
        return
    for sub in src_objects.iterdir():
        if not sub.is_dir():
            continue
        (dst_objects / sub.name).mkdir(parents=True, exist_ok=True)
        for obj in sub.iterdir():
            dst = dst_objects / sub.name / obj.name
            _atomic_write(dst, partial(shutil.copy2, obj))


class Remote:
    def __init__(self, url: str) -> None:
        self.url = url

    @property
    def bare_path(self) -> Path:
        if self.url.startswith("file://"):
            return Path(self.url[len("file://") :])
        if self.url.startswith("file:"):
            return Path(self.url[len("file:") :])
        return Path(self.url)

    def ensure_bare(self) -> Path:
        bare = self.bare_path
        if (bare / "HEAD").exists():
            return bare
        (bare / "objects").mkdir(parents=True, exist_ok=True)
        (bare / "refs" / "heads").mkdir(parents=True, exist_ok=True)
        (bare / "refs" / "tags").mkdir(parents=True, exist_ok=True)
        (bare / "HEAD").write_text("ref: refs/heads/main\n")
        return bare

    def clone(self, target: Path) -> Repository:
        bare = self.ensure_bare()
        target_resolved = target.resolve()
        target_resolved.mkdir(parents=True, exist_ok=True)
        repo = Repository.init(target_resolved)

        _copy_objects(bare, repo.oxidize_dir / "objects")
        _copy_refs(bare, repo.oxidize_dir)

        for branch in (bare / "refs" / "heads").iterdir():
            if branch.is_file():
                oid = branch.read_text().strip()
                (repo.oxidize_dir / "refs" / "heads" / branch.name).write_text(oid + "\n")

        head_text = (bare / "HEAD").read_text().strip()
        (repo.oxidize_dir / "HEAD").write_text(head_text + "\n")
        return repo

    def push(
        self, repo: Repository, branch: str | None = None, *, force: bool = False
    ) -> list[str]:
        bare = self.ensure_bare()
        branches = [branch] if branch else repo.refs.list_branches()
        pushed: list[str] = []
        remote_objects = bare / "objects"
        first_push = not _has_objects(remote_objects)
        for b in branches:
            local_oid = repo.refs.read(f"refs/heads/{b}")
            if not local_oid:
                raise TransferError(f"local branch '{b}' not found")
            remote_ref = bare / "refs" / "heads" / b
            if remote_ref.exists() and not force:
                remote_oid = remote_ref.read_text().strip()
                if remote_oid != local_oid and not _is_ancestor(repo, remote_oid, local_oid):
                    raise TransferError(f"remote branch '{b}' diverges (use --force)")
            if first_push:
                _bulk_copy_objects(repo.oxidize_dir, remote_objects)
                first_push = False
            else:
                _copy_objects(repo.oxidize_dir, remote_objects, stop=local_oid, repo=repo)
            remote_ref.parent.mkdir(parents=True, exist_ok=True)
            remote_ref.write_text(local_oid + "\n")
            pushed.append(b)
        return pushed

    def pull(self, repo: Repository, branch: str | None = None) -> list[str]:
        bare = self.ensure_bare()
        pulled: list[str] = []

        target_branches: list[str]
        if branch:
            target_branches = [branch]
        else:
            target_branches = [p.name for p in (bare / "refs" / "heads").iterdir()]

        remote_db = ObjectDatabase.filesystem(bare / "objects")
        local_objects = repo.oxidize_dir / "objects"
        first_pull = not _has_objects(local_objects)

        for b in target_branches:
            remote_ref = bare / "refs" / "heads" / b
            if not remote_ref.exists():
                continue
            remote_oid = remote_ref.read_text().strip()
            local_ref = repo.oxidize_dir / "refs" / "heads" / b
            local_oid = local_ref.read_text().strip() if local_ref.exists() else ""

            if local_oid == remote_oid:
                continue
            if first_pull:
                _bulk_copy_objects(bare, local_objects)
                first_pull = False
            else:
                missing = _reachable_oids(remote_db, [remote_oid], repo.db)
                for oid in missing:
                    _copy_object(bare, local_objects, oid)
            local_ref.parent.mkdir(parents=True, exist_ok=True)
            local_ref.write_text(remote_oid + "\n")
            pulled.append(b)
        return pulled


def _copy_objects(
    src_root: Path, dst_root: Path, *, stop: str | None = None, repo: Repository | None = None
) -> None:
    src_objects = src_root / "objects"
    if not src_objects.exists():
        return
    if not stop:
        _bulk_copy_objects(src_root, dst_root)
        return
    commit_stack = [stop]
    tree_stack: list[str] = []
    seen_commits: set[str] = set()
    seen_trees: set[str] = set()

    while commit_stack:
        oid = commit_stack.pop()
        if oid in seen_commits:
            continue
        seen_commits.add(oid)
        _copy_object(src_root, dst_root, oid)
        if not repo:
            continue
        try:
            commit = repo.db.load_commit(oid)
        except Exception:
            continue
        commit_stack.extend(commit.parents)
        tree_stack.append(commit.tree_oid)

    while tree_stack:
        oid = tree_stack.pop()
        if oid in seen_trees:
            continue
        seen_trees.add(oid)
        _copy_object(src_root, dst_root, oid)
        if not repo:
            continue
        try:
            tree = repo.db.load_tree(oid)
        except Exception:
            continue
        for entry in tree:
            if entry.mode == FileMode.DIRECTORY:
                tree_stack.append(entry.oid)
            else:
                _copy_object(src_root, dst_root, entry.oid)


def _copy_object(src_root: Path, dst_root: Path, oid: str) -> None:
    sub = oid[:2]
    name = oid[2:]
    src = src_root / "objects" / sub / name
    if not src.exists():
        return
    dst = dst_root / sub / name
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        return
    _atomic_write(dst, lambda tmp: shutil.copy2(src, tmp))


def _copy_refs(src_root: Path, dst_root: Path) -> None:
    src_refs = src_root / "refs"
    if not src_refs.exists():
        return
    for sub in src_refs.iterdir():
        target_dir = dst_root / "refs" / sub.name
        target_dir.mkdir(parents=True, exist_ok=True)
        if sub.is_file():
            shutil.copy2(sub, target_dir / sub.name)
            continue
        for f in sub.iterdir():
            if f.is_file():
                shutil.copy2(f, target_dir / f.name)


def _is_ancestor(repo: Repository, ancestor_oid: str, descendant_oid: str) -> bool:
    seen: set[str] = set()
    stack = [descendant_oid]
    while stack:
        oid = stack.pop()
        if oid == ancestor_oid:
            return True
        if oid in seen:
            continue
        seen.add(oid)
        try:
            commit = repo.db.load_commit(oid)
            stack.extend(commit.parents)
        except Exception:
            continue
    return False


def _reachable_oids(
    remote_db: ObjectDatabase, starting: list[str], local_db: ObjectDatabase
) -> list[str]:
    commit_stack = list(starting)
    tree_stack: list[str] = []
    seen_commits: set[str] = set()
    seen_trees: set[str] = set()
    out: list[str] = []

    while commit_stack:
        oid = commit_stack.pop()
        if oid in seen_commits or not oid:
            continue
        seen_commits.add(oid)
        if local_db.exists(oid):
            continue
        out.append(oid)
        try:
            commit = remote_db.load_commit(oid)
        except Exception:
            continue
        commit_stack.extend(commit.parents)
        tree_stack.append(commit.tree_oid)

    while tree_stack:
        oid = tree_stack.pop()
        if oid in seen_trees or not oid:
            continue
        seen_trees.add(oid)
        if local_db.exists(oid):
            continue
        out.append(oid)
        try:
            tree = remote_db.load_tree(oid)
        except Exception:
            continue
        for entry in tree:
            if entry.mode == FileMode.DIRECTORY:
                tree_stack.append(entry.oid)
            else:
                if not local_db.exists(entry.oid):
                    out.append(entry.oid)

    return out
