from __future__ import annotations

import pytest
from click.testing import CliRunner

from oxidize.cli.main import cli
from oxidize.core.repository import Repository


@pytest.fixture
def in_repo(tmp_repo: Repository, monkeypatch: pytest.MonkeyPatch) -> Repository:
    monkeypatch.chdir(tmp_repo.work_tree)
    return tmp_repo


def _commit(repo: Repository, files: dict[str, str], msg: str) -> str:
    for path, content in files.items():
        full = repo.work_tree / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content)
        oid = repo.db.store_blob(full.read_bytes())
        repo.index.add(path, oid, full)
    res = CliRunner().invoke(cli, ["commit", "-m", msg], catch_exceptions=False)
    assert res.exit_code == 0, res.output
    return repo.refs.head() or ""


def test_stash_save_list_pop(in_repo: Repository) -> None:
    repo = in_repo
    _commit(repo, {"a.txt": "v1"}, "first")
    (repo.work_tree / "a.txt").write_text("v2")
    oid = repo.db.store_blob(b"v2")
    repo.index.add("a.txt", oid, repo.work_tree / "a.txt")

    res_save = CliRunner().invoke(cli, ["stash", "save", "feature-x"], catch_exceptions=False)
    assert res_save.exit_code == 0, res_save.output

    import json as _json
    raw = _json.loads(repo.index._path.read_text())
    assert all(e["path"] != "a.txt" for e in raw), raw

    res_list = CliRunner().invoke(cli, ["stash", "list"], catch_exceptions=False)
    assert "feature-x" in res_list.output

    res_pop = CliRunner().invoke(cli, ["stash", "pop", "0"], catch_exceptions=False)
    assert res_pop.exit_code == 0, res_pop.output


def test_hooks_install_template(in_repo: Repository) -> None:
    repo = in_repo
    res = CliRunner().invoke(cli, ["hooks", "install", "pre-commit"], catch_exceptions=False)
    assert res.exit_code == 0, res.output
    candidates = list((repo.oxidize_dir / "hooks").glob("pre-commit*"))
    assert candidates, "expected at least one pre-commit hook file"


def test_hooks_run_returns_exit_code(in_repo: Repository) -> None:
    repo = in_repo
    repo.oxidize_dir.joinpath("hooks").mkdir(parents=True, exist_ok=True)
    fail_path = repo.oxidize_dir / "hooks" / "post-commit.py"
    fail_path.write_text('import sys; sys.exit(7)\n')
    res = CliRunner().invoke(
        cli,
        ["hooks", "run", "post-commit"],
        catch_exceptions=False,
    )
    assert res.exit_code == 7, f"got {res.exit_code}: {res.output}"


def test_bisect_state_cycle(tmp_repo: Repository, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_repo
    monkeypatch.chdir(repo.work_tree)
    _commit(repo, {"a.txt": "ok"}, "good-base")
    runner = CliRunner()

    r = runner.invoke(cli, ["bisect", "start"], catch_exceptions=False)
    assert r.exit_code == 0, r.output

    state_path = repo.oxidize_dir / "bisect.json"
    if state_path.exists():
        state_path.unlink()


def test_show_ref_missing(in_repo: Repository) -> None:
    runner = CliRunner()
    res = runner.invoke(cli, ["show", "9" * 40], catch_exceptions=False)
    assert res.exit_code != 0
