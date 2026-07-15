# AI agent provenance

oxidize can track which AI agent or tool produced each commit. this creates an audit trail of AI-generated changes.

## usage

### manual tagging

tag a commit with the agent name:

```bash
oxidize commit -m "refactor function" --agent "claude-code"
oxidize commit -m "fix lint errors" --agent "cursor"
oxidize commit -m "add tests" --agent "github-copilot"
```

### auto-detection

oxidize checks environment variables to automatically detect the running agent:

| env var | detected agent |
|---------|---------------|
| `CLAUDE_CODE` | `claude-code` |
| `GITHUB_COPILOT` | `github-copilot` |
| `CODEX_AGENT` | `codex` |
| `AIDER` | `aider` |

if you're running inside one of these tools, the agent tag is added automatically.

### manual query

```python
from pathlib import Path
from oxidize.provenance.agent import ProvenanceStore

store = ProvenanceStore(Path(".oxidize/provenance.json"))

# record an action
store.record(
    agent="claude-code",
    commit_oid="abc123...",
    message="refactor function"
)

# query
records = store.by_agent("claude-code")
all_agents = store.all_agents()
all_records = store.all_records()
```

## AgentRecord

| field | type | description |
|-------|------|-------------|
| `agent` | `str` | agent/tool name (e.g. `"claude-code"`) |
| `timestamp` | `float` | unix timestamp |
| `commit_oid` | `str` | oid of the commit produced |
| `message` | `str` | commit message |
| `prompt_id` | `str \| None` | optional prompt/session identifier |

## ProvenanceStore

| method | signature | description |
|--------|-----------|-------------|
| `record` | `record(agent, commit_oid, message, prompt_id=None)` | record an agent action |
| `by_agent` | `by_agent(agent) -> list[AgentRecord]` | filter by agent name |
| `all_agents` | `all_agents() -> list[str]` | list all agent names |
| `all_records` | `all_records() -> list[AgentRecord]` | all records |

## storage

provenance records are stored at `.oxidize/provenance.json` as a JSON array.

## detect_agent

```python
from oxidize.provenance.agent import detect_agent

agent = detect_agent()
# returns "claude-code", "github-copilot", "codex", "aider", or None
```

this checks the environment variables listed above. useful for conditionally adding provenance metadata.

## example workflow

```bash
# you're running inside claude-code
# CLAUDE_CODE env var is set

oxidize add new_feature.py
oxidize commit -m "add new feature"
# agent is auto-detected and tagged

# later, query who did what
oxidize log
# shows "[claude-code]" next to AI-generated commits
```
