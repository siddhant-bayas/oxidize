from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from oxidize.cli.main import cli
from oxidize.core.ignores import IgnoreMatcher
from oxidize.core.repository import Repository


def _write_oxignore(repo: Repository, content: str) -> None:
    (repo.work_tree / ".oxignore").write_text(content)


@pytest.fixture
def in_work_tree(tmp_repo: Repository, monkeypatch: pytest.MonkeyPatch) -> Repository:
    monkeypatch.chdir(tmp_repo.work_tree)
    return tmp_repo


def test_empty_repo_no_oxignore(tmp_path: Path) -> None:
    (tmp_path / ".oxidize").mkdir()
    (tmp_path / ".oxidize" / "HEAD").write_text("ref: refs/heads/main")
    (tmp_path / ".oxidize" / "objects").mkdir(parents=True, exist_ok=True)
    repo = Repository(tmp_path)
    matcher = IgnoreMatcher.from_repo(repo)
    matcher._user_spec  # ensure load ran
    assert matcher.patterns() == []
    assert not matcher.is_ignored("main.py")
    assert not matcher.is_ignored("src/app.py")


def test_literal_pattern(tmp_repo: Repository) -> None:
    _write_oxignore(tmp_repo, "secrets.env\n")
    matcher = IgnoreMatcher.from_repo(tmp_repo)
    assert matcher.is_ignored("secrets.env")
    assert not matcher.is_ignored("secrets.env.bak")


def test_glob_pattern(tmp_repo: Repository) -> None:
    _write_oxignore(tmp_repo, "*.log\n")
    matcher = IgnoreMatcher.from_repo(tmp_repo)
    assert matcher.is_ignored("app.log")
    assert matcher.is_ignored("logs/debug.log")
    assert not matcher.is_ignored("app.txt")


def test_directory_pattern(tmp_repo: Repository) -> None:
    _write_oxignore(tmp_repo, "build/\n")
    matcher = IgnoreMatcher.from_repo(tmp_repo)
    assert matcher.is_ignored("build/output.bin")
    assert matcher.is_ignored("build/sub/file.o")


def test_doublestar_pattern(tmp_repo: Repository) -> None:
    _write_oxignore(tmp_repo, "**/__pycache__/\n")
    matcher = IgnoreMatcher.from_repo(tmp_repo)
    assert matcher.is_ignored("__pycache__/foo.pyc")
    assert matcher.is_ignored("src/__pycache__/bar.pyc")
    assert matcher.is_ignored("a/b/__pycache__/baz.pyc")


def test_negation_pattern(tmp_repo: Repository) -> None:
    _write_oxignore(tmp_repo, "*.pyc\n!keep.pyc\n")
    matcher = IgnoreMatcher.from_repo(tmp_repo)
    assert matcher.is_ignored("junk.pyc")
    assert not matcher.is_ignored("keep.pyc")


def test_comments_and_blanks_skipped(tmp_repo: Repository) -> None:
    _write_oxignore(
        tmp_repo,
        "\n# a comment\n\n   \n*.tmp\n# another\n",
    )
    matcher = IgnoreMatcher.from_repo(tmp_repo)
    assert matcher.patterns() == ["*.tmp"]


def test_builtins_always_on(tmp_repo: Repository) -> None:
    _write_oxignore(tmp_repo, "")
    matcher = IgnoreMatcher.from_repo(tmp_repo)
    assert matcher.is_ignored(".git/HEAD")
    assert matcher.is_ignored(".oxidize/objects/aa")


def test_builtins_cannot_be_unignored(tmp_repo: Repository) -> None:
    _write_oxignore(tmp_repo, "!.git/\n")
    matcher = IgnoreMatcher.from_repo(tmp_repo)
    assert matcher.is_ignored(".git/HEAD")


def test_parent_dir_ignored(tmp_repo: Repository) -> None:
    _write_oxignore(tmp_repo, "build/\n")
    matcher = IgnoreMatcher.from_repo(tmp_repo)
    assert matcher.is_ignored("build/output.bin")
    assert matcher.is_ignored("build/sub/file.o")


def test_init_seeds_oxignore(tmp_path: Path) -> None:
    Repository.init(tmp_path)
    assert (tmp_path / ".oxignore").exists()
    content = (tmp_path / ".oxignore").read_text()
    assert "__pycache__/" in content
    assert ".env" in content


def test_init_does_not_overwrite_oxignore(tmp_path: Path) -> None:
    Repository.init(tmp_path)
    (tmp_path / ".oxignore").write_text("mine.txt\n")
    import pytest

    with pytest.raises(FileExistsError):
        Repository.init(tmp_path)
    assert (tmp_path / ".oxignore").read_text() == "mine.txt\n"


def test_starter_content_has_python_patterns() -> None:
    content = IgnoreMatcher.starter_content()
    for expected in ["__pycache__/", "*.pyc", ".venv/", "dist/", ".env"]:
        assert expected in content, f"missing {expected} in starter"


def test_add_skips_ignored_files(in_work_tree: Repository) -> None:
    tmp_repo = in_work_tree
    (tmp_repo.work_tree / "debug.log").write_text("noise\n")
    (tmp_repo.work_tree / "main.py").write_text("print('hi')\n")
    _write_oxignore(tmp_repo, "*.log\n")

    runner = CliRunner()
    result = runner.invoke(cli, ["add", "."], catch_exceptions=False)
    assert result.exit_code == 0, result.output + f"\n[exc={result.exception}]"

    assert "staged: main.py" in result.output
    assert "ignored: debug.log" in result.output


def test_add_force_stages_ignored(in_work_tree: Repository) -> None:
    tmp_repo = in_work_tree
    (tmp_repo.work_tree / "debug.log").write_text("noise\n")
    _write_oxignore(tmp_repo, "*.log\n")

    runner = CliRunner()
    result = runner.invoke(cli, ["add", "-f", "debug.log"], catch_exceptions=False)
    assert result.exit_code == 0, result.output + f"\n[exc={result.exception}]"
    assert "staged: debug.log" in result.output


def test_status_omits_ignored(in_work_tree: Repository) -> None:
    tmp_repo = in_work_tree
    (tmp_repo.work_tree / "main.py").write_text("x = 1\n")
    (tmp_repo.work_tree / "debug.log").write_text("noise\n")
    _write_oxignore(tmp_repo, "*.log\n")

    runner = CliRunner()
    result = runner.invoke(cli, ["status"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert "main.py" in result.output
    assert "debug.log" not in result.output


def test_ignores_list_command(in_work_tree: Repository) -> None:
    tmp_repo = in_work_tree
    _write_oxignore(tmp_repo, "*.log\nbuild/\n")

    runner = CliRunner()
    result = runner.invoke(cli, ["ignores", "list"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert "*.log" in result.output
    assert "build/" in result.output
    assert ".git/" in result.output


def test_ignores_check_command(in_work_tree: Repository) -> None:
    tmp_repo = in_work_tree
    (tmp_repo.work_tree / "secret.env").write_text("KEY=x\n")
    (tmp_repo.work_tree / "main.py").write_text("x = 1\n")
    _write_oxignore(tmp_repo, "*.env\n")

    runner = CliRunner()

    result_tracked = runner.invoke(cli, ["ignores", "check", "main.py"], catch_exceptions=False)
    assert result_tracked.exit_code == 0, result_tracked.output

    result_ignored = runner.invoke(cli, ["ignores", "check", "secret.env"], catch_exceptions=False)
    assert result_ignored.exit_code == 1
    assert "ignored" in result_ignored.output
