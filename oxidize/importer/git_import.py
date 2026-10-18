from __future__ import annotations

import subprocess
from pathlib import Path

from oxidize.core.repository import Repository
from oxidize.objects.types import Author, Commit, FileMode, Tree, TreeEntry


class GitImportError(Exception):
    pass


def _run_git(source: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(source), *args],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise GitImportError(result.stderr.decode(errors="replace").strip())
    return result.stdout


def _import_tree(source: Path, git_tree_sha: str, repo: Repository, cache: dict[str, str]) -> str:
    if git_tree_sha in cache:
        return cache[git_tree_sha]
    out = _run_git(source, "ls-tree", git_tree_sha)
    tree = Tree()
    for line in out.decode(errors="replace").splitlines():
        if not line.strip():
            continue
        meta, name = line.split("\t", 1)
        parts = meta.split()
        if len(parts) != 3:
            continue
        mode_str, obj_type, oid = parts
        if obj_type == "blob":
            data = _run_git(source, "cat-file", "-p", oid)
            ox_oid = repo.db.store_blob(data)
            tree.add(TreeEntry(name=name, oid=ox_oid, mode=FileMode(mode_str)))
        elif obj_type == "tree":
            child_oid = _import_tree(source, oid, repo, cache)
            tree.add(TreeEntry(name=name, oid=child_oid, mode=FileMode.DIRECTORY))
        # submodules (commit type) are skipped
    repo.db.store_tree(tree)
    cache[git_tree_sha] = tree.oid
    return tree.oid


def import_git(source: Path, repo: Repository) -> dict[str, str]:
    source = source.resolve()
    try:
        _run_git(source, "rev-parse", "--is-inside-work-tree")
    except GitImportError as exc:
        raise GitImportError(f"not a git repository: {source}") from exc

    raw = _run_git(
        source,
        "log",
        "--reverse",
        "--format=%H%x1f%P%x1f%an%x1f%ae%x1f%at%x1f%B%x1e",
        "--all",
    ).decode(errors="replace")

    commit_map: dict[str, str] = {}
    tree_cache: dict[str, str] = {}

    for record in raw.split("\x1e"):
        record = record.strip("\n")
        if not record.strip():
            continue
        parts = record.split("\x1f", 5)
        if len(parts) < 6:
            continue
        sha, parents_str, name, email, ts, message = parts
        parents = parents_str.split()

        git_tree_sha = _run_git(source, "rev-parse", f"{sha}^{{tree}}").decode().strip()
        ox_tree_oid = _import_tree(source, git_tree_sha, repo, tree_cache)

        ox_parents = [commit_map[p] for p in parents if p in commit_map]
        try:
            timestamp = int(ts)
        except ValueError:
            timestamp = 0
        author = Author(name=name, email=email, timestamp=timestamp)
        commit = Commit(
            tree_oid=ox_tree_oid,
            author=author,
            committer=author,
            message=message.rstrip("\n"),
            parents=ox_parents,
        )
        repo.db.store_commit(commit)
        commit_map[sha] = commit.oid

    # import branches
    try:
        refs_out = _run_git(
            source, "for-each-ref", "refs/heads", "--format=%(refname:short) %(objectname)"
        ).decode(errors="replace")
    except GitImportError:
        refs_out = ""
    for line in refs_out.splitlines():
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) != 2:
            continue
        branch_name, sha = parts
        if sha not in commit_map:
            continue
        ref_path = repo.oxidize_dir / "refs" / "heads" / branch_name
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        ref_path.write_text(commit_map[sha] + "\n")

    # set HEAD
    try:
        head_ref = _run_git(source, "symbolic-ref", "HEAD").decode().strip()
        branch_name = head_ref.split("/")[-1]
    except GitImportError:
        branch_name = "main"
    try:
        head_sha_proc = _run_git(source, "rev-parse", "HEAD").decode().strip()
    except GitImportError:
        head_sha_proc = ""
    if head_sha_proc in commit_map:
        repo.refs.set_head_branch(branch_name)
        (repo.oxidize_dir / "HEAD").write_text(f"ref: refs/heads/{branch_name}\n")
        ref_path = repo.oxidize_dir / "refs" / "heads" / branch_name
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        ref_path.write_text(commit_map[head_sha_proc] + "\n")

    # populate working tree from HEAD
    if head_sha_proc in commit_map:
        head_commit = repo.db.load_commit(commit_map[head_sha_proc])
        head_tree = repo.db.load_tree(head_commit.tree_oid)
        _write_tree(repo, head_tree, repo.work_tree)

    return commit_map


def _write_tree(repo: Repository, tree: Tree, root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for entry in tree:
        target = root / entry.name
        if entry.mode.value == "040000":
            child = repo.db.load_tree(entry.oid)
            _write_tree(repo, child, target)
        else:
            try:
                from oxidize import lfs

                data = lfs.load_blob_data(repo, entry.oid)
            except KeyError:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
