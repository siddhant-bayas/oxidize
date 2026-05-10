from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.text import Text

from oxide.core.repository import Repository, RepositoryNotFound

console = Console()

_IGNORE = {".oxide", ".git", "__pycache__", ".DS_Store"}


def _walk(root: Path) -> list[Path]:
    result = []
    for p in sorted(root.rglob("*")):
        if any(part in _IGNORE for part in p.parts):
            continue
        if p.is_file():
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

    indexed_paths = {e.path for e in repo.index.entries()}
    disk_files = _walk(repo.work_tree)

    for file_path in disk_files:
        rel = file_path.relative_to(repo.work_tree).as_posix()
        entry = repo.index.get(rel)
        if entry is None:
            untracked.append(rel)
        elif entry.is_stale(file_path):
            modified.append(rel)

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
