from __future__ import annotations

from pathlib import Path

import click

from oxidize.core.repository import Repository, RepositoryNotFound
from oxidize.exporter.git_export import GitExportError, export_git


@click.command("export-git")
@click.argument("target", type=click.Path())
def cmd_export_git(target: str) -> None:
    """Export the current oxidize repository to a git repository."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))
    try:
        count = export_git(repo, Path(target).resolve())
    except GitExportError as e:
        raise click.ClickException(str(e))
    click.echo(f"exported {count} commits to {target}")
