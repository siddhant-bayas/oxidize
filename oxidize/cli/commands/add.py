from pathlib import Path

import click

from oxidize.core.repository import Repository, RepositoryNotFound


@click.command("add")
@click.argument("paths", nargs=-1, required=True, type=click.Path(exists=True))
def cmd_add(paths: tuple[str, ...]) -> None:
    """Stage files for the next commit."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

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
            click.echo(f"  staged: {rel}")
