from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from oxidize.core.repository import Repository, RepositoryNotFound
from oxidize.security.scanner import scan_directory, scan_file, scan_paths

console = Console()


@click.command("scan")
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
@click.option("--staged", is_flag=True, help="Scan only staged files")
@click.option("--no-oxignore", "respect_ignore", is_flag=True, default=False, help="Skip .oxignore filtering")
def cmd_scan(paths: tuple[str, ...], staged: bool, respect_ignore: bool) -> None:
    """Scan for secrets and credentials (.oxignore rules apply)."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    matcher = None if respect_ignore else repo.ignore_matcher

    findings: list[dict[str, str | int]] = []

    if staged:
        for entry in repo.index.entries():
            full = repo.work_tree / entry.path
            if full.exists():
                is_ignored = matcher.is_ignored(entry.path) if matcher else False
                findings.extend(scan_file(full, repo.work_tree, is_ignored=is_ignored))
    elif paths:
        targets: list[Path] = []
        for raw in paths:
            targets.append(Path(raw).resolve())
        findings.extend(scan_paths(targets, repo.work_tree, matcher))
    else:
        findings.extend(scan_directory(repo.work_tree, matcher))

    if not findings:
        console.print("[green]No secrets found.[/]")
        return

    console.print(f"\n[red bold]Found {len(findings)} potential secret(s):[/]\n")
    for f in findings:
        console.print(
            f"  [yellow]{f['type']}[/] in [cyan]{f['file']}[/] line {f['line']}: {f['match']}"
        )
    console.print()
