from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class AgentRecord:
    agent: str
    timestamp: float
    commit_oid: str
    message: str
    prompt_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AgentRecord:
        return cls(
            agent=str(d["agent"]),
            timestamp=float(d["timestamp"]),
            commit_oid=str(d["commit_oid"]),
            message=str(d["message"]),
            prompt_id=str(d["prompt_id"]) if d.get("prompt_id") else None,
        )
        return cls(**d)


class ProvenanceStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._records: list[AgentRecord] = []
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        data = json.loads(self._path.read_text())
        self._records = [AgentRecord.from_dict(r) for r in data]

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps([r.to_dict() for r in self._records], indent=2))

    def record(
        self, agent: str, commit_oid: str, message: str, prompt_id: str | None = None
    ) -> None:
        entry = AgentRecord(
            agent=agent,
            timestamp=time.time(),
            commit_oid=commit_oid,
            message=message,
            prompt_id=prompt_id,
        )
        self._records.append(entry)
        self._save()

    def by_agent(self, agent: str) -> list[AgentRecord]:
        return [r for r in self._records if r.agent == agent]

    def all_agents(self) -> list[str]:
        return list({r.agent for r in self._records})

    def all_records(self) -> list[AgentRecord]:
        return list(self._records)


def detect_agent() -> str | None:
    if os.environ.get("CLAUDE_CODE"):
        return "claude-code"
    if os.environ.get("GITHUB_COPILOT"):
        return "github-copilot"
    if os.environ.get("CODEX_AGENT"):
        return "codex"
    if os.environ.get(" Cursor"):
        return "cursor"
    if os.environ.get("AIDER"):
        return "aider"
    return None
