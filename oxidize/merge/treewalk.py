from __future__ import annotations

from pathlib import Path

from rich.console import Console

from oxidize.core.ignores import IgnoreMatcher
from oxidize.core.repository import Repository
from oxidize.objects.types import Tree

console = Console()


def _walk(root: Path, matcher: type[IgnoreMatcher] = IgnoreMatcher) -> list[Path]:
    result: list[Path] = []
    for p in sorted(root.rglob("*")):
        if p.is_file():
            try:
                _rel = p.relative_to(root).as_posix()
            except ValueError:
                continue
            result.append(p)
    return result


def _find_merge_base(repo: Repository, a: str, b: str) -> str | None:
    seen_b: set[str] = set()
    stack: list[str] = [b]
    while stack:
        oid = stack.pop()
        if oid in seen_b:
            continue
        seen_b.add(oid)
        try:
            commit = repo.db.load_commit(oid)
        except Exception:
            continue
        stack.extend(commit.parents)
    if a in seen_b:
        return a
    seen_a: set[str] = set()
    stack = [a]
    while stack:
        oid = stack.pop()
        if oid in seen_a:
            continue
        seen_a.add(oid)
        if oid in seen_b:
            return oid
        try:
            commit = repo.db.load_commit(oid)
        except Exception:
            continue
        stack.extend(commit.parents)
    return None


def _list_tree_paths(repo: Repository, tree_oid: str, base: Path = Path("")) -> list[str]:
    out: list[str] = []
    try:
        tree = repo.db.load_tree(tree_oid)
    except Exception:
        return out
    for entry in tree:
        rel = (base / entry.name).as_posix() if base.as_posix() else entry.name
        if entry.mode.value == "040000":
            out.extend(_list_tree_paths(repo, entry.oid, base / entry.name))
        else:
            out.append(rel)
    return out


def _blob_text(repo: Repository, tree_oid: str, path: str) -> tuple[str | None, bool]:
    try:
        tree = repo.db.load_tree(tree_oid)
    except Exception:
        return None, False
    parts = path.split("/")
    return _walk_tree_for_blob(repo, tree, parts)


def _walk_tree_for_blob(
    repo: Repository,
    tree: Tree,
    parts: list[str],
    idx: int = 0,
) -> tuple[str | None, bool]:
    if idx == len(parts):
        return None, False
    name = parts[idx]
    for entry in tree:
        if entry.name == name:
            if idx == len(parts) - 1:
                if entry.mode.value == "040000":
                    return None, True
                try:
                    blob = repo.db.load_blob(entry.oid)
                except Exception:
                    return None, True
                return blob.data.decode(errors="replace"), True
            if entry.mode.value != "040000":
                return None, False
            try:
                subtree = repo.db.load_tree(entry.oid)
            except Exception:
                return None, False
            return _walk_tree_for_blob(repo, subtree, parts, idx + 1)
    return None, False
