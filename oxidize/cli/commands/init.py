from pathlib import Path

import click

from oxidize.core.repository import Repository


@click.command("init")
@click.argument("path", default=".", type=click.Path())
def cmd_init(path: str) -> None:
    """Initialize a new oxidize repository."""
    target = Path(path).resolve()
    target.mkdir(parents=True, exist_ok=True)

    oxignore_path = target / ".oxignore"
    oxignore_was_new = not oxignore_path.exists()

    try:
        repo = Repository.init(target)
    except FileExistsError as e:
        raise click.ClickException(str(e))

    click.echo(f"Initialized empty oxidize repository in {repo.oxidize_dir}")
    if oxignore_was_new:
        click.echo(f"Created {oxignore_path}")
