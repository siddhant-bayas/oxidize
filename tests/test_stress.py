from __future__ import annotations

import json
import time
import tracemalloc
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from oxidize.cli.main import cli
from oxidize.core.repository import Repository
from oxidize.network.github_api import GitHubAPI, GitHubAPIError
from oxidize.network.github_remote import GitHubRemote
from oxidize.network.remote import Remote, TransferError
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


def _make_chain(repo: Repository, n: int) -> str:
    parent = None
    for i in range(n):
        parent = _make_commit(repo, {"a.txt": f"v{i}"}, f"commit {i}", parents=[parent] if parent else None)
    return parent


def _make_wide_tree(repo: Repository, n_files: int) -> str:
    files = {f"file_{i:04d}.txt": f"content_{i}" for i in range(n_files)}
    return _make_commit(repo, files, f"add {n_files} files")


def _stats(name: str, t0: float, *, obj_count: int | None = None, api_calls: int | None = None, dedup: float | None = None) -> None:
    elapsed = (time.perf_counter() - t0) * 1000
    mem_kb = 0
    if tracemalloc.is_tracing():
        snap = tracemalloc.take_snapshot()
        top = snap.statistics("lineno")
        mem_kb = top[0].size / 1024 if top else 0
    parts = [f"{name}: {elapsed:.0f}ms", f"{mem_kb:.0f}KB"]
    if obj_count is not None:
        parts.append(f"objects={obj_count}")
    if api_calls is not None:
        parts.append(f"api_calls={api_calls}")
    if dedup is not None:
        parts.append(f"dedup={dedup:.0%}")
    print("  ".join(parts))


# ============================================================================
# SECTION 1: Filesystem Remote Stress
# ============================================================================


def test_deep_chain_500(tmp_path: Path) -> None:
    tracemalloc.start()
    t0 = time.perf_counter()

    src = tmp_path / "src"
    Repository.init(src)
    src_repo = Repository(src)

    head = _make_chain(src_repo, 500)
    src_repo.refs.write("refs/heads/main", head)

    remote = Remote(str(tmp_path / "remote"))
    remote.push(src_repo, "main")

    clone_repo = remote.clone(tmp_path / "clone")
    _stats("deep_chain_500", t0, obj_count=500)

    assert clone_repo.refs.head() == head
    commit = clone_repo.db.load_commit(head)
    assert clone_repo.db.exists(commit.tree_oid)
    tracemalloc.stop()


def test_wide_tree_1000(tmp_path: Path) -> None:
    tracemalloc.start()
    t0 = time.perf_counter()

    src = tmp_path / "src"
    Repository.init(src)
    src_repo = Repository(src)

    head = _make_wide_tree(src_repo, 1000)
    src_repo.refs.write("refs/heads/main", head)

    remote = Remote(str(tmp_path / "remote"))
    remote.push(src_repo, "main")

    clone_repo = remote.clone(tmp_path / "clone")
    _stats("wide_tree_1000", t0, obj_count=1002)

    commit = clone_repo.db.load_commit(head)
    tree = clone_repo.db.load_tree(commit.tree_oid)
    assert len(list(tree)) == 1000
    for entry in tree:
        assert clone_repo.db.exists(entry.oid), f"missing {entry.name}"
    tracemalloc.stop()


def test_clone_roundtrip_integrity(tmp_path: Path) -> None:
    tracemalloc.start()
    t0 = time.perf_counter()

    src = tmp_path / "src"
    Repository.init(src)
    src_repo = Repository(src)

    parent = None
    verified = 0
    for i in range(20):
        files = {f"f{j}.txt": f"v{i}_{j}" for j in range(5)}
        parent = _make_commit(src_repo, files, f"commit {i}", parents=[parent] if parent else None)
    src_repo.refs.write("refs/heads/main", parent)

    remote = Remote(str(tmp_path / "remote"))
    remote.push(src_repo, "main")

    clone_repo = remote.clone(tmp_path / "clone")

    oid = parent
    for _ in range(20):
        commit = clone_repo.db.load_commit(oid)
        assert clone_repo.db.exists(commit.tree_oid)
        tree = clone_repo.db.load_tree(commit.tree_oid)
        for entry in tree:
            assert clone_repo.db.exists(entry.oid)
            verified += 1
        oid = commit.parents[0] if commit.parents else None
        if not oid:
            break

    _stats("clone_roundtrip", t0, obj_count=verified)
    assert verified > 0
    tracemalloc.stop()


