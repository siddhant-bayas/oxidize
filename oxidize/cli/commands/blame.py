from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from oxidize.core.repository import Repository, RepositoryNotFound
from oxidize.workflow.blame import Blamer

console = Console()


@click.command("blame")
@click.argument("path")
def cmd_blame(path: str) -> None:
    """Show commit-by-commit annotation for a file."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    target = Path(path).resolve()
    try:
        rel = target.relative_to(repo.work_tree).as_posix()
    except ValueError:
        rel = path

    annotations = Blamer(repo).annotate(rel)
    if not annotations:
        click.echo(f"no history for {rel}")
        return

    history = {oid for oid, _ in annotations}
    name = _author_lookup(repo, history)

    for oid, line in annotations:
        author = name.get(oid, "?")
        when = "?       "
        console.print(f"{oid} {author:<10} {when} {line}")


def _author_lookup(repo: Repository, oids: set[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for oid in oids:
        try:
            commit = repo.db.load_commit(oid)
        except Exception:
            continue
        full = oid
        out[full[:8]] = commit.author.name.split()[0]
    return out
