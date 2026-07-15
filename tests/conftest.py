import pytest
from pathlib import Path
from oxidize.core.repository import Repository


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Repository:
    return Repository.init(tmp_path)
