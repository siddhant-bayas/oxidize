from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from oxidize.core.repository import Repository
from oxidize.network.github_remote import GitHubRemote, parse_github_url
from oxidize.network.remote import TransferError
from oxidize.objects.types import Author, Commit, FileMode, Tree, TreeEntry

from .conftest import make_commit


class TestParseGithubURL:
    def test_https_with_git_suffix(self) -> None:
        assert parse_github_url("https://github.com/owner/repo.git") == ("owner", "repo")

    def test_https_without_git_suffix(self) -> None:
        assert parse_github_url("https://github.com/owner/repo") == ("owner", "repo")

    def test_https_trailing_slash(self) -> None:
        assert parse_github_url("https://github.com/owner/repo/") == ("owner", "repo")

    def test_ssh_style(self) -> None:
        assert parse_github_url("git@github.com:owner/repo.git") == ("owner", "repo")

    def test_ssh_without_git_suffix(self) -> None:
        assert parse_github_url("git@github.com:owner/repo") == ("owner", "repo")

    def test_non_github_returns_none(self) -> None:
        assert parse_github_url("file:///tmp/remote") is None
        assert parse_github_url("/path/to/local") is None
        assert parse_github_url("https://gitlab.com/owner/repo") is None

    def test_malformed_returns_none(self) -> None:
        assert parse_github_url("https://github.com/") is None
        assert parse_github_url("https://github.com/only-owner") is None


class TestGitHubRemoteAuth:
    def test_no_token_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OXIDIZE_GITHUB_TOKEN", raising=False)
        with pytest.raises(TransferError, match="OXIDIZE_GITHUB_TOKEN"):
            GitHubRemote("owner", "repo")


class TestGitHubAPIMock:
    def test_create_blob(self) -> None:
        from oxidize.network.github_api import GitHubAPI

        api = GitHubAPI("o", "r", "tok")
        with patch.object(api, "_request") as mock_req:
            mock_req.return_value = {"sha": "abc123"}
            sha = api.create_blob(b"hello")
            assert sha == "abc123"
            mock_req.assert_called_once_with(
                "POST",
                "/git/blobs",
                {
                    "content": "aGVsbG8=",
                    "encoding": "base64",
                },
            )

    def test_create_commit(self) -> None:
        from oxidize.network.github_api import GitHubAPI

        api = GitHubAPI("o", "r", "tok")
        with patch.object(api, "_request") as mock_req:
            mock_req.return_value = {"sha": "def456"}
            sha = api.create_commit(
                tree_sha="tree1",
                parent_shas=["p1"],
                message="test",
                author={"name": "a", "email": "a@b", "date": "2024-01-01T00:00:00Z"},
                committer={"name": "a", "email": "a@b", "date": "2024-01-01T00:00:00Z"},
            )
            assert sha == "def456"

    def test_get_ref_returns_sha(self) -> None:
        from oxidize.network.github_api import GitHubAPI

        api = GitHubAPI("o", "r", "tok")
        with patch.object(api, "_request") as mock_req:
            mock_req.return_value = {"object": {"sha": "sha123"}}
            assert api.get_ref("main") == "sha123"

    def test_get_ref_404_returns_none(self) -> None:
        from oxidize.network.github_api import GitHubAPI, GitHubAPIError

        api = GitHubAPI("o", "r", "tok")
        with patch.object(api, "_request") as mock_req:
            mock_req.side_effect = GitHubAPIError(404, "not found")
            assert api.get_ref("main") is None


