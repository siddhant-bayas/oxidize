from __future__ import annotations

import click
from rich.console import Console

from oxidize.core.repository import Repository, RepositoryNotFound

console = Console()


@click.group(invoke_without_command=True)
@click.pass_context
def cmd_tag(ctx: click.Context) -> None:
    """Create, list, or delete tags."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(cmd_tag_list)


@cmd_tag.command("list")
@click.option("--verify", is_flag=True, help="Check each tag points to a real object")
def cmd_tag_list(verify: bool) -> None:
    """List existing tags."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    tags = repo.refs.list_tags()
    if not tags:
        click.echo("No tags.")
        return
    for name in sorted(tags):
        oid = repo.refs.read(f"refs/tags/{name}")
        short = oid[:8] if oid else "(dangling)"
        if verify and oid and not repo.db.exists(oid):
            short = f"{short} [red](missing)[/]"
        console.print(f"  {name:<24} {short}")


@cmd_tag.command("create")
@click.argument("name")
@click.argument("ref", required=False, default=None)
def cmd_tag_create(name: str, ref: str | None) -> None:
    """Tag HEAD (or given ref) with a name."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    target = repo.refs.read(ref) if ref else repo.refs.head()
    if not target:
        raise click.ClickException("nothing to tag (no commits yet)")
    repo.refs.write(f"refs/tags/{name}", target)
    click.echo(f"tag {name} -> {target[:8]}")


@cmd_tag.command("delete")
@click.argument("name")
def cmd_tag_delete(name: str) -> None:
    """Delete an existing tag."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    if repo.refs.delete(f"refs/tags/{name}"):
        click.echo(f"deleted tag {name}")
    else:
        raise click.ClickException(f"tag {name} not found")
