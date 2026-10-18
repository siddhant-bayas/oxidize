from __future__ import annotations

from pathlib import Path

import click

from oxidize.core.repository import Repository, RepositoryNotFound
from oxidize.importer.git_import import GitImportError, import_git


@click.command("import-git")
@click.argument("source", type=click.Path(exists=True, file_okay=False))
@click.option("--target", type=click.Path(), default=".", help="target directory")
def cmd_import_git(source: str, target: str) -> None:
    """Import a git repository's history into an oxidize repository."""
    target_path = Path(target).resolve()
    try:
        repo = Repository.discover(target_path)
    except RepositoryNotFound:
        repo = Repository.init(target_path)

    try:
        commit_map = import_git(Path(source), repo)
    except GitImportError as exc:
        raise click.ClickException(str(exc))

    click.echo(f"imported {len(commit_map)} commits into {target_path}")
