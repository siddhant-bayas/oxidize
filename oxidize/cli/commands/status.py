from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from oxidize.core.ignores import IgnoreMatcher
from oxidize.core.repository import Repository, RepositoryNotFound

console = Console()


def _walk(root: Path, matcher: "IgnoreMatcher") -> list[Path]:
    result = []
    for p in sorted(root.rglob("*")):
        try:
            rel = p.relative_to(root).as_posix()
        except ValueError:
            continue
        if p.is_file() and not matcher.is_ignored(rel):
            result.append(p)
    return result


@click.command("status")
def cmd_status() -> None:
    """Show working tree status."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    branch = repo.refs.current_branch() or "(detached HEAD)"
    console.print(f"On branch [bold cyan]{branch}[/]")

    staged: list[str] = []
    modified: list[str] = []
    untracked: list[str] = []

    indexed_paths = {ie.path for ie in repo.index.entries()}
    disk_files = _walk(repo.work_tree, repo.ignore_matcher)

    head_tree_names: set[str] = set()
    head = repo.refs.head()
    if head:
        commit = repo.db.load_commit(head)
        tree = repo.db.load_tree(commit.tree_oid)
        for tree_entry in tree:
            head_tree_names.add(tree_entry.name)

    for file_path in disk_files:
        rel = file_path.relative_to(repo.work_tree).as_posix()
        index_entry = repo.index.get(rel)
        if index_entry is not None:
            if index_entry.is_stale(file_path):
                modified.append(rel)
        elif rel in head_tree_names and head is not None:
            blob = repo.db.load_blob(
                next(
                    te.oid
                    for te in repo.db.load_tree(repo.db.load_commit(head).tree_oid)
                    if te.name == rel
                )
            )
            disk_content = file_path.read_text(errors="replace").replace("\r\n", "\n")
            stored_content = blob.data.decode(errors="replace").replace("\r\n", "\n")
            if disk_content != stored_content:
                modified.append(rel)
        else:
            untracked.append(rel)

    for path in indexed_paths:
        full = repo.work_tree / path
        if not full.exists():
            staged.append(f"deleted: {path}")
        else:
            staged.append(path)

    if not staged and not modified and not untracked:
        console.print("nothing to commit, working tree clean")
        return

    if staged:
        console.print("\n[green]Changes staged for commit:[/]")
        for p in staged:
            console.print(f"        [green]{p}[/]")

    if modified:
        console.print("\n[yellow]Changes not staged for commit:[/]")
        for p in modified:
            console.print(f"        [yellow]modified: {p}[/]")

    if untracked:
        console.print("\n[dim]Untracked files:[/]")
        for p in untracked:
            console.print(f"        [dim]{p}[/]")
