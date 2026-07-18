from __future__ import annotations

import datetime

import click
from rich.console import Console

from oxidize.core.repository import Repository, RepositoryNotFound

console = Console()


@click.command("show")
@click.argument("ref", default="HEAD")
@click.option("--stat", is_flag=True, help="Show file-level diff stats only")
def cmd_show(ref: str, stat: bool) -> None:
    """Show a commit object (default HEAD)."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    oid = repo.refs.read(ref) or ref
    if not repo.db.exists(oid):
        raise click.ClickException(f"unknown ref: {ref}")

    commit = repo.db.load_commit(oid)
    dt = datetime.datetime.fromtimestamp(commit.author.timestamp)
    console.print(f"[yellow]commit {oid}[/]")
    console.print(f"Author: {commit.author.name} <{commit.author.email}>")
    if commit.agent:
        console.print(f"Agent:  [magenta]{commit.agent}[/]")
    console.print(f"Date:   {dt.strftime('%a %b %d %H:%M:%S %Y')}\n")
    console.print(f"    {commit.message}")

    if stat and commit.parents:
        console.print("\n  --stat is not yet implemented for show--")
