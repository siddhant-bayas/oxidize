from __future__ import annotations

import click
from rich.console import Console

from oxidize.core.repository import Repository, RepositoryNotFound
from oxidize.workflow.bisect import BisectState, midpoint

console = Console()


@click.group(invoke_without_command=True)
@click.pass_context
def cmd_bisect(ctx: click.Context) -> None:
    """Find a regression by binary search."""
    if ctx.invoked_subcommand is None:
        try:
            repo = Repository.discover()
        except RepositoryNotFound as e:
            raise click.ClickException(str(e))
        state = BisectState(repo.oxidize_dir / "bisect.json")
        status = state.status()
        if not status:
            click.echo("no bisect session; try `oxidize bisect start`")
            return
        console.print("current session:")
        for k, v in status.items():
            console.print(f"  [dim]{k}[/]: {v}")


@cmd_bisect.command("start")
@click.argument("good", required=False, default="")
@click.argument("bad", required=False, default="")
def cmd_bisect_start(good: str, bad: str) -> None:
    """Start a bisect session. Optionally provide GOOD and BAD commits."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    state = BisectState(repo.oxidize_dir / "bisect.json")
    state.reset()

    if good and bad:
        good_oid = repo.refs.read(good) or good
        bad_oid = repo.refs.read(bad) or bad
        state.start(good_oid, bad_oid)
        click.echo(
            f"check out: {midpoint(repo, good_oid, bad_oid)} then run `oxidize bisect good` or `oxidize bisect bad`"
        )
    else:
        click.echo("bisect armed; run `oxidize bisect bad HEAD`, then `oxidize bisect good <ref>`")


@cmd_bisect.command("good")
@click.argument("ref", required=False, default="HEAD")
def cmd_bisect_good(ref: str) -> None:
    """Mark the current commit (or ref) as good."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))
    state = BisectState(repo.oxidize_dir / "bisect.json")
    oid = repo.refs.read(ref) or ref
    result = state.mark("good", oid)
    if result.get("done"):
        click.echo(f"FOUND regression: {result['found']}")
    else:
        click.echo(f"check out: {result['next']}")


@cmd_bisect.command("bad")
@click.argument("ref", required=False, default="HEAD")
def cmd_bisect_bad(ref: str) -> None:
    """Mark the current commit (or ref) as bad."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))
    state = BisectState(repo.oxidize_dir / "bisect.json")
    oid = repo.refs.read(ref) or ref
    result = state.mark("bad", oid)
    if result.get("done"):
        click.echo(f"FOUND regression: {result['found']}")
    else:
        click.echo(f"check out: {result['next']}")


@cmd_bisect.command("reset")
def cmd_bisect_reset() -> None:
    """End the bisect session."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))
    BisectState(repo.oxidize_dir / "bisect.json").reset()
    click.echo("bisect reset")
