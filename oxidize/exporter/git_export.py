from __future__ import annotations

import subprocess
from pathlib import Path

from oxidize.core.repository import Repository


class GitExportError(Exception):
    pass


def _run_git(cwd: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, check=False)
    if result.returncode != 0:
        raise GitExportError(result.stderr.decode(errors="replace").strip())
    return result.stdout


def export_git(repo: Repository, target: Path) -> int:
    target = target.resolve()
    target.mkdir(parents=True, exist_ok=True)
    # init git repo if needed
    if not (target / ".git").exists():
        _run_git(target, "init", "-q")
    _run_git(
        target,
        "config",
        "user.email",
        repo.db.load_commit(repo.refs.head() or "").author.email
        if repo.refs.head()
        else "oxidize@example.com",
    )
    _run_git(
        target,
        "config",
        "user.name",
        repo.db.load_commit(repo.refs.head() or "").author.name if repo.refs.head() else "oxidize",
    )

    head_oid = repo.refs.head()
    if not head_oid:
        return 0

    # collect commits reachable from HEAD in topo order (parents first)
    all_commits: set[str] = set()
    stack = [head_oid]
    while stack:
        oid = stack.pop()
        if oid in all_commits:
            continue
        all_commits.add(oid)
        try:
            c = repo.db.load_commit(oid)
        except KeyError:
            continue
        stack.extend(c.parents)

    # topo sort: parents before children
    ordered: list[str] = []
    visited: set[str] = set()

    def visit(oid: str) -> None:
        if oid in visited:
            return
        visited.add(oid)
        try:
            c = repo.db.load_commit(oid)
        except KeyError:
            return
        for p in c.parents:
            visit(p)
        ordered.append(oid)

    visit(head_oid)

    # marks
    commit_mark: dict[str, int] = {}
    next_mark = 1

    lines: list[str] = []

    for oid in ordered:
        c = repo.db.load_commit(oid)
        # tree -> file entries
        tree_entries: list[tuple[str, str, str]] = []

        def walk(tree_oid: str, prefix: str, acc: list[tuple[str, str, str]]) -> None:
            try:
                tree = repo.db.load_tree(tree_oid)
            except KeyError:
                return
            for e in tree:
                path = f"{prefix}/{e.name}" if prefix else e.name
                if e.mode.value == "040000":
                    walk(e.oid, path, acc)
                else:
                    acc.append((path, e.mode.value, e.oid))

        walk(c.tree_oid, "", tree_entries)
        m = next_mark
        next_mark += 1
        commit_mark[oid] = m
        lines.append(f"commit refs/heads/main\nmark :{m}\n")
        # author/committer
        author = c.author
        committer = c.committer
        lines.append(f"author {author.name} <{author.email}> {author.timestamp} +0000\n")
        lines.append(
            f"committer {committer.name} <{committer.email}> {committer.timestamp} +0000\n"
        )
        msg = c.message
        lines.append(f"data {len(msg.encode())}\n{msg}\n")
        if c.parents:
            for p in c.parents:
                if p in commit_mark:
                    lines.append(f"from :{commit_mark[p]}\n")
                    break
            # additional parents
            for p in c.parents[1:]:
                if p in commit_mark:
                    lines.append(f"merge :{commit_mark[p]}\n")
        for path, mode, blob_oid in tree_entries:
            git_mode = mode
            try:
                blob = repo.db.load_blob(blob_oid)
                data = blob.data
            except KeyError:
                data = b""
            try:
                from oxidize import lfs

                data = lfs.resolve_data(repo, data)
            except Exception:
                pass
            lines.append(f"M {git_mode} inline {path}\n")
            lines.append(f"data {len(data)}\n")
            lines.append(data.decode("latin-1"))
            if not data.endswith(b"\n"):
                lines.append("\n")
        lines.append("\n")

    stream = "".join(lines).encode("latin-1")
    proc = subprocess.run(
        ["git", "-C", str(target), "fast-import", "--quiet"],
        input=stream,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise GitExportError(proc.stderr.decode(errors="replace").strip())

    # fast-import leaves refs/heads/main at last commit already
    _run_git(target, "reset", "--hard", "main")
    return len(ordered)
