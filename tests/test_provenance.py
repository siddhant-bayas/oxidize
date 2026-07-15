from __future__ import annotations

from pathlib import Path

from oxidize.provenance.agent import AgentRecord, ProvenanceStore, detect_agent


def test_agent_record_roundtrip() -> None:
    r = AgentRecord(
        agent="claude-code", timestamp=1700000000.0, commit_oid="abc123", message="fix bug"
    )
    d = r.to_dict()
    r2 = AgentRecord.from_dict(d)
    assert r2.agent == "claude-code"
    assert r2.commit_oid == "abc123"


def test_provenance_store_record_and_query(tmp_path: Path) -> None:
    store = ProvenanceStore(tmp_path / "agents.json")
    store.record("claude-code", "abc123", "fix bug")
    store.record("aider", "def456", "add feature")
    store.record("claude-code", "ghi789", "refactor")

    assert len(store.all_records()) == 3
    assert set(store.all_agents()) == {"claude-code", "aider"}
    assert len(store.by_agent("claude-code")) == 2


def test_provenance_persistence(tmp_path: Path) -> None:
    path = tmp_path / "agents.json"
    s1 = ProvenanceStore(path)
    s1.record("test-agent", "oid1", "msg1")
    s2 = ProvenanceStore(path)
    assert len(s2.all_records()) == 1


def test_detect_agent_returns_none_by_default() -> None:
    import os

    for key in ["CLAUDE_CODE", "GITHUB_COPILOT", "CODEX_AGENT", "AIDER"]:
        os.environ.pop(key, None)
    assert detect_agent() is None
