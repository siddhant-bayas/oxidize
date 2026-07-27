from __future__ import annotations

from pathlib import Path

import pytest

from oxidize.core.repository import Repository
from oxidize.network.remote import Remote, TransferError, _is_ancestor
from oxidize.objects.types import Author, Commit, FileMode, Tree, TreeEntry


def _make_commit(
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


def test_clone_preserves_all_objects(tmp_path: Path) -> None:
    src = tmp_path / "src"
    Repository.init(src)
    src_repo = Repository(src)

    oid1 = _make_commit(src_repo, {"a.txt": "hello"}, "first")
    oid2 = _make_commit(src_repo, {"a.txt": "world", "b.txt": "new"}, "second", parents=[oid1])
    src_repo.refs.write("refs/heads/main", oid2)

    remote_path = tmp_path / "remote"
    remote = Remote(str(remote_path))
    remote.push(src_repo, "main")

    target = tmp_path / "clone"
    clone_repo = remote.clone(target)

    commit = clone_repo.db.load_commit(oid2)
    assert clone_repo.db.exists(commit.tree_oid)
    tree = clone_repo.db.load_tree(commit.tree_oid)
    for entry in tree:
        assert clone_repo.db.exists(entry.oid), f"missing blob {entry.oid}"

    commit1 = clone_repo.db.load_commit(oid1)
    assert clone_repo.db.exists(commit1.tree_oid)
    tree1 = clone_repo.db.load_tree(commit1.tree_oid)
    for entry in tree1:
        assert clone_repo.db.exists(entry.oid), f"missing blob {entry.oid}"

    head_oid = clone_repo.refs.head()
    assert head_oid == oid2


def test_clone_detached_head(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src_repo = Repository.init(src)
    oid = _make_commit(src_repo, {"a.txt": "hi"}, "only")
    src_repo.refs.write("refs/heads/main", oid)

    bare = src / ".bare"
    (bare / "objects").mkdir(parents=True)
    (bare / "refs" / "heads").mkdir(parents=True)
    (bare / "refs" / "tags").mkdir(parents=True)
    (bare / "HEAD").write_text(oid + "\n")

    remote = Remote(str(bare))
    clone_repo = remote.clone(tmp_path / "clone")
    head_content = (clone_repo.oxidize_dir / "HEAD").read_text().strip()
    assert head_content == oid


def test_push_diverges_raises(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src_repo = Repository.init(src)
    oid1 = _make_commit(src_repo, {"a.txt": "v1"}, "first")
    src_repo.refs.write("refs/heads/main", oid1)

    remote = Remote(str(tmp_path / "remote"))
    remote.push(src_repo, "main")

    bare = remote.bare_path
    diverged_oid = "b" * 64
    (bare / "refs" / "heads" / "main").write_text(diverged_oid + "\n")

    oid2 = _make_commit(src_repo, {"a.txt": "v2"}, "second", parents=[oid1])
    src_repo.refs.write("refs/heads/main", oid2)

    with pytest.raises(TransferError, match="diverges"):
        remote.push(src_repo, "main")


def test_push_force_diverges_succeeds(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src_repo = Repository.init(src)
    oid1 = _make_commit(src_repo, {"a.txt": "v1"}, "first")
    src_repo.refs.write("refs/heads/main", oid1)

    remote = Remote(str(tmp_path / "remote"))
    remote.push(src_repo, "main")

    bare = remote.bare_path
    diverged_oid = "b" * 64
    (bare / "refs" / "heads" / "main").write_text(diverged_oid + "\n")

    oid2 = _make_commit(src_repo, {"a.txt": "v2"}, "second", parents=[oid1])
    src_repo.refs.write("refs/heads/main", oid2)

    pushed = remote.push(src_repo, "main", force=True)
    assert pushed == ["main"]
    assert (bare / "refs" / "heads" / "main").read_text().strip() == oid2


def test_pull_deep_repo_all_objects(tmp_path: Path) -> None:
    src = tmp_path / "src"
    Repository.init(src)
    src_repo = Repository(src)

    oids = []
    parent = None
    for i in range(60):
        oid = _make_commit(src_repo, {"a.txt": f"v{i}"}, f"commit {i}", parents=[parent] if parent else [])
        oids.append(oid)
        parent = oid
    src_repo.refs.write("refs/heads/main", oids[-1])

    remote = Remote(str(tmp_path / "remote"))
    remote.push(src_repo, "main")

    dest = tmp_path / "dest"
    Repository.init(dest)
    dest_repo = Repository(dest)
    dest_repo.refs.write("refs/heads/main", oids[0])

    pulled = remote.pull(dest_repo, "main")
    assert pulled == ["main"]

    for oid in oids:
        assert dest_repo.db.exists(oid), f"missing object {oid}"
        commit = dest_repo.db.load_commit(oid)
        assert dest_repo.db.exists(commit.tree_oid)


def test_is_ancestor_linear(tmp_path: Path) -> None:
    repo = Repository.init(tmp_path / "a")
    oid1 = _make_commit(repo, {"a.txt": "1"}, "c1")
    oid2 = _make_commit(repo, {"a.txt": "2"}, "c2", parents=[oid1])
    oid3 = _make_commit(repo, {"a.txt": "3"}, "c3", parents=[oid2])

    assert _is_ancestor(repo, oid1, oid3)
    assert _is_ancestor(repo, oid2, oid3)
    assert not _is_ancestor(repo, oid3, oid1)


def test_is_ancestor_merge(tmp_path: Path) -> None:
    repo = Repository.init(tmp_path / "b")
    base = _make_commit(repo, {"a.txt": "base"}, "base")
    left = _make_commit(repo, {"a.txt": "left"}, "left", parents=[base])
    right = _make_commit(repo, {"a.txt": "right"}, "right", parents=[base])
    merge = _make_commit(repo, {"a.txt": "merged"}, "merge", parents=[left, right])

    assert _is_ancestor(repo, base, merge)
    assert _is_ancestor(repo, left, merge)
    assert _is_ancestor(repo, right, merge)
    assert not _is_ancestor(repo, left, right)
    assert not _is_ancestor(repo, right, left)


def test_push_nested_trees_all_objects_copied(tmp_path: Path) -> None:
    src = tmp_path / "src"
    Repository.init(src)
    src_repo = Repository(src)
    author = Author(name="tester", email="t@dev", timestamp=1700000000)

    blob_root = src_repo.db.store_blob(b"root file")
    blob_sub = src_repo.db.store_blob(b"sub file")
    blob_deep = src_repo.db.store_blob(b"deep file")

    deep_tree = Tree()
    deep_tree.add(TreeEntry(name="deep.txt", oid=blob_deep, mode=FileMode.REGULAR))
    src_repo.db.store_tree(deep_tree)

    sub_tree = Tree()
    sub_tree.add(TreeEntry(name="sub.txt", oid=blob_sub, mode=FileMode.REGULAR))
    sub_tree.add(TreeEntry(name="deep", oid=deep_tree.oid, mode=FileMode.DIRECTORY))
    src_repo.db.store_tree(sub_tree)

    root_tree = Tree()
    root_tree.add(TreeEntry(name="root.txt", oid=blob_root, mode=FileMode.REGULAR))
    root_tree.add(TreeEntry(name="sub", oid=sub_tree.oid, mode=FileMode.DIRECTORY))
    src_repo.db.store_tree(root_tree)

    commit = Commit(
        tree_oid=root_tree.oid, author=author, committer=author,
        message="nested", parents=[],
    )
    src_repo.db.store_commit(commit)
    src_repo.refs.write("refs/heads/main", commit.oid)

    remote = Remote(str(tmp_path / "remote"))
    remote.push(src_repo, "main")

    bare = remote.bare_path
    for expected in [blob_root, blob_sub, blob_deep, deep_tree.oid, sub_tree.oid, root_tree.oid]:
        obj_path = bare / "objects" / expected[:2] / expected[2:]
        assert obj_path.exists(), f"missing object {expected[:12]}… in bare repo"

    clone_repo = remote.clone(tmp_path / "clone")
    for expected in [blob_root, blob_sub, blob_deep, deep_tree.oid, sub_tree.oid]:
        assert clone_repo.db.exists(expected), f"missing object {expected[:12]}… in clone"


def test_incremental_push_only_copies_new_objects(tmp_path: Path) -> None:
    src = tmp_path / "src"
    Repository.init(src)
    src_repo = Repository(src)

    oid1 = _make_commit(src_repo, {"a.txt": "first"}, "first")
    src_repo.refs.write("refs/heads/main", oid1)

    remote = Remote(str(tmp_path / "remote"))
    remote.push(src_repo, "main")

    oid2 = _make_commit(src_repo, {"a.txt": "second"}, "second", parents=[oid1])
    src_repo.refs.write("refs/heads/main", oid2)

    pushed = remote.push(src_repo, "main")
    assert pushed == ["main"]

    bare = remote.bare_path
    commit2 = src_repo.db.load_commit(oid2)
    for oid in [oid2, commit2.tree_oid]:
        assert (bare / "objects" / oid[:2] / oid[2:]).exists()

    commit1 = src_repo.db.load_commit(oid1)
    assert (bare / "objects" / commit1.tree_oid[:2] / commit1.tree_oid[2:]).exists()
