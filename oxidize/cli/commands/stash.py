from __future__ import annotations

import click
from rich.console import Console

from oxidize.core.repository import Repository, RepositoryNotFound
from oxidize.staging.stash import Stash

console = Console()


@click.group(invoke_without_command=True)
@click.pass_context
def cmd_stash(ctx: click.Context) -> None:
    """Stash changes for later."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(cmd_stash_save, message=None)


@cmd_stash.command("save")
@click.argument("message", required=False, default=None)
def cmd_stash_save(message: str | None) -> None:
    """Save the current index to a stash."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))
    if not repo.index.entries():
        raise click.ClickException("nothing to stash")
    stash = Stash(repo.oxidize_dir / "stashes")
    name = stash.save(repo, message)
    console.print(f"saved stash [cyan]{name}[/]")


@cmd_stash.command("list")
def cmd_stash_list() -> None:
    """List stashes."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))
    items = Stash(repo.oxidize_dir / "stashes").list()
    if not items:
        click.echo("no stashes.")
        return
    for i, meta in enumerate(items):
        msg = meta.get("message") or "(no message)"
        console.print(f"  [{i}] [cyan]{meta['name']}[/]  {msg}")


@cmd_stash.command("pop")
@click.argument("name_or_idx")
def cmd_stash_pop(name_or_idx: str) -> None:
    """Pop a stash back into the index."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))
    items = Stash(repo.oxidize_dir / "stashes").list()
    target = name_or_idx
    try:
        idx = int(name_or_idx)
        if 0 <= idx < len(items):
            target = items[idx]["name"]
    except ValueError:
        pass
    if not Stash(repo.oxidize_dir / "stashes").pop(target, repo):
        raise click.ClickException(f"stash '{target}' not found")
    click.echo(f"applied stash {target}")
