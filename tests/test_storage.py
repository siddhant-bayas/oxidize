from pathlib import Path
from oxidize.storage.database import ObjectDatabase
from oxidize.objects.types import Tree, TreeEntry, FileMode, Author, Commit


def test_store_and_load_blob(tmp_path: Path) -> None:
    db = ObjectDatabase.filesystem(tmp_path / "objects")
    oid = db.store_blob(b"hello")
    blob = db.load_blob(oid)
    assert blob.data == b"hello"


def test_blob_deduplication(tmp_path: Path) -> None:
    db = ObjectDatabase.filesystem(tmp_path / "objects")
    oid1 = db.store_blob(b"same")
    oid2 = db.store_blob(b"same")
    assert oid1 == oid2


def test_store_and_load_tree(tmp_path: Path) -> None:
    db = ObjectDatabase.filesystem(tmp_path / "objects")
    tree = Tree()
    tree.add(TreeEntry("readme.md", "d" * 64, FileMode.REGULAR))
    db.store_tree(tree)
    loaded = db.load_tree(tree.oid)
    assert loaded.entries[0].name == "readme.md"


def test_store_and_load_commit(tmp_path: Path) -> None:
    db = ObjectDatabase.filesystem(tmp_path / "objects")
    author = Author("Dev", "dev@oxide.dev", timestamp=1700000000)
    tree = Tree()
    tree.add(TreeEntry("x.py", "e" * 64, FileMode.REGULAR))
    db.store_tree(tree)
    commit = Commit(tree_oid=tree.oid, author=author, committer=author, message="test")
    db.store_commit(commit)
    loaded = db.load_commit(commit.oid)
    assert loaded.message == "test"