def test_pull_incremental(tmp_path: Path) -> None:
    tracemalloc.start()
    t0 = time.perf_counter()

    src = tmp_path / "src"
    Repository.init(src)
    src_repo = Repository(src)

    parent = None
    for i in range(30):
        parent = _make_commit(src_repo, {"a.txt": f"v{i}"}, f"commit {i}", parents=[parent] if parent else None)
    src_repo.refs.write("refs/heads/main", parent)

    remote = Remote(str(tmp_path / "remote"))
    remote.push(src_repo, "main")

    dest = tmp_path / "dest"
    Repository.init(dest)
    dest_repo = Repository(dest)

    partial_parent = None
    for i in range(10):
        partial_parent = _make_commit(dest_repo, {"a.txt": f"v{i}"}, f"commit {i}", parents=[partial_parent] if partial_parent else None)
    dest_repo.refs.write("refs/heads/main", partial_parent)

    copy_count = 0

    from oxidize.network import remote as remote_mod
    original_copy_fn = remote_mod._copy_object

    def counting_copy(src_root: Path, dst_root: Path, oid: str) -> None:
        nonlocal copy_count
        copy_count += 1
        original_copy_fn(src_root, dst_root, oid)

    with patch.object(remote_mod, "_copy_object", side_effect=counting_copy):
        pulled = remote.pull(dest_repo, "main")

    _stats("pull_incremental", t0, obj_count=copy_count)
    assert pulled == ["main"]
    assert dest_repo.refs.head() == parent
    assert copy_count <= 60, f"expected <=60 copies, got {copy_count}"
    tracemalloc.stop()


def test_push_diverge_force(tmp_path: Path) -> None:
    t0 = time.perf_counter()

    src = tmp_path / "src"
    Repository.init(src)
    src_repo = Repository(src)

    oid1 = _make_commit(src_repo, {"a.txt": "v1"}, "first")
    src_repo.refs.write("refs/heads/main", oid1)

    remote = Remote(str(tmp_path / "remote"))
    remote.push(src_repo, "main")

    (remote.bare_path / "refs" / "heads" / "main").write_text("b" * 64 + "\n")

    oid2 = _make_commit(src_repo, {"a.txt": "v2"}, "second", parents=[oid1])
    src_repo.refs.write("refs/heads/main", oid2)

    with pytest.raises(TransferError, match="diverges"):
        remote.push(src_repo, "main")

    pushed = remote.push(src_repo, "main", force=True)
    _stats("push_diverge_force", t0)
    assert pushed == ["main"]
    assert (remote.bare_path / "refs" / "heads" / "main").read_text().strip() == oid2


def test_clone_detached_deep(tmp_path: Path) -> None:
    t0 = time.perf_counter()

    src = tmp_path / "src"
    Repository.init(src)
    src_repo = Repository(src)

    head = _make_chain(src_repo, 200)
    src_repo.refs.write("refs/heads/main", head)

    bare = tmp_path / "bare"
    (bare / "objects").mkdir(parents=True)
    (bare / "refs" / "heads").mkdir(parents=True)
    (bare / "refs" / "tags").mkdir(parents=True)
    (bare / "HEAD").write_text(head + "\n")

    remote = Remote(str(bare))
    clone_repo = remote.clone(tmp_path / "clone")

    head_content = (clone_repo.oxidize_dir / "HEAD").read_text().strip()
    _stats("clone_detached_deep", t0, obj_count=200)
    assert head_content == head


