from __future__ import annotations

import datetime

import click
from rich.console import Console

from oxidize.core.repository import Repository, RepositoryNotFound

console = Console()


@click.command("log")
@click.option("-n", "--count", default=20, help="Max commits to show")
@click.option("--agent", default=None, help="Filter by agent (e.g. claude-code)")
@click.option("--author", default=None, help="Filter by author name/email substring")
@click.option("--oneline", is_flag=True, help="One line per commit")
def cmd_log(count: int, agent: str | None, author: str | None, oneline: bool) -> None:
    """Show commit history."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    head = repo.refs.head()
    if not head:
        click.echo("No commits yet.")
        return

    shown = 0
    oid: str | None = head
    while oid and shown < count:
        commit = repo.db.load_commit(oid)

        if agent is not None and commit.agent != agent:
            oid = commit.parents[0] if commit.parents else None
            continue
        if author is not None:
            attr_blob = f"{commit.author.name} {commit.author.email}".lower()
            if author.lower() not in attr_blob:
                oid = commit.parents[0] if commit.parents else None
                continue

        if oneline:
            agent_str = f" [agent={commit.agent}]" if commit.agent else ""
            console.print(f"[yellow]{oid[:8]}[/] {commit.message.strip().splitlines()[0]}{agent_str}")
        else:
            dt = datetime.datetime.fromtimestamp(commit.author.timestamp)
            date_str = dt.strftime("%a %b %d %H:%M:%S %Y")
            console.print(f"[yellow]commit {oid}[/]")
            console.print(f"Author: {commit.author.name} <{commit.author.email}>")
            if commit.agent:
                console.print(f"Agent:  {commit.agent}")
            console.print(f"Date:   {date_str}\n")
            console.print(f"    {commit.message}\n")

        shown += 1
        oid = commit.parents[0] if commit.parents else None
