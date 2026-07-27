from pathlib import Path

import pytest

from oxidize.storage.backend import _atomic_write
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


def test_atomic_write_success(tmp_path: Path) -> None:
    dst = tmp_path / "obj" / "ab" / "cdef"
    dst.parent.mkdir(parents=True)
    _atomic_write(dst, lambda p: p.write_bytes(b"hello"))
    assert dst.read_bytes() == b"hello"


def test_atomic_write_failure_no_partial_file(tmp_path: Path) -> None:
    dst = tmp_path / "obj" / "ab" / "cdef"
    dst.parent.mkdir(parents=True)

    def broken_writer(p: Path) -> None:
        p.write_bytes(b"partial")
        raise OSError("simulated crash")

    with pytest.raises(OSError, match="simulated crash"):
        _atomic_write(dst, broken_writer)

    assert not dst.exists(), "partial file must not survive at dst"


def test_atomic_write_failure_cleans_temp(tmp_path: Path) -> None:
    dst = tmp_path / "obj" / "ab" / "cdef"
    dst.parent.mkdir(parents=True)

    def broken_writer(p: Path) -> None:
        p.write_bytes(b"data")
        raise ValueError("boom")

    with pytest.raises(ValueError):
        _atomic_write(dst, broken_writer)

    temps = list(dst.parent.iterdir())
    assert temps == [], f"temp files left behind: {temps}"


def test_atomic_write_overwrites_existing(tmp_path: Path) -> None:
    dst = tmp_path / "obj" / "ab" / "cdef"
    dst.parent.mkdir(parents=True)
    dst.write_bytes(b"old")
    _atomic_write(dst, lambda p: p.write_bytes(b"new"))
    assert dst.read_bytes() == b"new"
