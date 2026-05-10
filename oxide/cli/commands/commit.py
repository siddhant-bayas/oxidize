from __future__ import annotations

import os
from pathlib import Path

import click

from oxide.core.repository import Repository, RepositoryNotFound
from oxide.objects.types import Author, Commit, FileMode, Tree, TreeEntry


def _build_tree(repo: Repository) -> Tree:
    # Flat tree for now. TODO: recursive subtree building for nested paths.
    tree = Tree()
    for entry in repo.index.entries():
        tree.add(TreeEntry(
            name=entry.path.replace("/", "_"),  # flat: slash-to-underscore until subtree support
            oid=entry.oid,
            mode=FileMode(entry.mode),
        ))
    return tree


@click.command("commit")
@click.option("-m", "--message", required=True, help="Commit message")
def cmd_commit(message: str) -> None:
    """Record staged changes as a new commit."""
    try:
        repo = Repository.discover()
    except RepositoryNotFound as e:
        raise click.ClickException(str(e))

    if len(repo.index) == 0:
        raise click.ClickException("nothing staged — use `oxide add` first")

    name = os.environ.get("OXIDE_AUTHOR_NAME") or repo.config.user_name
    email = os.environ.get("OXIDE_AUTHOR_EMAIL") or repo.config.user_email
    author = Author(name=name, email=email)

    tree = _build_tree(repo)
    repo.db.store_tree(tree)

    parents: list[str] = []
    head = repo.refs.head()
    if head:
        parents.append(head)

    commit = Commit(
        tree_oid=tree.oid,
        author=author,
        committer=author,
        message=message,
        parents=parents,
    )
    repo.db.store_commit(commit)
    repo.refs.update_head(commit.oid)

    short = commit.oid[:8]
    branch = repo.refs.current_branch() or "HEAD"
    click.echo(f"[{branch} {short}] {message}")
