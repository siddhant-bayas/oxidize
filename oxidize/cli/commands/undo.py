from __future__ import annotations

import time

import click
from rich.console import Console

from oxidize.core.repository import Repository, RepositoryNotFound
from oxidize.undo.journal import Journal
from oxidize.undo.reverser import UndoManager

console = Console()


@click.group(invoke_without_command=True)
@click.pass_context
def cmd_undo(ctx: click.Context) -> None:
    """Undo the last operation."""
    if ctx.invoked_subcommand is None:
        _do_undo(1)


@cmd_undo.command("last")
def cmd_undo_last() -> None:
    """Undo the last operation."""
    _do_undo(1)


@cmd_undo.command("count")
@click.argument("n", type=int)
def cmd_undo_count(n: int) -> None:
    """Undo the last N operations."""
    _do_undo(n)


@cmd_undo.command("journal")
def cmd_journal() -> None:
    """Show operation journal."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    journal = Journal(repo.oxidize_dir / "journal.json")
    entries = journal.entries()

    if not entries:
        click.echo("No operations recorded.")
        return

    for i, entry in enumerate(reversed(entries)):
        dt = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.timestamp))
        click.echo(f"  {i + 1}. [{dt}] {entry.op} - {entry.data}")


def _do_undo(count: int) -> None:
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    mgr = UndoManager(repo)
    messages = mgr.undo(count)
    for msg in messages:
        click.echo(msg)
