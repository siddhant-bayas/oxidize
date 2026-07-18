from __future__ import annotations

import os
from collections import defaultdict

import click

from oxidize.core.repository import Repository, RepositoryNotFound
from oxidize.objects.types import Author, Commit, FileMode, Tree, TreeEntry
from oxidize.undo.reverser import UndoManager


def _build_tree(repo: Repository) -> Tree:
    entries_by_dir: dict[str, list[tuple[str, str, FileMode]]] = defaultdict(list)
    for entry in repo.index.entries():
        parts = entry.path.split("/")
        if len(parts) == 1:
            entries_by_dir[""].append((parts[0], entry.oid, FileMode(entry.mode)))
        else:
            dir_name = parts[0]
            file_name = parts[-1]
            entries_by_dir[dir_name].append((file_name, entry.oid, FileMode(entry.mode)))

    subtrees: dict[str, str] = {}
    for dir_name, dir_entries in entries_by_dir.items():
        if dir_name and len(dir_entries) == 1 and dir_entries[0][0] == "__subtree__":
            continue
        if not dir_name:
            continue
        sub_tree = Tree()
        for fname, foid, fmode in dir_entries:
            sub_tree.add(TreeEntry(name=fname, oid=foid, mode=fmode))
        repo.db.store_tree(sub_tree)
        subtrees[dir_name] = sub_tree.oid

    root = Tree()
    for fname, foid, fmode in entries_by_dir.get("", []):
        root.add(TreeEntry(name=fname, oid=foid, mode=fmode))
    for dir_name, subtree_oid in sorted(subtrees.items()):
        root.add(TreeEntry(name=dir_name, oid=subtree_oid, mode=FileMode.DIRECTORY))
    return root


@click.command("commit")
@click.option("-m", "--message", required=True, help="Commit message")
@click.option("--agent", default=None, help="Agent that produced this change (e.g. claude-code)")
def cmd_commit(message: str, agent: str | None = None) -> None:
    """Record staged changes as a new commit."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    if len(repo.index) == 0:
        raise click.ClickException("nothing staged -- use `oxidize add` first")

    name = os.environ.get("OXIDE_AUTHOR_NAME") or repo.config.user_name
    email = os.environ.get("OXIDE_AUTHOR_EMAIL") or repo.config.user_email
    author = Author(name=name, email=email)

    tree = _build_tree(repo)
    repo.db.store_tree(tree)

    parents: list[str] = []
    head = repo.refs.head()
    prev_head = head
    if head:
        parents.append(head)

    commit = Commit(
        tree_oid=tree.oid,
        author=author,
        committer=author,
        message=message,
        parents=parents,
        agent=agent,
    )
    repo.db.store_commit(commit)
    repo.refs.update_head(commit.oid)
    repo.index.clear()

    undo_mgr = UndoManager(repo)
    undo_mgr.record_commit(commit.oid, prev_head, message)

    short = commit.oid[:8]
    branch = repo.refs.current_branch() or "HEAD"
    agent_str = f" [{agent}]" if agent else ""
    click.echo(f"[{branch} {short}]{agent_str} {message}")
