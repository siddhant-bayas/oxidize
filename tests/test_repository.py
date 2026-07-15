from pathlib import Path
import pytest
from oxidize.core.repository import Repository, RepositoryNotFound


def test_init_creates_structure(tmp_path: Path) -> None:
    Repository.init(tmp_path)
    assert (tmp_path / ".oxidize" / "objects").is_dir()
    assert (tmp_path / ".oxidize" / "HEAD").exists()


def test_init_twice_raises(tmp_path: Path) -> None:
    Repository.init(tmp_path)
    with pytest.raises(FileExistsError):
        Repository.init(tmp_path)


def test_discover_from_subdir(tmp_path: Path) -> None:
    Repository.init(tmp_path)
    subdir = tmp_path / "src" / "deep"
    subdir.mkdir(parents=True)
    repo = Repository.discover(subdir)
    assert repo.work_tree == tmp_path


def test_discover_fails_outside_repo(tmp_path: Path) -> None:
    with pytest.raises(RepositoryNotFound):
        Repository.discover(tmp_path)


def test_empty_repo(tmp_repo: Repository) -> None:
    assert tmp_repo.is_empty()
    assert tmp_repo.refs.current_branch() == "main"
