from __future__ import annotations

from pathlib import Path


class RefStore:
    def __init__(self, git_dir: Path) -> None:
        self._root = git_dir

    def _ref_path(self, name: str) -> Path:
        return self._root / name

    def read(self, name: str) -> str | None:
        path = self._ref_path(name)
        if not path.exists():
            return None
        content = path.read_text().strip()
        if content.startswith("ref: "):
            return self.read(content[5:])
        return content

    def write(self, name: str, oid: str) -> None:
        path = self._ref_path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(oid + "\n")

    def head(self) -> str | None:
        return self.read("HEAD")

    def set_head_branch(self, branch: str) -> None:
        (self._root / "HEAD").write_text(f"ref: refs/heads/{branch}\n")

    def current_branch(self) -> str | None:
        head_path = self._root / "HEAD"
        if not head_path.exists():
            return None
        content = head_path.read_text().strip()
        if content.startswith("ref: refs/heads/"):
            return content[len("ref: refs/heads/") :]
        return None  # detached HEAD

    def update_head(self, oid: str) -> None:
        head_path = self._root / "HEAD"
        content = head_path.read_text().strip()
        if content.startswith("ref: "):
            self.write(content[5:], oid)
        else:
            head_path.write_text(oid + "\n")

    def list_branches(self) -> list[str]:
        branches_dir = self._root / "refs" / "heads"
        if not branches_dir.exists():
            return []
        return [p.name for p in branches_dir.iterdir() if p.is_file()]
