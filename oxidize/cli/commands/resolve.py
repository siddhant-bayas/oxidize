from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.prompt import Confirm, Prompt

from oxidize.core.repository import Repository, RepositoryNotFound
from oxidize.merge.text import is_conflict

console = Console()


_CONFLICT_PATTERN = [
    "<<<<<<< OURS",
    "||||||| BASE",
    "======= THEIRS",
    ">>>>>>> THEIRS",
]


@click.command("resolve")
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
@click.option("--all", "resolve_all", is_flag=True, help="Resolve every file with conflict markers")
@click.option("-t", "--theirs", "take_theirs", is_flag=True, help="Take theirs for every conflict")
@click.option("-o", "--ours", "take_ours", is_flag=True, help="Take ours for every conflict")
def cmd_resolve(
    paths: tuple[str, ...], resolve_all: bool, take_theirs: bool, take_ours: bool
) -> None:
    """Interactively resolve merge conflicts."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    if take_ours and take_theirs:
        raise click.ClickException("pick at most one of --ours / --theirs")

    targets: list[Path] = []
    if resolve_all:
        for p in repo.work_tree.rglob("*"):
            if p.is_file() and p.suffix in {
                ".txt",
                ".py",
                ".md",
                ".json",
                ".yml",
                ".yaml",
                ".toml",
                ".cfg",
                ".ini",
            }:
                try:
                    text = p.read_text(encoding="utf-8", errors="replace")
                except UnicodeDecodeError:
                    continue
                if is_conflict(text):
                    targets.append(p)
    if paths:
        for raw in paths:
            targets.append(Path(raw).resolve())

    if not targets:
        click.echo("no files with conflict markers found.")
        return

    if take_ours or take_theirs:
        for p in targets:
            _take_side(p, take_theirs=take_theirs)
        click.echo(f"resolved {len(targets)} file(s). run `oxidize add` then `oxidize commit`.")
        return

    for p in targets:
        _interactive(p)


def _interactive(p: Path) -> None:
    console.print(f"\n[bold cyan]{p}[/]")
    text = p.read_text(encoding="utf-8")
    console.print(text)

    choice = Prompt.ask("  resolve", choices=["ours", "theirs", "skip", "abort"], default="ours")
    if choice == "abort":
        raise click.exceptions.Exit(1)
    if choice == "skip":
        return
    if choice == "ours":
        _take_side(p, take_theirs=False)
    else:
        _take_side(p, take_theirs=True)
    if Confirm.ask(f"  stage {p.name}?", default=True):
        p.relative_to  # touch


def _take_side(p: Path, take_theirs: bool) -> None:
    text = p.read_text(encoding="utf-8")
    lines = text.splitlines()
    out: list[str] = []
    state: str = "neutral"
    for line in lines:
        if line.startswith("<<<<<<< OURS"):
            state = "skip-ours" if take_theirs else "ours"
            continue
        if line.startswith(">>>>>>> THEIRS"):
            state = "neutral"
            continue
        if line.startswith("||||||| BASE"):
            if not take_theirs:
                state = "skip-ours"
            continue
        if line.startswith("======= THEIRS"):
            state = "neutral" if take_theirs else "skip-ours"
            continue
        if state == "ours":
            out.append(line)
        elif state == "skip-ours":
            continue
        elif state == "neutral":
            out.append(line)
    p.write_text("\n".join(out) + ("\n" if text.endswith("\n") and out else ""), encoding="utf-8")
