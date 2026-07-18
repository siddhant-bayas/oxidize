from __future__ import annotations

import click
from rich.console import Console

from oxidize.core.repository import Repository, RepositoryNotFound
from oxidize.undo.reverser import UndoManager

console = Console()


@click.group(invoke_without_command=True)
@click.pass_context
def cmd_branch(ctx: click.Context) -> None:
    """Manage branches."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(cmd_branch_list)


@cmd_branch.command("list")
@click.option("--all", "show_all", is_flag=True, help="Include remote-tracking refs")
def cmd_branch_list(show_all: bool) -> None:
    """List branches."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    branches = sorted(repo.refs.list_branches())
    current = repo.refs.current_branch()
    head = repo.refs.head()

    if not branches:
        click.echo("no branches.")
        return

    for name in branches:
        marker = "*" if name == current else " "
        ref_path = f"refs/heads/{name}"
        oid = repo.refs.read(ref_path) or ""
        short = oid[:8] if oid else "(none)"
        if oid == head:
            short += " (HEAD)"
        console.print(f"  {marker} [cyan]{name}[/]  {short}")


@cmd_branch.command("create")
@click.argument("name")
@click.argument("start_point", required=False, default=None)
def cmd_branch_create(name: str, start_point: str | None) -> None:
    """Create a branch from HEAD (or from start_point)."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    oid = repo.refs.read(start_point) if start_point else repo.refs.head()
    if not oid:
        raise click.ClickException("no commit to branch from")
    repo.refs.write(f"refs/heads/{name}", oid)
    mgr = UndoManager(repo)
    mgr.journal.record(
        op="branch_create",
        data={"branch": name, "oid": oid},
        undo_data={"branch": name},
    )
    click.echo(f"created branch {name} at {oid[:8]}")


@cmd_branch.command("delete")
@click.argument("name")
def cmd_branch_delete(name: str) -> None:
    """Delete a branch."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    current = repo.refs.current_branch()
    if name == current:
        raise click.ClickException(f"cannot delete branch '{name}' checked out at HEAD")
    ref_path = f"refs/heads/{name}"
    oid = repo.refs.read(ref_path)
    if not oid:
        raise click.ClickException(f"branch '{name}' not found")
    repo.refs.delete(ref_path)
    mgr = UndoManager(repo)
    mgr.journal.record(
        op="branch_delete",
        data={"branch": name, "oid": oid},
        undo_data={"branch": name, "oid": oid},
    )
    click.echo(f"deleted branch {name}")
