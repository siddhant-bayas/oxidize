from pathlib import Path

import click

from oxide.core.repository import Repository


@click.command("init")
@click.argument("path", default=".", type=click.Path())
def cmd_init(path: str) -> None:
    """Initialize a new Oxide repository."""
    target = Path(path).resolve()
    target.mkdir(parents=True, exist_ok=True)
    try:
        repo = Repository.init(target)
        click.echo(f"Initialized empty Oxide repository in {repo.oxide_dir}")
    except FileExistsError as e:
        raise click.ClickException(str(e))
