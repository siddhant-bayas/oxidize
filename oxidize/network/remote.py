from __future__ import annotations

import shutil
from pathlib import Path

from oxidize.core.repository import Repository


class TransferError(Exception):
    pass


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

        _copy_objects(bare, target_resolved / "oxidize_dir" / "objects")
        _copy_refs(bare, target_resolved / "oxidize_dir")

        for branch in (bare / "refs" / "heads").iterdir():
            oid = (bare / "refs" / "heads" / branch.name).read_text().strip()
            (target_resolved / ".oxidize" / "refs" / "heads" / branch.name).write_text(oid + "\n")

        head_text = (bare / "HEAD").read_text().strip()
        if head_text.startswith("ref: refs/heads/"):
            current = head_text[len("ref: refs/heads/") :]
            (target_resolved / ".oxidize" / "HEAD").write_text(head_text + "\n")
            oid = (target_resolved / ".oxidize" / "refs" / "heads" / current).read_text().strip()
            (target_resolved / ".oxidize" / "refs" / "heads" / current).write_text(oid + "\n")
        return repo

    def push(self, repo: Repository, branch: str | None = None, *, force: bool = False) -> list[str]:
        bare = self.ensure_bare()
        branches = [branch] if branch else repo.refs.list_branches()
        pushed: list[str] = []
        for b in branches:
            local_oid = repo.refs.read(f"refs/heads/{b}")
            if not local_oid:
                raise TransferError(f"local branch '{b}' not found")
            remote_ref = bare / "refs" / "heads" / b
            if remote_ref.exists() and not force:
                remote_oid = remote_ref.read_text().strip()
                if remote_oid != local_oid and not repo.refs.exists(f"refs/heads/{b}"):
                    raise TransferError(f"remote branch '{b}' diverges (use --force)")
            _copy_objects(repo.oxidize_dir, bare / "objects", stop=local_oid, repo=repo)
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

        for b in target_branches:
            remote_ref = bare / "refs" / "heads" / b
            if not remote_ref.exists():
                continue
            remote_oid = remote_ref.read_text().strip()
            local_ref = repo.oxidize_dir / "refs" / "heads" / b
            local_oid = local_ref.read_text().strip() if local_ref.exists() else ""

            if local_oid == remote_oid:
                continue
            parent_oids = _reachable_oids(repo, [remote_oid], limit=50)
            for oid in parent_oids:
                _copy_object(repo.oxidize_dir, bare / "objects", oid)
            local_ref.parent.mkdir(parents=True, exist_ok=True)
            local_ref.write_text(remote_oid + "\n")
            pulled.append(b)
        return pulled


def _copy_objects(src_root: Path, dst_root: Path, *, stop: str | None = None, repo: Repository | None = None) -> None:
    src_objects = src_root / "objects"
    dst_objects = dst_root
    if not src_objects.exists():
        return
    if not stop:
        for sub in src_objects.iterdir():
            if not sub.is_dir():
                continue
            (dst_objects / sub.name).mkdir(parents=True, exist_ok=True)
            for obj in sub.iterdir():
                shutil.copy2(obj, dst_objects / sub.name / obj.name)
        return
    seen: set[str] = set()
    stack = [stop]
    while stack:
        oid = stack.pop()
        if oid in seen:
            continue
        seen.add(oid)
        _copy_object(src_root, dst_root, oid)
        if repo:
            try:
                commit = repo.db.load_commit(oid)
            except Exception:
                continue
            stack.extend(commit.parents)
            try:
                tree = repo.db.load_tree(commit.tree_oid)
            except Exception:
                continue
            for entry in tree:
                stack.append(entry.oid)


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
    shutil.copy2(src, dst)


def _copy_refs(src_root: Path, dst_root: Path) -> None:
    src_refs = src_root / "refs"
    if not src_refs.exists():
        return
    for sub in src_refs.iterdir():
        target_dir = dst_root / "refs" / sub.name
        target_dir.mkdir(parents=True, exist_ok=True)
        if sub.is_file():
            shutil.copy2(sub, target_dir / sub.name)
            return
        for f in sub.iterdir():
            if f.is_file():
                shutil.copy2(f, target_dir / f.name)


def _reachable_oids(repo: Repository, starting: list[str], *, limit: int) -> list[str]:
    seen: set[str] = set()
    stack = list(starting)
    out: list[str] = []
    while stack and len(out) < limit * 5:
        oid = stack.pop()
        if oid in seen or not oid:
            continue
        seen.add(oid)
        out.append(oid)
        try:
            commit = repo.db.load_commit(oid)
        except Exception:
            continue
        stack.extend(commit.parents)
        try:
            tree = repo.db.load_tree(commit.tree_oid)
        except Exception:
            continue
        for entry in tree:
            stack.append(entry.oid)
    return out
