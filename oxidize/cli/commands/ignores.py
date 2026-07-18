from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from oxidize.core.repository import Repository, RepositoryNotFound

console = Console()


@click.group("ignores")
def cmd_ignores() -> None:
    """Inspect and test .oxignore rules."""


@cmd_ignores.command("list")
def cmd_ignores_list() -> None:
    """Show all effective ignore patterns."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    matcher = repo.ignore_matcher
    patterns = matcher.patterns()
    builtins = matcher.builtin_patterns()

    if builtins:
        console.print("[bold]builtins (always active):[/]")
        for b in builtins:
            console.print(f"  [dim]{b}[/]")
        console.print()

    if patterns:
        console.print("[bold].oxignore patterns:[/]")
        for p in patterns:
            console.print(f"  {p}")
    else:
        console.print("[dim]no .oxignore file found -- only builtins apply[/]")


@cmd_ignores.command("check")
@click.argument("targets", nargs=-1, required=True, type=click.Path(exists=True))
def cmd_ignores_check(targets: tuple[str, ...]) -> None:
    """Test whether paths are ignored. Exits 1 if any path is ignored."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    matcher = repo.ignore_matcher
    any_ignored = False

    for raw in targets:
        p = Path(raw).resolve()
        try:
            rel = p.relative_to(repo.work_tree).as_posix()
        except ValueError:
            console.print(f"  [red]error[/]: {raw} is outside the working tree")
            any_ignored = True
            continue

        if matcher.is_ignored(rel):
            console.print(f"  [yellow]{rel}[/]: ignored")
            any_ignored = True
        else:
            console.print(f"  [green]{rel}[/]: tracked")

    if any_ignored:
        raise click.exceptions.Exit(1)
