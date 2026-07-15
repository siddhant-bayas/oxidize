from __future__ import annotations

from oxidize.core.repository import Repository
from oxidize.undo.journal import Journal, JournalEntry, OpType


class UndoManager:
    def __init__(self, repo: Repository) -> None:
        self._repo = repo
        self._journal = Journal(repo.oxidize_dir / "journal.json")

    @property
    def journal(self) -> Journal:
        return self._journal

    def record_add(self, paths: list[str], oids: list[str]) -> None:
        self._journal.record(
            op=OpType.ADD,
            data={"paths": paths, "oids": oids},
            undo_data={"paths": paths},
        )

    def record_commit(self, commit_oid: str, prev_head: str | None) -> None:
        self._journal.record(
            op=OpType.COMMIT,
            data={"commit_oid": commit_oid, "prev_head": prev_head},
            undo_data={"commit_oid": commit_oid, "restore_to": prev_head},
        )

    def record_branch_create(self, branch: str, oid: str) -> None:
        self._journal.record(
            op=OpType.BRANCH_CREATE,
            data={"branch": branch, "oid": oid},
            undo_data={"branch": branch},
        )

    def record_branch_delete(self, branch: str, oid: str) -> None:
        self._journal.record(
            op=OpType.BRANCH_DELETE,
            data={"branch": branch, "oid": oid},
            undo_data={"branch": branch, "oid": oid},
        )

    def undo(self, count: int = 1) -> list[str]:
        messages: list[str] = []
        for _ in range(count):
            entry = self._journal.pop_last()
            if not entry:
                messages.append("nothing to undo")
                break
            msgs = self._apply_undo(entry)
            messages.extend(msgs)
        return messages

    def _apply_undo(self, entry: JournalEntry) -> list[str]:
        msgs: list[str] = []
        if entry.op == OpType.COMMIT:
            restore_to = entry.undo_data.get("restore_to")
            if restore_to:
                self._repo.refs.update_head(str(restore_to))
                msgs.append(f"undid commit {str(entry.data.get('commit_oid', ''))[:8]}")
            else:
                head_path = self._repo.oxidize_dir / "HEAD"
                head_path.write_text("ref: refs/heads/main\n")
                ref_path = self._repo.oxidize_dir / "refs" / "heads" / "main"
                if ref_path.exists():
                    ref_path.unlink()
                msgs.append(f"undid initial commit {str(entry.data.get('commit_oid', ''))[:8]}")

        elif entry.op == OpType.ADD:
            paths = entry.undo_data.get("paths", [])
            for p in paths:
                self._repo.index.remove(str(p))
            msgs.append(f"unstaged {len(paths)} file(s)")

        elif entry.op == OpType.BRANCH_CREATE:
            branch = entry.undo_data.get("branch")
            if branch:
                ref_path = self._repo.oxidize_dir / "refs" / "heads" / str(branch)
                if ref_path.exists():
                    ref_path.unlink()
                msgs.append(f"deleted branch '{branch}'")

        elif entry.op == OpType.BRANCH_DELETE:
            branch = entry.undo_data.get("branch")
            oid = entry.undo_data.get("oid")
            if branch and oid:
                self._repo.refs.write(f"refs/heads/{branch}", str(oid))
                msgs.append(f"restored branch '{branch}'")
        else:
            msgs.append(f"cannot undo {entry.op}")

        return msgs
