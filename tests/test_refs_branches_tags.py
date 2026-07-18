from __future__ import annotations

import pytest
from click.testing import CliRunner

from oxidize.cli.main import cli
from oxidize.core.repository import Repository


def _commit(repo: Repository, files: dict[str, str], msg: str) -> str:
    for path, content in files.items():
        full = repo.work_tree / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content)
        oid = repo.db.store_blob(full.read_bytes())
        repo.index.add(path, oid, full)
    runner = CliRunner()
    res = runner.invoke(cli, ["commit", "-m", msg], catch_exceptions=False)
    assert res.exit_code == 0, res.output
    head = repo.refs.head()
    assert head is not None
    return head


@pytest.fixture
def in_repo(tmp_repo: Repository, monkeypatch: pytest.MonkeyPatch) -> Repository:
    monkeypatch.chdir(tmp_repo.work_tree)
    return tmp_repo


def test_tag_list_create_delete(in_repo: Repository) -> None:
    repo = in_repo
    _commit(repo, {"a.txt": "hello"}, "initial")
    runner = CliRunner()
    r1 = runner.invoke(cli, ["tag", "create", "v1.0"], catch_exceptions=False)
    assert r1.exit_code == 0, r1.output

    r2 = runner.invoke(cli, ["tag", "list"], catch_exceptions=False)
    assert "v1.0" in r2.output

    r3 = runner.invoke(cli, ["tag", "delete", "v1.0"], catch_exceptions=False)
    assert r3.exit_code == 0, r3.output
    assert "v1.0" not in repo.refs.list_tags()


def test_branch_list_create_delete(in_repo: Repository) -> None:
    repo = in_repo
    _commit(repo, {"a.txt": "hello"}, "initial")
    runner = CliRunner()
    runner.invoke(cli, ["branch", "create", "feature"], catch_exceptions=False)
    assert "feature" in repo.refs.list_branches()

    r2 = runner.invoke(cli, ["branch", "list"], catch_exceptions=False)
    assert "feature" in r2.output

    runner.invoke(cli, ["branch", "delete", "feature"], catch_exceptions=False)
    assert "feature" not in repo.refs.list_branches()


def test_branch_delete_current_fails(in_repo: Repository) -> None:
    repo = in_repo
    _commit(repo, {"a.txt": "hello"}, "initial")
    runner = CliRunner()
    r = runner.invoke(cli, ["branch", "delete", "main"], catch_exceptions=True)
    assert r.exit_code != 0
    assert "checked out" in r.output.lower()


def test_log_filters_by_agent(in_repo: Repository) -> None:
    repo = in_repo
    runner = CliRunner()
    (repo.work_tree / "a.txt").write_text("hi")
    repair_target = repo.work_tree / "a.txt"
    _ = repair_target.resolve()
    oid = repo.db.store_blob(b"hi")
    repo.index.add("a.txt", oid, repo.work_tree / "a.txt")
    r = runner.invoke(
        cli,
        ["commit", "-m", "ai commit", "--agent", "claude-code"],
        catch_exceptions=False,
    )
    assert r.exit_code == 0, r.output

    log = runner.invoke(cli, ["log", "--agent", "claude-code"], catch_exceptions=False)
    assert log.exit_code == 0, log.output
    assert "ai commit" in log.output

    log_none = runner.invoke(cli, ["log", "--agent", "nonexistent"], catch_exceptions=False)
    assert "ai commit" not in log_none.output


def test_undo_list(in_repo: Repository) -> None:
    repo = in_repo
    _commit(repo, {"a.txt": "hello"}, "first")
    _commit(repo, {"a.txt": "world"}, "second")
    runner = CliRunner()
    r = runner.invoke(cli, ["undo", "--list"], catch_exceptions=False)
    assert r.exit_code == 0, r.output
    assert "first" in r.output or "second" in r.output
