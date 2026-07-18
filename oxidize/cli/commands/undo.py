from __future__ import annotations

import time

import click
from rich.console import Console

from oxidize.core.repository import Repository, RepositoryNotFound
from oxidize.undo.journal import Journal, JournalEntry
from oxidize.undo.reverser import UndoManager

console = Console()


@click.group(invoke_without_command=True)
@click.pass_context
@click.option("--list", "show_list", is_flag=True, help="Reverse-browse the journal")
def cmd_undo(ctx: click.Context, show_list: bool) -> None:
    """Undo the last operation (or browse the journal with --list)."""
    if show_list:
        ctx.invoke(cmd_journal)
        return
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


@cmd_undo.command("list")
def cmd_journal() -> None:
    """Show the operation journal (newest first)."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    journal = Journal(repo.oxidize_dir / "journal.json")
    entries = journal.entries()
    if not entries:
        click.echo("No operations recorded.")
        return

    n = len(entries)
    for i, entry in enumerate(reversed(entries)):
        seq = n - i
        dt = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.timestamp))
        detail = _summarize(entry)
        console.print(f"  [{seq:>3}] [dim]{dt}[/]  [cyan]{entry.op:<14}[/]  {detail}")


def _summarize(entry: "JournalEntry") -> str:
    data = getattr(entry, "data", None) or {}
    op = getattr(entry, "op", "?")
    if op == "add":
        return f"{len(data.get('paths', []))} file(s) staged"
    if op == "commit":
        return f"commit {str(data.get('commit_oid', ''))[:8]}: {data.get('message', '')}".strip()
    if op == "branch_create":
        return f"created '{data.get('branch', '?')}'"
    if op == "branch_delete":
        return f"deleted '{data.get('branch', '?')}'"
    if op == "tag_create":
        return f"tag '{data.get('tag', '?')}'"
    if op == "tag_delete":
        return f"tag '{data.get('tag', '?')}'"
    if op == "stash":
        return str(data.get("name", ""))
    if op == "merge":
        return f"merge {str(data.get('commit_oid', ''))[:8]}"
    if op == "reset":
        return f"reset to {str(data.get('oid', ''))[:8]}"
    return str(data)


def _do_undo(count: int) -> None:
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    mgr = UndoManager(repo)
    messages = mgr.undo(count)
    for msg in messages:
        click.echo(msg)
