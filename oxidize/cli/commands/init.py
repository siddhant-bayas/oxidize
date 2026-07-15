from pathlib import Path

import click

from oxidize.core.repository import Repository


@click.command("init")
@click.argument("path", default=".", type=click.Path())
def cmd_init(path: str) -> None:
    """Initialize a new oxidize repository."""
    target = Path(path).resolve()
    target.mkdir(parents=True, exist_ok=True)
    try:
        repo = Repository.init(target)
        click.echo(f"Initialized empty oxidize repository in {repo.oxidize_dir}")
    except FileExistsError as e:
        raise click.ClickException(str(e))
