from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from oxidize.core.repository import Repository, RepositoryNotFound
from oxidize.undo.reverser import UndoManager

console = Console()


@click.command("add")
@click.argument("paths", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("-f", "--force", is_flag=True, help="Add ignored files (bypass .oxignore)")
def cmd_add(paths: tuple[str, ...], force: bool) -> None:
    """Stage files for the next commit."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    matcher = repo.ignore_matcher

    undo_mgr = UndoManager(repo)
    added_paths: list[str] = []
    added_oids: list[str] = []
    skipped_paths: list[str] = []

    for raw_path in paths:
        target = Path(raw_path).resolve()
        if target.is_dir():
            candidates = [f for f in target.rglob("*") if f.is_file()]
        else:
            candidates = [target]

        if force:
            files = candidates
        else:
            files = []
            for f in candidates:
                try:
                    rel = f.relative_to(repo.work_tree).as_posix()
                except ValueError:
                    files.append(f)
                    continue
                if matcher.is_ignored(rel):
                    skipped_paths.append(rel)
                else:
                    files.append(f)

        for file_path in files:
            rel = file_path.relative_to(repo.work_tree).as_posix()
            oid = repo.db.store_blob(file_path.read_bytes())
            repo.index.add(rel, oid, file_path)
            added_paths.append(rel)
            added_oids.append(oid)
            click.echo(f"  staged: {rel}")

    for skipped in skipped_paths:
        console.print(f"  [dim]ignored: {skipped}[/]")

    if added_paths:
        undo_mgr.record_add(added_paths, added_oids)
