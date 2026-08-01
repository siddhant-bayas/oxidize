from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from oxidize.core.repository import Repository, RepositoryNotFound
from oxidize.network.github_remote import GitHubRemote, parse_github_url
from oxidize.network.remote import Remote, TransferError

console = Console()


def _make_remote(url: str) -> tuple[Remote | GitHubRemote, str]:
    gh = parse_github_url(url)
    if gh:
        return GitHubRemote(gh[0], gh[1]), "github"
    return Remote(url), "filesystem"


@click.group()
def cmd_remote() -> None:
    """Manage remotes."""


@cmd_remote.command("clone")
@click.argument("url")
@click.argument("target", required=False, default=".")
def cmd_remote_clone(url: str, target: str) -> None:
    """Clone a filesystem remote into a target directory."""
    remote, kind = _make_remote(url)
    if kind == "github":
        raise click.ClickException(
            "Clone from GitHub is not supported yet. "
            "Use `git clone` or `oxidize remote push` to export."
        )
    assert isinstance(remote, Remote)
    try:
        remote.clone(Path(target).resolve())
    except TransferError as e:
        raise click.ClickException(str(e))
    click.echo(f"cloned {url} -> {target}")


@cmd_remote.command("push")
@click.argument("url")
@click.argument("branch", required=False, default=None)
@click.option("--force", "-f", is_flag=True, help="Overwrite divergent refs")
def cmd_remote_push(url: str, branch: str | None, force: bool) -> None:
    """Push the current branch (or named branch) to a remote."""
    remote, _kind = _make_remote(url)
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))
    try:
        pushed = remote.push(repo, branch=branch, force=force)
    except TransferError as e:
        raise click.ClickException(str(e))
    for b in pushed:
        click.echo(f"  -> {url}::{b}")


@cmd_remote.command("pull")
@click.argument("url")
@click.argument("branch", required=False, default=None)
def cmd_remote_pull(url: str, branch: str | None) -> None:
    """Pull named branches from a remote."""
    remote, kind = _make_remote(url)
    if kind == "github":
        raise click.ClickException("Pull from GitHub is not supported yet (push-only for v1).")
    assert isinstance(remote, Remote)
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))
    try:
        pulled = remote.pull(repo, branch=branch)
    except TransferError as e:
        raise click.ClickException(str(e))
    for b in pulled:
        click.echo(f"  <- {url}::{b}")
    if not pulled:
        click.echo("nothing to pull (already up to date)")
