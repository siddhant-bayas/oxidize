from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.text import Text

from oxidize.core.repository import Repository, RepositoryNotFound
from oxidize.diff.engine import LineOp, diff_lines
from oxidize.semantic.differ import format_semantic_diff, semantic_diff
from oxidize.semantic.parser import detect_language

console = Console()


@click.command("diff")
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
@click.option("--cached", is_flag=True, help="Show staged changes (index vs HEAD)")
@click.option("--semantic", is_flag=True, help="Show entity-level semantic changes")
def cmd_diff(paths: tuple[str, ...], cached: bool, semantic: bool) -> None:
    """Show changes between working tree and index (or staged vs HEAD)."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    if cached:
        _diff_cached(repo, paths, semantic)
    else:
        _diff_working(repo, paths, semantic)


def _diff_working(repo: Repository, paths: tuple[str, ...], semantic: bool = False) -> None:
    indexed = {e.path: e for e in repo.index.entries()}

    if indexed:
        files = _resolve_paths(repo, paths, indexed)
        for rel in sorted(files):
            entry = indexed.get(rel)
            if entry is None:
                continue
            disk = repo.work_tree / rel
            if not disk.exists():
                console.print(f"[red]deleted: {rel}[/]")
                continue
            new_text = disk.read_text(errors="replace").replace("\r\n", "\n")
            from oxidize import lfs

            old_text = lfs.load_blob_data(repo, entry.oid).decode(errors="replace").replace("\r\n", "\n")
            if old_text == new_text:
                continue
            _print_diff(rel, old_text, new_text, semantic)
        return

    head = repo.refs.head()
    if not head:
        console.print("[dim]no commits yet[/]")
        return

    commit = repo.db.load_commit(head)
    head_files: dict[str, str] = {}
    _collect_head_files(repo, commit.tree_oid, "", head_files)

    if paths:
        files = set()
        for raw in paths:
            p = Path(raw).resolve()
            if p.is_dir():
                for f in p.rglob("*"):
                    if f.is_file():
                        rel = f.relative_to(repo.work_tree).as_posix()
                        files.add(rel)
            else:
                files = {p.relative_to(repo.work_tree).as_posix()}
    else:
        files = set(head_files.keys())
        for p in repo.ignore_matcher.filter([*repo.work_tree.rglob("*")]):
            if p.is_file():
                rel = p.relative_to(repo.work_tree).as_posix()
                files.add(rel)

    for rel in sorted(files):
        head_oid = head_files.get(rel)
        disk = repo.work_tree / rel
        if not disk.exists():
            console.print(f"[red]deleted: {rel}[/]")
            continue
        if head_oid is None:
            continue
        new_text = disk.read_text(errors="replace").replace("\r\n", "\n")
        from oxidize import lfs

        old_text = lfs.load_blob_data(repo, head_oid).decode(errors="replace").replace("\r\n", "\n")
        if old_text == new_text:
            continue
        _print_diff(rel, old_text, new_text, semantic)


def _diff_cached(repo: Repository, paths: tuple[str, ...], semantic: bool = False) -> None:
    head = repo.refs.head()
    if not head:
        console.print("[dim]no commits yet[/]")
        return

    commit = repo.db.load_commit(head)
    head_files: dict[str, str] = {}
    _collect_head_files(repo, commit.tree_oid, "", head_files)

    indexed = {e.path: e for e in repo.index.entries()}
    files = _resolve_paths(repo, paths, indexed)

    for rel in sorted(files):
        entry = indexed.get(rel)
        head_oid = head_files.get(rel)
        if entry and not head_oid:
            console.print(f"[green]new file: {rel}[/]")
        elif not entry and head_oid:
            console.print(f"[red]deleted: {rel}[/]")
        elif entry and head_oid:
            from oxidize import lfs

            old_blob_data = lfs.load_blob_data(repo, head_oid)
            new_blob_data = lfs.load_blob_data(repo, entry.oid)
            old_blob = type("B", (), {"data": old_blob_data})()
            new_blob = type("B", (), {"data": new_blob_data})()
            if old_blob.data != new_blob.data:
                _print_diff(
                    rel,
                    old_blob.data.decode(errors="replace"),
                    new_blob.data.decode(errors="replace"),
                    semantic,
                )


def _resolve_paths(
    repo: Repository, paths: tuple[str, ...], indexed: Mapping[str, Any]
) -> set[str]:
    if paths:
        result: set[str] = set()
        for raw in paths:
            p = Path(raw).resolve()
            if p.is_dir():
                for f in p.rglob("*"):
                    rel = f.relative_to(repo.work_tree).as_posix()
                    if rel in indexed:
                        result.add(rel)
            else:
                rel = p.relative_to(repo.work_tree).as_posix()
                result.add(rel)
        return result
    return set(indexed.keys())



def _collect_head_files(repo: Repository, tree_oid: str, prefix: str, out: dict[str, str]) -> None:
    from oxidize.objects.types import FileMode

    tree = repo.db.load_tree(tree_oid)
    for te in tree:
        path = f"{prefix}/{te.name}" if prefix else te.name
        if te.mode == FileMode.DIRECTORY:
            _collect_head_files(repo, te.oid, path, out)
        else:
            out[path] = te.oid


def _print_diff(path: str, old: str, new: str, semantic: bool = False) -> None:
    console.print(f"\n[bold]diff --a/a b/{path}[/]")
    if semantic:
        language = detect_language(path)
        changes = semantic_diff(old, new, language=language)
        console.print(format_semantic_diff(changes))
        return
    diff_result = diff_lines(old, new)
    for dl in diff_result:
        if dl.op == LineOp.EQUAL:
            console.print(f" {dl.content}", end="")
        elif dl.op == LineOp.INSERT:
            line = Text(f"+{dl.content}")
            line.stylize("green")
            console.print(line, end="")
        elif dl.op == LineOp.DELETE:
            line = Text(f"-{dl.content}")
            line.stylize("red")
            console.print(line, end="")
    if diff_result and not diff_result[-1].content.endswith("\n"):
        console.print()
