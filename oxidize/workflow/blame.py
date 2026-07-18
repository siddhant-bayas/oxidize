from __future__ import annotations

from oxidize.core.repository import Repository
from oxidize.objects.types import Tree


class Blamer:
    def __init__(self, repo: Repository) -> None:
        self._repo = repo

    def annotate(self, path: str) -> list[tuple[str, str]]:
        result: list[tuple[str, str]] = []
        for oid in self._history():
            try:
                commit = self._repo.db.load_commit(oid)
                tree = self._repo.db.load_tree(commit.tree_oid)
                blob_text = self._blob_for_path(tree, path)
            except Exception:
                continue
            if blob_text is None:
                continue
            for line in blob_text.splitlines():
                result.append((oid[:8], line))
        return result

    def _history(self) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        head = self._repo.refs.head()
        stack = [head] if head else []
        while stack:
            oid = stack.pop()
            if oid in seen or not oid:
                continue
            seen.add(oid)
            out.append(oid)
            try:
                commit = self._repo.db.load_commit(oid)
            except Exception:
                continue
            stack.extend(commit.parents)
        return out

    def _blob_for_path(self, tree: Tree, path: str) -> str | None:
        parts = path.split("/")
        node = tree
        for i, name in enumerate(parts):
            entry = next((e for e in node if e.name == name), None)
            if entry is None:
                return None
            if i == len(parts) - 1:
                if entry.mode.value == "040000":
                    return None
                try:
                    blob = self._repo.db.load_blob(entry.oid)
                except Exception:
                    return None
                return blob.data.decode(errors="replace")
            if entry.mode.value != "040000":
                return None
            try:
                node = self._repo.db.load_tree(entry.oid)
            except Exception:
                return None
        return None