class TestGitHubRemotePush:
    def test_push_linear(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OXIDIZE_GITHUB_TOKEN", "fake-token")
        src = tmp_path / "src"
        Repository.init(src)
        src_repo = Repository(src)

        oid1 = make_commit(src_repo, {"a.txt": "hello"}, "first")
        oid2 = make_commit(src_repo, {"a.txt": "world"}, "second", parents=[oid1])
        src_repo.refs.write("refs/heads/main", oid2)

        remote = GitHubRemote("owner", "repo")
        call_log: list[tuple[str, str, dict]] = []

        def mock_request(method: str, endpoint: str, data: dict | None = None) -> dict:
            call_log.append((method, endpoint, data or {}))
            if "/git/blobs" in endpoint:
                return {"sha": f"blob_{hash(str(data)) % 1000}"}
            if "/git/trees" in endpoint:
                return {"sha": f"tree_{len(call_log)}"}
            if "/git/commits" in endpoint:
                return {"sha": f"commit_{len(call_log)}"}
            if "/git/refs" in endpoint and "PATCH" in method:
                return None
            if "/git/refs" in endpoint and "GET" in method:
                return None
            return {}

        with patch.object(remote.api, "_request", side_effect=mock_request):
            pushed = remote.push(src_repo, "main")

        assert pushed == ["main"]
        commit_calls = [c for c in call_log if "/git/commits" in c[1]]
        assert len(commit_calls) == 2

        export_map_path = src_repo.oxidize_dir / "github_export_map.json"
        assert export_map_path.exists()
        data = json.loads(export_map_path.read_text())
        assert oid1 in data["commits"]
        assert oid2 in data["commits"]

    def test_push_merge_commit(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OXIDIZE_GITHUB_TOKEN", "fake-token")
        src = tmp_path / "src"
        Repository.init(src)
        src_repo = Repository(src)

        base = make_commit(src_repo, {"a.txt": "base"}, "base")
        left = make_commit(src_repo, {"a.txt": "left"}, "left", parents=[base])
        right = make_commit(src_repo, {"a.txt": "right"}, "right", parents=[base])
        merge = make_commit(src_repo, {"a.txt": "merged"}, "merge", parents=[left, right])
        src_repo.refs.write("refs/heads/main", merge)

        remote = GitHubRemote("owner", "repo")
        commit_parents: list[list[str]] = []

        def mock_request(method: str, endpoint: str, data: dict | None = None) -> dict:
            if "/git/blobs" in endpoint:
                return {"sha": f"blob_{id(data) % 10000}"}
            if "/git/trees" in endpoint:
                return {"sha": f"tree_{id(data) % 10000}"}
            if "/git/commits" in endpoint:
                if data and "parents" in data:
                    commit_parents.append(data["parents"])
                return {"sha": f"commit_{id(data) % 10000}"}
            if "/git/refs" in endpoint:
                return None
            return {}

        with patch.object(remote.api, "_request", side_effect=mock_request):
            pushed = remote.push(src_repo, "main")

        assert pushed == ["main"]
        merge_commit_parents = [c for c in commit_parents if len(c) == 2]
        assert len(merge_commit_parents) == 1

    def test_push_agent_trailer(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OXIDIZE_GITHUB_TOKEN", "fake-token")
        src = tmp_path / "src"
        Repository.init(src)
        src_repo = Repository(src)

        author = Author(name="tester", email="t@dev", timestamp=1700000000)
        tree = Tree()
        oid = src_repo.db.store_blob(b"content")
        tree.add(TreeEntry(name="f.txt", oid=oid, mode=FileMode.REGULAR))
        src_repo.db.store_tree(tree)
        c = Commit(
            tree_oid=tree.oid,
            author=author,
            committer=author,
            message="with agent",
            agent="claude-code",
        )
        src_repo.db.store_commit(c)
        src_repo.refs.write("refs/heads/main", c.oid)

        remote = GitHubRemote("owner", "repo")
        captured_messages: list[str] = []

        def mock_request(method: str, endpoint: str, data: dict | None = None) -> dict:
            if "/git/commits" in endpoint and data:
                captured_messages.append(data.get("message", ""))
                return {"sha": "abc"}
            if "/git/blobs" in endpoint:
                return {"sha": "blob"}
            if "/git/trees" in endpoint:
                return {"sha": "tree"}
            return None

        with patch.object(remote.api, "_request", side_effect=mock_request):
            remote.push(src_repo, "main")

        assert len(captured_messages) == 1
        assert "Oxidize-Agent: claude-code" in captured_messages[0]
        assert captured_messages[0].startswith("with agent")

    def test_push_no_token(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OXIDIZE_GITHUB_TOKEN", raising=False)
        with pytest.raises(TransferError, match="OXIDIZE_GITHUB_TOKEN"):
            GitHubRemote("o", "r")

    def test_incremental_push(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OXIDIZE_GITHUB_TOKEN", "fake-token")
        src = tmp_path / "src"
        Repository.init(src)
        src_repo = Repository(src)

        oid1 = make_commit(src_repo, {"a.txt": "v1", "b.txt": "v2"}, "first")
        src_repo.refs.write("refs/heads/main", oid1)

        remote = GitHubRemote("owner", "repo")
        export_calls: list[str] = []

        def mock_request(method: str, endpoint: str, data: dict | None = None) -> dict:
            if "/git/blobs" in endpoint:
                export_calls.append("blob")
                return {"sha": f"blob_{len(export_calls)}"}
            if "/git/trees" in endpoint:
                export_calls.append("tree")
                return {"sha": f"tree_{len(export_calls)}"}
            if "/git/commits" in endpoint:
                export_calls.append("commit")
                return {"sha": f"commit_{len(export_calls)}"}
            return None

        with patch.object(remote.api, "_request", side_effect=mock_request):
            remote.push(src_repo, "main")
            first_export_count = len(export_calls)

        oid2 = make_commit(
            src_repo, {"a.txt": "v1", "b.txt": "v2", "c.txt": "v3"}, "second", parents=[oid1]
        )
        src_repo.refs.write("refs/heads/main", oid2)

        with patch.object(remote.api, "_request", side_effect=mock_request):
            remote.push(src_repo, "main")
            second_export_count = len(export_calls) - first_export_count

        assert first_export_count > 0
        assert second_export_count < first_export_count
