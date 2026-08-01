from pathlib import Path

import pytest

from oxidize.core.repository import Repository


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Repository:
    return Repository.init(tmp_path)
