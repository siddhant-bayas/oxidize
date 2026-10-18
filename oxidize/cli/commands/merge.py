from __future__ import annotations

import click
from rich.console import Console

from oxidize.core.repository import Repository, RepositoryNotFound
from oxidize.merge.rename import detect_renames
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

    base_paths = _enumerate_paths(repo, base_oid) if base_oid else set()
    ours_paths = _enumerate_paths(repo, ours_oid)
    theirs_paths = _enumerate_paths(repo, theirs_oid)

    def _text(tree_oid: str, path: str) -> str:
        text, existed = _blob_text(repo, tree_oid, path)
        return text if (existed and text is not None) else ""

    ours_renames: dict[str, str] = {}
    theirs_renames: dict[str, str] = {}
    if base_oid:
        ours_renames = detect_renames(
            base_paths, ours_paths, lambda p: _text(base_oid, p), lambda p: _text(ours_oid, p)
        )
        theirs_renames = detect_renames(
            base_paths, theirs_paths, lambda p: _text(base_oid, p), lambda p: _text(theirs_oid, p)
        )

    ours_reverse = {v: k for k, v in ours_renames.items()}
    theirs_reverse = {v: k for k, v in theirs_renames.items()}

    # Build canonical merge items: (base_path or None, ours_path or None, theirs_path or None, display_path)
    items: list[tuple[str | None, str | None, str | None, str]] = []
    handled_targets: set[str] = set()

    for p in sorted(base_paths):
        op = ours_renames.get(p, p)
        tp = theirs_renames.get(p, p)
        ours_has = op in ours_paths or op in ours_renames.values()
        theirs_has = tp in theirs_paths or tp in theirs_renames.values()
        display = op if (op in ours_paths or op in ours_renames.values()) else tp
        if display is None:
            display = p
        items.append((p, op if ours_has else None, tp if theirs_has else None, display))
        handled_targets.add(display)

    # independent additions (not renames targets)
    for p in sorted(ours_paths | theirs_paths):
        if p in handled_targets:
            continue
        if p in ours_reverse or p in theirs_reverse:
            continue
        if p in base_paths:
            continue
        items.append((None, p if p in ours_paths else None, p if p in theirs_paths else None, p))
        handled_targets.add(p)

    conflicts: list[str] = []
    auto_merged = 0
    succeeded: dict[str, str] = {}

    for _bp, _op, _tp, rel in [(i[0], i[1], i[2], i[3]) for i in items]:
        base_path = _bp
        ours_path = _op
        theirs_path = _tp

        if base_path is not None:
            base_text = _text(base_oid, base_path) if base_oid else ""
            b_existed = True
        else:
            base_text = ""
            b_existed = False

        if ours_path is not None and (ours_path in ours_paths or ours_path in ours_renames.values()):
            ours_text = _text(ours_oid, ours_path)
            o_existed = True
        else:
            ours_text = None
            o_existed = False

        if theirs_path is not None and (theirs_path in theirs_paths or theirs_path in theirs_renames.values()):
            theirs_text = _text(theirs_oid, theirs_path)
            t_existed = True
        else:
            theirs_text = None
            t_existed = False

        if not b_existed:
            base_text = ours_text or theirs_text or ""

        eff_ours_text = ours_text if o_existed else base_text
        eff_theirs_text = theirs_text if t_existed else base_text

        if o_existed == t_existed and ours_text == theirs_text:
            # handle deletion on both sides: remove file
            if not o_existed and not t_existed:
                target = repo.work_tree / rel
                if target.exists():
                    target.unlink()
                continue
            continue

        result = three_way_text_merge(base_text or "", eff_ours_text or "", eff_theirs_text or "")

        target = repo.work_tree / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.merged, encoding="utf-8")

        # if renamed away, remove old path
        if base_path is not None and base_path != rel:
            old_target = repo.work_tree / base_path
            if old_target.exists() and old_target != target:
                try:
                    old_target.unlink()
                except OSError:
                    pass

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
    except KeyError:
        return
    for entry in tree:
        rel = f"{prefix}/{entry.name}" if prefix else entry.name
        if entry.mode.value == "040000":
            _walk(repo, entry.oid, paths, rel)
        else:
            paths.add(rel)
