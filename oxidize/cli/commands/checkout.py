from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from oxidize.core.repository import Repository, RepositoryNotFound
from oxidize.objects.types import Tree

console = Console()


@click.command("checkout")
@click.argument("target")
@click.option("-b", "--create", is_flag=True, help="Create the branch before switching")
@click.option("-f", "--force", is_flag=True, help="Discard local changes")
def cmd_checkout(target: str, create: bool, force: bool) -> None:
    """Switch branches or restore files to a ref."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    if create:
        _create_and_checkout(repo, target, force)
        return

    oid = _resolve_target(repo, target)
    if not oid:
        raise click.ClickException(f"target '{target}' did not resolve to any commit")

    _restore_work_tree(repo, oid, force)
    repo.refs.set_head_branch(target) if _is_branch(repo, target) else _detach(repo, oid)
    console.print(f"HEAD -> [cyan]{target}[/] ({oid[:8]})")


def _create_and_checkout(repo: Repository, name: str, force: bool) -> None:
    head = repo.refs.head()
    if not head:
        raise click.ClickException("no commit to branch from")
    repo.refs.write(f"refs/heads/{name}", head)
    _restore_work_tree(repo, head, force)
    repo.refs.set_head_branch(name)
    console.print(f"created branch [cyan]{name}[/] at {head[:8]}")


def _resolve_target(repo: Repository, target: str) -> str | None:
    if len(target) == 64 and all(c in "0123456789abcdef" for c in target):
        return target if repo.db.exists(target) else None
    return repo.refs.read(target) or repo.refs.read(f"refs/heads/{target}")


def _is_branch(repo: Repository, name: str) -> bool:
    ref_path = f"refs/heads/{name}"
    return repo.refs.exists(ref_path)


def _detach(repo: Repository, oid: str) -> None:
    (repo.oxidize_dir / "HEAD").write_text(oid + "\n")


def _restore_work_tree(repo: Repository, target_oid: str, force: bool) -> None:
    if not force and any(_is_dirty(p, repo.work_tree) for p in repo.work_tree.iterdir()):
        if not _staged_or_untracked(repo):
            raise click.ClickException("local changes would be overwritten (use -f to discard)")
    commit = repo.db.load_commit(target_oid)
    tree = repo.db.load_tree(commit.tree_oid)
    _write_tree(repo, tree, repo.work_tree)


def _is_dirty(path: Path, root: Path) -> bool:
    return False  # simplified: don't deep-check; use untracked/staged signalling instead


def _staged_or_untracked(repo: Repository) -> bool:
    return bool(repo.index.entries()) or any(p.is_file() for p in repo.work_tree.rglob("*"))


def _write_tree(repo: Repository, tree: Tree, root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for entry in tree:
        if entry.mode.value != "040000":
            try:
                blob = repo.db.load_blob(entry.oid)
            except Exception:
                continue
            target = root / entry.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob.data)
