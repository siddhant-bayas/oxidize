from pathlib import Path

import click

from oxidize.core.repository import Repository, RepositoryNotFound
from oxidize.undo.reverser import UndoManager


@click.command("add")
@click.argument("paths", nargs=-1, required=True, type=click.Path(exists=True))
def cmd_add(paths: tuple[str, ...]) -> None:
    """Stage files for the next commit."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    undo_mgr = UndoManager(repo)
    added_paths: list[str] = []
    added_oids: list[str] = []

    for raw_path in paths:
        target = Path(raw_path).resolve()
        if target.is_dir():
            files = [f for f in target.rglob("*") if f.is_file()]
        else:
            files = [target]

        for file_path in files:
            rel = file_path.relative_to(repo.work_tree).as_posix()
            oid = repo.db.store_blob(file_path.read_bytes())
            repo.index.add(rel, oid, file_path)
            added_paths.append(rel)
            added_oids.append(oid)
            click.echo(f"  staged: {rel}")

    if added_paths:
        undo_mgr.record_add(added_paths, added_oids)
