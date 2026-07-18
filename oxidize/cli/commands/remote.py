from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from oxidize.core.repository import Repository, RepositoryNotFound
from oxidize.network.remote import Remote, TransferError

console = Console()


@click.group()
def cmd_remote() -> None:
    """Manage remotes."""


@cmd_remote.command("clone")
@click.argument("url")
@click.argument("target", required=False, default=".")
def cmd_remote_clone(url: str, target: str) -> None:
    """Clone a remote (filesystem URL like file:///path) into a target directory."""
    try:
        Remote(url).clone(Path(target).resolve())
    except TransferError as e:
        raise click.ClickException(str(e))
    click.echo(f"cloned {url} -> {target}")


@cmd_remote.command("push")
@click.argument("url")
@click.argument("branch", required=False, default=None)
@click.option("--force", "-f", is_flag=True, help="Overwrite divergent refs")
def cmd_remote_push(url: str, branch: str | None, force: bool) -> None:
    """Push the current branch (or named branch) to a filesystem remote."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))
    try:
        pushed = Remote(url).push(repo, branch=branch, force=force)
    except TransferError as e:
        raise click.ClickException(str(e))
    for b in pushed:
        click.echo(f"  -> {url}::{b}")


@cmd_remote.command("pull")
@click.argument("url")
@click.argument("branch", required=False, default=None)
def cmd_remote_pull(url: str, branch: str | None) -> None:
    """Pull named branches from a filesystem remote."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))
    try:
        pulled = Remote(url).pull(repo, branch=branch)
    except TransferError as e:
        raise click.ClickException(str(e))
    for b in pulled:
        click.echo(f"  <- {url}::{b}")
    if not pulled:
        click.echo("nothing to pull (already up to date)")
