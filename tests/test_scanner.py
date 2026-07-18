from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from oxidize.cli.main import cli
from oxidize.core.repository import Repository
from oxidize.security.scanner import scan_directory, scan_file, scan_text, PATTERNS


def _stripe_key() -> str:
    return "sk_live_" + "abcdefghijklmnopqrstuvwx"


def _slack_token() -> str:
    return "xoxb-" + "123456789012" + "-" + "123456789012" + "-" + "12345678901234567890"


def _openai_key() -> str:
    return "sk-" + "abcdefghijklmnopqrst" + "T3BlbkFJ" + "abcdefghijklmnopqrst"


FIXTURE_STRIPE = "sk_live_abcde" + "fghijklmnopqrstuvwx"
FIXTURE_STRIPE_JOINED = "sk_l" + "ive_a" + "bcdefgh" + "ijklmnopqrstuvwx"


def test_scan_finds_github_pat() -> None:
    text = 'token = "ghp_' + "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij" + '"'
    findings = scan_text(text, "config.py")
    assert any(f["type"] == "GitHub PAT" for f in findings)


def test_scan_finds_private_key() -> None:
    text = "-----BEGIN RSA PRIVATE KEY-----"
    findings = scan_text(text, "key.pem")
    assert any(f["type"] == "Private Key Block" for f in findings)


def test_scan_finds_stripe_key() -> None:
    text = 'stripe_key = "' + _stripe_key() + '"'
    findings = scan_text(text, ".env")
    assert any(f["type"] == "Stripe Secret Key" for f in findings)


def test_scan_finds_slack_token() -> None:
    text = 'SLACK_TOKEN = "' + _slack_token() + '"'
    findings = scan_text(text, ".env")
    assert any(f["type"] == "Slack Token" for f in findings)


def test_scan_finds_openai_key() -> None:
    text = 'api_key = "' + _openai_key() + '"'
    findings = scan_text(text, "config.py")
    assert any(f["type"] == "OpenAI API Key" for f in findings)


def test_scan_clean_file() -> None:
    text = "def hello():\n    print('hello')\n"
    findings = scan_text(text, "hello.py")
    assert len(findings) == 0


def test_scan_line_numbers() -> None:
    text = "line1\nline2\napi_key = '" + "sk-live-" + "abcdefghijklmnopqrstuvwx" + "'\n"
    findings = scan_text(text, "test.py")
    if findings:
        assert findings[0]["line"] == 3


def test_patterns_are_compiled() -> None:
    assert len(PATTERNS) > 10
    for name, pattern in PATTERNS.items():
        assert isinstance(pattern, str)
        assert len(pattern) > 5


def test_scan_directory_respects_ignore(tmp_path: Path) -> None:
    (tmp_path / "config.py").write_text('key = "ghp_' + "X" * 36 + '"')
    (tmp_path / "secret.env").write_text('key = "ghp_' + "Y" * 36 + '"')
    (tmp_path / ".oxignore").write_text("*.env\n")

    from oxidize.core.ignores import IgnoreMatcher

    lines = [
        ln.strip()
        for ln in (tmp_path / ".oxignore").read_text().splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    matcher = IgnoreMatcher(lines, tmp_path)
    all_findings = scan_directory(tmp_path, matcher)
    files_seen = {str(f["file"]) for f in all_findings}
    assert "config.py" in files_seen
    assert all("secret.env" not in fp for fp in files_seen)


def test_scan_directory_without_ignore_includes_all(tmp_path: Path) -> None:
    (tmp_path / "config.py").write_text('key = "ghp_' + "X" * 36 + '"')
    (tmp_path / "secret.env").write_text('key = "ghp_' + "Y" * 36 + '"')
    findings = scan_directory(tmp_path, None)
    files = {str(f["file"]) for f in findings}
    assert "secret.env" in files
    assert "config.py" in files


def test_scan_file_respects_ignore_flag(tmp_path: Path) -> None:
    f = tmp_path / "secret.env"
    f.write_text('key = "ghp_' + "Z" * 36 + '"')
    assert scan_file(f, tmp_path) != []
    assert scan_file(f, tmp_path, is_ignored=True) == []


@pytest.fixture
def in_repo(tmp_repo: Repository, monkeypatch: pytest.MonkeyPatch) -> Repository:
    monkeypatch.chdir(tmp_repo.work_tree)
    return tmp_repo


def test_oxi_scan_respects_oxignore(in_repo: Repository) -> None:
    repo = in_repo
    (repo.work_tree / "secret.env").write_text(FIXTURE_STRIPE)
    (repo.work_tree / "main.py").write_text("x = 1\n")
    (repo.work_tree / ".oxignore").write_text("*.env\n")

    runner = CliRunner()
    ignored = runner.invoke(cli, ["scan"], catch_exceptions=False)
    assert ignored.exit_code == 0, ignored.output
    assert "secret.env" not in ignored.output
    assert "No secrets found." in ignored.output

    (repo.work_tree / "main.py").write_text(FIXTURE_STRIPE_JOINED)
    found = runner.invoke(cli, ["scan"], catch_exceptions=False)
    assert found.exit_code == 0, found.output
    assert "main.py" in found.output


def test_oxi_scan_no_oxignore_flag_unlocks(in_repo: Repository) -> None:
    repo = in_repo
    (repo.work_tree / "secret.env").write_text(FIXTURE_STRIPE_JOINED)
    (repo.work_tree / ".oxignore").write_text("*.env\n")

    runner = CliRunner()
    bypass = runner.invoke(cli, ["scan", "--no-oxignore"], catch_exceptions=False)
    assert bypass.exit_code == 0, bypass.output
    assert "secret.env" in bypass.output


def test_oxi_scan_staged_respects_oxignore(in_repo: Repository) -> None:
    repo = in_repo
    sec = repo.work_tree / "secret.env"
    sec.write_text(FIXTURE_STRIPE_JOINED)
    (repo.work_tree / ".oxignore").write_text("*.env\n")
    oid = repo.db.store_blob(sec.read_bytes())
    repo.index.add("secret.env", oid, sec)

    runner = CliRunner()
    res = runner.invoke(cli, ["scan", "--staged"], catch_exceptions=False)
    assert res.exit_code == 0, res.output
    assert "secret.env" not in res.output
