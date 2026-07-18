from __future__ import annotations


import click
from rich.console import Console

from oxidize.core.repository import Repository, RepositoryNotFound
from oxidize.merge.text import three_way_text_merge
from oxidize.merge.treewalk import _blob_text, _find_merge_base

console = Console()


@click.command("merge")
@click.argument("branch")
@click.option(
    "--no-commit", is_flag=True, help="Leave conflicts in the working tree without committing"
)
def cmd_merge(branch: str, no_commit: bool) -> None:
    """Merge a branch into the current branch."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    current = repo.refs.current_branch()
    if not current:
        raise click.ClickException("not on any branch; cannot merge")
    ours_commit = repo.refs.read(f"refs/heads/{current}") or ""
    theirs_commit = repo.refs.read(branch) or repo.refs.read(f"refs/heads/{branch}")
    if not theirs_commit:
        raise click.ClickException(f"branch '{branch}' not found")
    if ours_commit == theirs_commit:
        click.echo("Already up to date.")
        return

    ours_oid = repo.db.load_commit(ours_commit).tree_oid
    theirs_oid = repo.db.load_commit(theirs_commit).tree_oid
    base_commit = _find_merge_base(repo, ours_commit, theirs_commit)
    base_oid = repo.db.load_commit(base_commit).tree_oid if base_commit else ""

    conflicts: list[str] = []
    auto_merged = 0
    succeeded: dict[str, str] = {}

    paths: set[str] = set()
    if base_oid:
        paths.update(_enumerate_paths(repo, base_oid))
    paths.update(_enumerate_paths(repo, ours_oid))
    paths.update(_enumerate_paths(repo, theirs_oid))

    for rel in sorted(paths):
        base_text, b_existed = _blob_text(repo, base_oid, rel) if base_oid else ("", False)
        ours_text, o_existed = _blob_text(repo, ours_oid, rel)
        theirs_text, t_existed = _blob_text(repo, theirs_oid, rel)

        if not b_existed:
            base_text = ours_text or ""

        eff_ours_text = ours_text if o_existed else base_text
        eff_theirs_text = theirs_text if t_existed else base_text

        if o_existed == t_existed and ours_text == theirs_text:
            continue

        result = three_way_text_merge(base_text or "", eff_ours_text or "", eff_theirs_text or "")

        target = repo.work_tree / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.merged, encoding="utf-8")

        if result.conflicted:
            conflicts.append(rel)
        else:
            auto_merged += 1

        succeeded[rel] = result.merged

    if conflicts:
        click.echo(f"merge: conflicts in {len(conflicts)} file(s):")
        for c in conflicts:
            click.echo(f"      {c}")
        if not no_commit:
            click.echo("resolve then `oxidize resolve` and `oxidize commit -m <msg>`")
        raise click.ClickException("merge stopped at conflicts")

    click.echo(f"merged {len(succeeded)} file(s) automatically ({auto_merged} clean)")


def _enumerate_paths(repo: Repository, tree_oid: str) -> set[str]:
    paths: set[str] = set()
    _walk(repo, tree_oid, paths)
    return paths


def _walk(repo: Repository, tree_oid: str, paths: set[str], prefix: str = "") -> None:
    try:
        tree = repo.db.load_tree(tree_oid)
    except Exception:
        return
    for entry in tree:
        rel = f"{prefix}/{entry.name}" if prefix else entry.name
        if entry.mode.value == "040000":
            _walk(repo, entry.oid, paths, rel)
        else:
            paths.add(rel)
