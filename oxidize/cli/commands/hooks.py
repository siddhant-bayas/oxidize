from __future__ import annotations

import click
from rich.console import Console

from oxidize.core.repository import Repository, RepositoryNotFound
from oxidize.workflow.hooks import Hooks

console = Console()


_HOOK_NAMES = (
    "pre-commit",
    "post-commit",
    "pre-add",
    "post-add",
    "pre-merge",
    "post-merge",
)


@click.group()
def cmd_hooks() -> None:
    """Manage repository hooks."""


@cmd_hooks.command("list")
def cmd_hooks_list() -> None:
    """List installed hooks."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    installed = Hooks(repo).list_hooks()
    for name in _HOOK_NAMES:
        path = installed.get(name)
        marker = "[green]✓[/]" if path else "[dim]--[/]"
        target = path or (repo.oxidize_dir / "hooks" / name)
        console.print(f"  {marker} [cyan]{name:<14}[/]  {target}")


@cmd_hooks.command("install")
@click.argument("name")
def cmd_hooks_install(name: str) -> None:
    """Install a starter hook script."""
    if name not in _HOOK_NAMES:
        raise click.ClickException(f"unknown hook: {name}; one of: {', '.join(_HOOK_NAMES)}")
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))
    path = Hooks(repo).install_template(name)
    click.echo(f"installed {name} at {path}")


@cmd_hooks.command("run")
@click.argument("name")
@click.argument("args", nargs=-1)
def cmd_hooks_run(name: str, args: tuple[str, ...]) -> None:
    """Run a hook manually (pass arbitrary args)."""
    if name not in _HOOK_NAMES:
        raise click.ClickException(f"unknown hook: {name}; one of: {', '.join(_HOOK_NAMES)}")
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))
    result = Hooks(repo).run(name, args)
    if result.stdout:
        click.echo(result.stdout, nl=False)
    if result.stderr:
        click.echo(result.stderr, nl=False)
    raise click.exceptions.Exit(result.exit_code)