# ============================================================================
# SECTION 2: GitHub Remote Stress
# ============================================================================


def test_github_50_commits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OXIDIZE_GITHUB_TOKEN", "fake")
    tracemalloc.start()
    t0 = time.perf_counter()

    src = tmp_path / "src"
    Repository.init(src)
    src_repo = Repository(src)

    parent = None
    for i in range(50):
        parent = _make_commit(src_repo, {f"f{i}.txt": f"v{i}"}, f"commit {i}", parents=[parent] if parent else None)
    src_repo.refs.write("refs/heads/main", parent)

    remote = GitHubRemote("owner", "repo")
    call_counts: dict[str, int] = {"blob": 0, "tree": 0, "commit": 0}

    def mock_request(method: str, endpoint: str, data: dict | None = None) -> dict:
        if "/git/blobs" in endpoint:
            call_counts["blob"] += 1
            return {"sha": f"blob_{call_counts['blob']}"}
        if "/git/trees" in endpoint:
            call_counts["tree"] += 1
            return {"sha": f"tree_{call_counts['tree']}"}
        if "/git/commits" in endpoint:
            call_counts["commit"] += 1
            return {"sha": f"commit_{call_counts['commit']}"}
        return None

    with patch.object(remote.api, "_request", side_effect=mock_request):
        remote.push(src_repo, "main")

    first_counts = call_counts.copy()
    extra = _make_commit(src_repo, {"f50.txt": "v50"}, "commit 50", parents=[parent])
    src_repo.refs.write("refs/heads/main", extra)

    with patch.object(remote.api, "_request", side_effect=mock_request):
        remote.push(src_repo, "main")

    total_api = sum(call_counts.values())
    new_api = sum(call_counts[k] - first_counts[k] for k in call_counts)
    dedup = 1 - (new_api / total_api) if total_api > 0 else 0

    export_map = json.loads((src_repo.oxidize_dir / "github_export_map.json").read_text())
    _stats("github_50_commits", t0, api_calls=total_api, dedup=dedup)
    print(f"  export_map_entries={len(export_map['commits'])}")
    assert first_counts["commit"] == 50
    assert call_counts["commit"] - first_counts["commit"] == 1


