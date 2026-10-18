from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from oxidize import lfs
from oxidize.cli.main import cli
from oxidize.core.repository import Repository


def test_store_and_resolve(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OXIDIZE_LFS_THRESHOLD", "10")
    repo = Repository.init(tmp_path)
    data = b"x" * 100
    oid, h = lfs.store(repo, data)
    assert lfs.is_pointer(repo.db.load_blob(oid).data)
    assert lfs.load_blob_data(repo, oid) == data
    assert lfs.parse_pointer(repo.db.load_blob(oid).data) == h


def test_cli_lfs_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OXIDIZE_LFS_THRESHOLD", "10")
    monkeypatch.chdir(tmp_path)
    Repository.init(tmp_path)
    (tmp_path / "big.txt").write_bytes(b"y" * 100)
    runner = CliRunner()
    res = runner.invoke(cli, ["add", "big.txt"], catch_exceptions=False)
    assert res.exit_code == 0, res.output
    res = runner.invoke(cli, ["commit", "-m", "lfs", "--agent", "t"], catch_exceptions=False)
    assert res.exit_code == 0, res.output
    (tmp_path / "big.txt").unlink()
    res = runner.invoke(cli, ["checkout", "main"], catch_exceptions=False)
    assert res.exit_code == 0, res.output
    assert (tmp_path / "big.txt").read_bytes() == b"y" * 100


def test_small_file_not_lfs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OXIDIZE_LFS_THRESHOLD", "10")
    Repository.init(tmp_path)
    data = b"hi"
    assert not lfs.is_large(data)
