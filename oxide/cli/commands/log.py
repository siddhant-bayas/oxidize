from __future__ import annotations

import datetime

import click
from rich.console import Console

from oxide.core.repository import Repository, RepositoryNotFound

console = Console()


@click.command("log")
@click.option("-n", "--count", default=20, help="Max commits to show")
def cmd_log(count: int) -> None:
    """Show commit history."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    head = repo.refs.head()
    if not head:
        click.echo("No commits yet.")
        return

    oid: str | None = head
    shown = 0
    while oid and shown < count:
        commit = repo.db.load_commit(oid)
        dt = datetime.datetime.fromtimestamp(commit.author.timestamp)
        date_str = dt.strftime("%a %b %d %H:%M:%S %Y")

        console.print(f"[yellow]commit {oid}[/]")
        console.print(f"Author: {commit.author.name} <{commit.author.email}>")
        console.print(f"Date:   {date_str}\n")
        console.print(f"    {commit.message}\n")

        oid = commit.parents[0] if commit.parents else None
        shown += 1
