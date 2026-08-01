from __future__ import annotations

from pathlib import Path

import pytest

from oxidize.core.repository import Repository
from oxidize.objects.types import Author, Commit, FileMode, Tree, TreeEntry


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Repository:
    return Repository.init(tmp_path)


def make_commit(
    repo: Repository, files: dict[str, str], msg: str, parents: list[str] | None = None
) -> str:
    author = Author(name="tester", email="t@dev", timestamp=1700000000)
    entries: list[TreeEntry] = []
    for name, content in sorted(files.items()):
        oid = repo.db.store_blob(content.encode())
        entries.append(TreeEntry(name=name, oid=oid, mode=FileMode.REGULAR))
    tree = Tree()
    for e in entries:
        tree.add(e)
    repo.db.store_tree(tree)
    c = Commit(
        tree_oid=tree.oid,
        author=author,
        committer=author,
        message=msg,
        parents=parents or [],
    )
    repo.db.store_commit(c)
    return c.oid
