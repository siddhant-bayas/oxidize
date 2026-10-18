from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from oxidize.cli.main import cli
from oxidize.core.repository import Repository


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    src = tmp_path / "src"
    src.mkdir()
    _git(src, "init", "-q")
    _git(src, "config", "user.email", "t@t")
    _git(src, "config", "user.name", "t")
    (src / "a.txt").write_text("hello\n")
    _git(src, "add", "a.txt")
    _git(src, "commit", "-q", "-m", "first")
    (src / "sub").mkdir()
    (src / "sub" / "b.txt").write_text("world\n")
    _git(src, "add", "sub/b.txt")
    _git(src, "commit", "-q", "-m", "second")
    return src


def test_import_git_cli(tmp_path: Path, git_repo: Path) -> None:
    target = tmp_path / "out"
    runner = CliRunner()
    res = runner.invoke(
        cli, ["import-git", str(git_repo), "--target", str(target)], catch_exceptions=False
    )
    assert res.exit_code == 0, res.output
    repo = Repository(target)
    assert len(repo.refs.list_branches()) >= 1
    head = repo.refs.head()
    assert head is not None
    assert (target / "a.txt").read_text() == "hello\n"
    assert (target / "sub" / "b.txt").read_text() == "world\n"


def test_import_git_library(tmp_path: Path, git_repo: Path) -> None:
    from oxidize.importer.git_import import import_git

    target = tmp_path / "out2"
    repo = Repository.init(target)
    commit_map = import_git(git_repo, repo)
    assert len(commit_map) == 2
