from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pathspec

if TYPE_CHECKING:
    from oxidize.core.repository import Repository


_BUILTIN_PATTERNS = (
    ".git/",
    ".oxidize/",
)


_STARTER_OXIGNORE = """\
# python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.egg-info/
.eggs/

# virtualenvs
.venv/
venv/
env/

# build output
dist/
build/

# testing / linting caches
.mypy_cache/
.pytest_cache/
.ruff_cache/
.coverage
htmlcov/

# environment
.env
.env.*

# editor / OS
.vscode/
.idea/
.DS_Store
"""


class IgnoreMatcher:
    def __init__(self, patterns: list[str], work_tree: Path) -> None:
        self._work_tree = work_tree
        self._patterns = list(patterns)
        self._user_spec: Any = pathspec.PathSpec.from_lines("gitignore", patterns)
        self._builtin_spec: Any = pathspec.PathSpec.from_lines(
            "gitignore", _BUILTIN_PATTERNS
        )

    @classmethod
    def from_repo(cls, repo: Repository) -> IgnoreMatcher:
        ignore_file = repo.work_tree / ".oxignore"
        patterns: list[str] = []
        if ignore_file.is_file():
            for raw in ignore_file.read_text().splitlines():
                stripped = raw.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                patterns.append(stripped)
        return cls(patterns, repo.work_tree)

    def is_ignored(self, rel_path: str) -> bool:
        if self._builtin_spec.match_file(rel_path):
            return True
        if self._user_spec.match_file(rel_path):
            return True
        return _parent_dir_ignored(rel_path, self._user_spec)

    def filter(self, paths: list[Path]) -> list[Path]:
        keep: list[Path] = []
        for p in paths:
            try:
                rel = p.relative_to(self._work_tree).as_posix()
            except ValueError:
                continue
            if not self.is_ignored(rel):
                keep.append(p)
        return keep

    def patterns(self) -> list[str]:
        return list(self._patterns)

    def builtin_patterns(self) -> tuple[str, ...]:
        return _BUILTIN_PATTERNS

    @staticmethod
    def starter_content() -> str:
        return _STARTER_OXIGNORE


def _parent_dir_ignored(rel_path: str, spec: Any) -> bool:
    parts = rel_path.split("/")
    for i in range(1, len(parts)):
        candidate = "/".join(parts[:i])
        if spec.match_file(candidate):
            return True
    return False
