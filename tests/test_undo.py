from __future__ import annotations

from pathlib import Path

from oxidize.core.repository import Repository
from oxidize.undo.journal import Journal
from oxidize.undo.reverser import UndoManager


def test_journal_record_and_retrieve(tmp_path: Path) -> None:
    journal = Journal(tmp_path / "journal.json")
    journal.record("test_op", {"key": "value"}, {"key": "undo_value"})
    assert len(journal) == 1
    entry = journal.last()
    assert entry is not None
    assert entry.op == "test_op"
    assert entry.data == {"key": "value"}


def test_journal_persistence(tmp_path: Path) -> None:
    path = tmp_path / "journal.json"
    j1 = Journal(path)
    j1.record("op1", {}, {})
    j2 = Journal(path)
    assert len(j2) == 1


def test_journal_pop_last(tmp_path: Path) -> None:
    journal = Journal(tmp_path / "journal.json")
    journal.record("op1", {"a": 1}, {})
    journal.record("op2", {"b": 2}, {})
    entry = journal.pop_last()
    assert entry is not None
    assert entry.op == "op2"
    assert len(journal) == 1


def test_undo_commit(tmp_path: Path) -> None:
    repo = Repository.init(tmp_path)
    (tmp_path / "file.txt").write_text("hello")
    repo.db.store_blob(b"hello")

    mgr = UndoManager(repo)
    mgr.record_commit("abc123" * 11, "prev_head_oid")

    messages = mgr.undo(1)
    assert len(messages) == 1
    assert "undid commit" in messages[0]


def test_undo_add(tmp_path: Path) -> None:
    repo = Repository.init(tmp_path)
    mgr = UndoManager(repo)
    mgr.record_add(["file.txt"], ["oid123"])

    messages = mgr.undo(1)
    assert "unstaged" in messages[0]


def test_undo_empty(tmp_path: Path) -> None:
    repo = Repository.init(tmp_path)
    mgr = UndoManager(repo)
    messages = mgr.undo(1)
    assert "nothing to undo" in messages[0]
