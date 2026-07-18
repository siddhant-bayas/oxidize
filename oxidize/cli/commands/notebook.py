from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.syntax import Syntax

from oxidize.core.repository import Repository, RepositoryNotFound
from oxidize.notebook.differ import NotebookDiffer
from oxidize.objects.types import Tree

console = Console()


@click.command("notebook-diff")
@click.argument("old")
@click.argument("new")
@click.option("--render", is_flag=True, help="Pretty-print each cell with side-by-side code")
def cmd_notebook_diff(old: str, new: str, render: bool) -> None:
    """Compare two Jupyter notebooks cell-by-cell."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    old_path = _resolve(repo, old)
    new_path = _resolve(repo, new)
    if old_path is None or new_path is None:
        raise click.ClickException("could not resolve notebook paths")

    diffs = NotebookDiffer.diff_cells(old_path, new_path)

    if not render:
        diff_summary: dict[str, str] = {}
        for d in diffs:
            diff_summary[str(d["cell"])] = str(d.get("summary", ""))
        for d in diffs:
            cell_key = str(d["cell"])
            cell_no = cell_key
            kind = d["type"]
            summary = diff_summary[cell_key]
            kind_key = str(d["type"])
            color = {"added": "green", "deleted": "red", "modified": "yellow", "unchanged": "dim"}[
                kind_key
            ]
            console.print(f"  [bold]cell {cell_no}[/] [{color}]{kind}[/]")
            if kind == "modified":
                console.print(f"    [yellow]{summary}[/]")
            elif kind in ("added", "deleted"):
                console.print(Syntax(summary, "python", theme="monokai", word_wrap=True))
            else:
                console.print(f"    [dim]{summary}[/]")
        console.print(f"\n[dim]{len(diffs)} cells compared[/]")
        return

    for d in diffs:
        if d["type"] == "unchanged":
            continue
        console.rule(f"cell {d['cell']} [{d['type']}]")
        if d["type"] in ("added", "deleted"):
            code = str(d.get("summary", ""))
            syntax = Syntax(code, "python", theme="monokai", word_wrap=True)
            console.print(syntax)


def _resolve(repo: Repository, raw: str) -> Path | None:
    p = Path(raw)
    if p.exists():
        return p
    head = repo.refs.head() or ""
    if not head:
        return None
    try:
        commit = repo.db.load_commit(head)
        tree: Tree = repo.db.load_tree(commit.tree_oid)
    except Exception:
        return None
    rel = raw
    sub: list[str] = rel.split("/")
    return _walk_tree(repo, tree, sub, [])


def _walk_tree(
    repo: Repository,
    tree: Tree,
    parts: list[str],
    parents: list[str],
) -> Path | None:
    if not parts:
        return None
    for entry in tree:
        if entry.name == parts[0]:
            if len(parts) == 1:
                if entry.mode.value == "040000":
                    return None
                try:
                    blob = repo.db.load_blob(entry.oid)
                except Exception:
                    return None
                target = repo.work_tree / "/".join(parents + [entry.name])
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(blob.data)
                return target
            if entry.mode.value != "040000":
                return None
            try:
                subtree: Tree = repo.db.load_tree(entry.oid)
            except Exception:
                return None
            return _walk_tree(repo, subtree, parts[1:], parents + [entry.name])
    return None
