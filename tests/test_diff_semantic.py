from __future__ import annotations

import pytest
from click.testing import CliRunner

from oxidize.cli.main import cli


@pytest.fixture
def in_repo(tmp_repo, monkeypatch):
    monkeypatch.chdir(tmp_repo.work_tree)
    return tmp_repo


def test_diff_semantic_flag(in_repo) -> None:
    (in_repo.work_tree / "m.py").write_text("def foo():\n    return 1\n")
    runner = CliRunner()
    r = runner.invoke(cli, ["add", "m.py"], catch_exceptions=False)
    assert r.exit_code == 0, r.output
    r = runner.invoke(cli, ["commit", "-m", "first", "--agent", "t"], catch_exceptions=False)
    assert r.exit_code == 0, r.output

    (in_repo.work_tree / "m.py").write_text("def bar():\n    return 2\n")
    r = runner.invoke(cli, ["diff", "--semantic", "m.py"], catch_exceptions=False)
    assert r.exit_code == 0, r.output
    assert "bar" in r.output or "foo" in r.output
