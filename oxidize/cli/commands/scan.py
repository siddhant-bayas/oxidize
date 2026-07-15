from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from oxidize.core.repository import Repository, RepositoryNotFound
from oxidize.security.scanner import scan_directory, scan_file

console = Console()


@click.command("scan")
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
@click.option("--staged", is_flag=True, help="Scan only staged files")
def cmd_scan(paths: tuple[str, ...], staged: bool) -> None:
    """Scan for secrets and credentials."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    findings: list[dict[str, str | int]] = []

    if staged:
        for entry in repo.index.entries():
            full = repo.work_tree / entry.path
            if full.exists():
                findings.extend(scan_file(full, repo.work_tree))
    elif paths:
        for raw in paths:
            p = Path(raw).resolve()
            if p.is_dir():
                findings.extend(scan_directory(p))
            else:
                findings.extend(scan_file(p, repo.work_tree))
    else:
        findings.extend(scan_directory(repo.work_tree))

    if not findings:
        console.print("[green]No secrets found.[/]")
        return

    console.print(f"\n[red bold]Found {len(findings)} potential secret(s):[/]\n")
    for f in findings:
        console.print(
            f"  [yellow]{f['type']}[/] in [cyan]{f['file']}[/] line {f['line']}: {f['match']}"
        )
    console.print()