def test_github_merge_topology(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OXIDIZE_GITHUB_TOKEN", "fake")
    t0 = time.perf_counter()

    src = tmp_path / "src"
    Repository.init(src)
    src_repo = Repository(src)

    base = _make_commit(src_repo, {"a.txt": "base"}, "base")
    left = _make_commit(src_repo, {"a.txt": "left"}, "left", parents=[base])
    right = _make_commit(src_repo, {"b.txt": "right"}, "right", parents=[base])
    merge = _make_commit(src_repo, {"a.txt": "m", "b.txt": "m"}, "merge", parents=[left, right])
    src_repo.refs.write("refs/heads/main", merge)

    remote = GitHubRemote("owner", "repo")
    parent_lists: list[list[str]] = []

    def mock_request(method: str, endpoint: str, data: dict | None = None) -> dict:
        if "/git/blobs" in endpoint:
            return {"sha": "b"}
        if "/git/trees" in endpoint:
            return {"sha": "t"}
        if "/git/commits" in endpoint:
            if data and "parents" in data:
                parent_lists.append(data["parents"])
            return {"sha": "c"}
        return None

    with patch.object(remote.api, "_request", side_effect=mock_request):
        remote.push(src_repo, "main")

    merge_calls = [p for p in parent_lists if len(p) == 2]
    _stats("github_merge_topology", t0, api_calls=len(parent_lists))
    assert len(merge_calls) == 1, "merge commit must have 2 parents"
    assert all(len(p) <= 2 for p in parent_lists)


def test_github_large_blob(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OXIDIZE_GITHUB_TOKEN", "fake")
    t0 = time.perf_counter()

    src = tmp_path / "src"
    Repository.init(src)
    src_repo = Repository(src)

    large_content = "x" * (1024 * 1024)
    oid = _make_commit(src_repo, {"big.txt": large_content}, "big file")
    src_repo.refs.write("refs/heads/main", oid)

    remote = GitHubRemote("owner", "repo")
    captured_blob_content: list[bytes] = []

    def mock_request(method: str, endpoint: str, data: dict | None = None) -> dict:
        if "/git/blobs" in endpoint and data:
            import base64
            captured_blob_content.append(base64.b64decode(data["content"]))
            return {"sha": "big_blob"}
        if "/git/trees" in endpoint:
            return {"sha": "t"}
        if "/git/commits" in endpoint:
            return {"sha": "c"}
        return None

    with patch.object(remote.api, "_request", side_effect=mock_request):
        remote.push(src_repo, "main")

    _stats("github_large_blob", t0)
    assert len(captured_blob_content) == 1
    assert len(captured_blob_content[0]) == 1024 * 1024


def test_github_wide_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OXIDIZE_GITHUB_TOKEN", "fake")
    tracemalloc.start()
    t0 = time.perf_counter()

    src = tmp_path / "src"
    Repository.init(src)
    src_repo = Repository(src)

    head = _make_wide_tree(src_repo, 1000)
    src_repo.refs.write("refs/heads/main", head)

    remote = GitHubRemote("owner", "repo")
    tree_entry_counts: list[int] = []

    def mock_request(method: str, endpoint: str, data: dict | None = None) -> dict:
        if "/git/blobs" in endpoint:
            return {"sha": "b"}
        if "/git/trees" in endpoint:
            if data and "tree" in data:
                tree_entry_counts.append(len(data["tree"]))
            return {"sha": "t"}
        if "/git/commits" in endpoint:
            return {"sha": "c"}
        return None

    with patch.object(remote.api, "_request", side_effect=mock_request):
        remote.push(src_repo, "main")

    _stats("github_wide_tree", t0, api_calls=sum(tree_entry_counts) + len(tree_entry_counts) + 1)
    assert len(tree_entry_counts) == 1
    assert tree_entry_counts[0] == 1000


def test_github_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OXIDIZE_GITHUB_TOKEN", "fake")
    t0 = time.perf_counter()

    src = tmp_path / "src"
    Repository.init(src)
    src_repo = Repository(src)

    parent = None
    for i in range(10):
        parent = _make_commit(src_repo, {f"f{i}.txt": f"v{i}"}, f"commit {i}", parents=[parent] if parent else None)
    src_repo.refs.write("refs/heads/main", parent)

    remote = GitHubRemote("owner", "repo")
    export_calls: list[str] = []

    def mock_request(method: str, endpoint: str, data: dict | None = None) -> dict:
        if "/git/blobs" in endpoint:
            export_calls.append("blob")
            return {"sha": "b"}
        if "/git/trees" in endpoint:
            export_calls.append("tree")
            return {"sha": "t"}
        if "/git/commits" in endpoint:
            export_calls.append("commit")
            return {"sha": "c"}
        return None

    with patch.object(remote.api, "_request", side_effect=mock_request):
        remote.push(src_repo, "main")

    first_count = len(export_calls)

    with patch.object(remote.api, "_request", side_effect=mock_request):
        remote.push(src_repo, "main")

    second_count = len(export_calls) - first_count
    _stats("github_idempotent", t0, api_calls=second_count, dedup=1.0 if second_count == 0 else 0)
    assert second_count == 0


def test_github_agent_trailers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OXIDIZE_GITHUB_TOKEN", "fake")
    t0 = time.perf_counter()

    src = tmp_path / "src"
    Repository.init(src)
    src_repo = Repository(src)

    parent = None
    for i in range(20):
        author = Author(name="tester", email="t@dev", timestamp=1700000000)
        entries = []
        oid = src_repo.db.store_blob(f"v{i}".encode())
        entries.append(TreeEntry(name="a.txt", oid=oid, mode=FileMode.REGULAR))
        tree = Tree()
        for e in entries:
            tree.add(e)
        src_repo.db.store_tree(tree)
        c = Commit(
            tree_oid=tree.oid, author=author, committer=author,
            message=f"commit {i}", parents=[parent] if parent else [],
            agent="claude-code",
        )
        src_repo.db.store_commit(c)
        parent = c.oid
    src_repo.refs.write("refs/heads/main", parent)

    remote = GitHubRemote("owner", "repo")
    messages: list[str] = []

    def mock_request(method: str, endpoint: str, data: dict | None = None) -> dict:
        if "/git/commits" in endpoint and data:
            messages.append(data.get("message", ""))
            return {"sha": "c"}
        if "/git/blobs" in endpoint:
            return {"sha": "b"}
        if "/git/trees" in endpoint:
            return {"sha": "t"}
        return None

    with patch.object(remote.api, "_request", side_effect=mock_request):
        remote.push(src_repo, "main")

    _stats("github_agent_trailers", t0, api_calls=len(messages))
    assert len(messages) == 20
    for msg in messages:
        assert "Oxidize-Agent: claude-code" in msg


# ============================================================================
# SECTION 3: Rate Limit & Error Handling
# ============================================================================


def test_rate_limit_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OXIDIZE_GITHUB_TOKEN", "fake")
    t0 = time.perf_counter()

    api = GitHubAPI("o", "r", "tok")
    call_count = 0

    def mock_urlopen(req: object) -> object:
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            from io import BytesIO
            fp = BytesIO(b'rate limited')
            raise urllib.error.HTTPError(
                url=getattr(req, "full_url", ""), code=429, msg="rate limited",
                hdrs={"Retry-After": "0"}, fp=fp
            )
        resp = MagicMock()
        resp.status = 200
        resp.__enter__ = lambda s: s
        resp.__exit__ = lambda *a: False
        resp.read.return_value = b'{"sha":"ok"}'
        return resp

    with patch("oxidize.network.github_api.urllib.request.urlopen", side_effect=mock_urlopen):
        result = api.create_blob(b"test")

    elapsed = (time.perf_counter() - t0) * 1000
    print(f"  rate_limit_retry: {elapsed:.0f}ms  calls={call_count}")
    assert result == "ok"
    assert call_count == 3


def test_rate_limit_exhausted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OXIDIZE_GITHUB_TOKEN", "fake")
    t0 = time.perf_counter()

    api = GitHubAPI("o", "r", "tok")

    def mock_request(method: str, endpoint: str, data: dict | None = None) -> dict:
        raise GitHubAPIError(429, "rate limited")

    with patch.object(api, "_request", side_effect=mock_request):
        with pytest.raises(GitHubAPIError, match="429"):
            api.create_blob(b"test")

    elapsed = (time.perf_counter() - t0) * 1000
    print(f"  rate_limit_exhausted: {elapsed:.0f}ms")


def test_get_ref_404(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OXIDIZE_GITHUB_TOKEN", "fake")
    t0 = time.perf_counter()

    api = GitHubAPI("o", "r", "tok")

    def mock_request(method: str, endpoint: str, data: dict | None = None) -> dict:
        raise GitHubAPIError(404, "not found")

    with patch.object(api, "_request", side_effect=mock_request):
        result = api.get_ref("main")

    elapsed = (time.perf_counter() - t0) * 1000
    print(f"  get_ref_404: {elapsed:.0f}ms")
    assert result is None


def test_network_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OXIDIZE_GITHUB_TOKEN", "fake")
    t0 = time.perf_counter()

    api = GitHubAPI("o", "r", "tok")

    def mock_request(method: str, endpoint: str, data: dict | None = None) -> dict:
        raise urllib.error.URLError("timed out")

    with patch.object(api, "_request", side_effect=mock_request):
        with pytest.raises(urllib.error.URLError):
            api.create_blob(b"test")

    elapsed = (time.perf_counter() - t0) * 1000
    print(f"  network_timeout: {elapsed:.0f}ms")


# ============================================================================
# SECTION 4: CLI Integration Stress
# ============================================================================


def test_cli_github_push(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OXIDIZE_GITHUB_TOKEN", "fake")
    t0 = time.perf_counter()

    src = tmp_path / "src"
    Repository.init(src)
    src_repo = Repository(src)
    parent = None
    for i in range(5):
        parent = _make_commit(src_repo, {f"f{i}.txt": f"v{i}"}, f"commit {i}", parents=[parent] if parent else None)
    src_repo.refs.write("refs/heads/main", parent)

    remote = GitHubRemote("owner", "repo")

    def mock_request(method: str, endpoint: str, data: dict | None = None) -> dict:
        if "/git/blobs" in endpoint:
            return {"sha": "b"}
        if "/git/trees" in endpoint:
            return {"sha": "t"}
        if "/git/commits" in endpoint:
            return {"sha": "c"}
        return None

    monkeypatch.chdir(src)
    with patch.object(remote.api, "_request", side_effect=mock_request):
        from oxidize.network.github_remote import GitHubRemote as GR
        original_init = GR.__init__

        def patched_init(self_inner: GitHubRemote, owner: str, repo: str) -> None:
            original_init(self_inner, owner, repo)
            self_inner.api._request = mock_request

        with patch.object(GR, "__init__", patched_init):
            runner = CliRunner()
            res = runner.invoke(cli, ["remote", "push", "https://github.com/owner/repo", "main"])

    elapsed = (time.perf_counter() - t0) * 1000
    print(f"  cli_github_push: {elapsed:.0f}ms  exit_code={res.exit_code}")
    assert res.exit_code == 0
    assert "owner/repo" in res.output


def test_cli_filesystem_push(tmp_path: Path) -> None:
    t0 = time.perf_counter()

    src = tmp_path / "src"
    Repository.init(src)
    src_repo = Repository(src)
    parent = None
    for i in range(3):
        parent = _make_commit(src_repo, {f"f{i}.txt": f"v{i}"}, f"commit {i}", parents=[parent] if parent else None)
    src_repo.refs.write("refs/heads/main", parent)

    remote_path = tmp_path / "remote"
    remote_path.mkdir()

    monkeypatch_dir = src
    import os
    old_cwd = os.getcwd()
    os.chdir(monkeypatch_dir)
    try:
        runner = CliRunner()
        res = runner.invoke(cli, ["remote", "push", str(remote_path), "main"])
    finally:
        os.chdir(old_cwd)

    elapsed = (time.perf_counter() - t0) * 1000
    print(f"  cli_filesystem_push: {elapsed:.0f}ms  exit_code={res.exit_code}")
    assert res.exit_code == 0


def test_cli_github_clone_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OXIDIZE_GITHUB_TOKEN", "fake")
    t0 = time.perf_counter()

    runner = CliRunner()
    res = runner.invoke(cli, ["remote", "clone", "https://github.com/owner/repo"])

    elapsed = (time.perf_counter() - t0) * 1000
    print(f"  cli_github_clone_rej: {elapsed:.0f}ms  exit_code={res.exit_code}")
    assert res.exit_code != 0
    assert "not supported yet" in res.output.lower()


def test_cli_github_pull_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OXIDIZE_GITHUB_TOKEN", "fake")
    t0 = time.perf_counter()

    src = tmp_path / "src"
    Repository.init(src)

    import os
    old_cwd = os.getcwd()
    os.chdir(src)
    try:
        runner = CliRunner()
        res = runner.invoke(cli, ["remote", "pull", "https://github.com/owner/repo"])
    finally:
        os.chdir(old_cwd)

    elapsed = (time.perf_counter() - t0) * 1000
    print(f"  cli_github_pull_rej: {elapsed:.0f}ms  exit_code={res.exit_code}")
    assert res.exit_code != 0
    assert "push-only" in res.output.lower()
