from oxidize.objects.types import Blob, Tree, TreeEntry, FileMode, Commit, Author


def test_blob_roundtrip() -> None:
    b = Blob(data=b"hello oxide")
    assert Blob.deserialize(b.serialize()).data == b.data


def test_blob_oid_deterministic() -> None:
    assert Blob(data=b"x").oid == Blob(data=b"x").oid
    assert Blob(data=b"x").oid != Blob(data=b"y").oid


def test_tree_ordering() -> None:
    tree = Tree()
    tree.add(TreeEntry("z.py", "a" * 64, FileMode.REGULAR))
    tree.add(TreeEntry("a.py", "b" * 64, FileMode.REGULAR))
    assert tree.entries[0].name == "a.py"


def test_tree_roundtrip() -> None:
    tree = Tree()
    tree.add(TreeEntry("main.py", "c" * 64, FileMode.REGULAR))
    restored = Tree.deserialize(tree.serialize())
    assert restored.entries[0].name == "main.py"
    assert restored.entries[0].oid == "c" * 64


def test_commit_roundtrip() -> None:
    author = Author("Ada", "ada@oxide.dev", timestamp=1700000000)
    c = Commit(tree_oid="a" * 64, author=author, committer=author, message="initial")
    restored = Commit.deserialize(c.serialize())
    assert restored.message == "initial"
    assert restored.author.name == "Ada"
    assert restored.tree_oid == "a" * 64


def test_commit_with_parents() -> None:
    author = Author("Ada", "ada@oxide.dev", timestamp=1700000000)
    c = Commit(
        tree_oid="a" * 64,
        author=author,
        committer=author,
        message="second",
        parents=["b" * 64],
    )
    restored = Commit.deserialize(c.serialize())
    assert restored.parents == ["b" * 64]
