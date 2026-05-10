# Contributing

## Setup

```bash
git clone https://github.com/yourname/oxide
cd oxide
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest
pytest --cov=oxide --cov-report=term-missing
```

## Linting

```bash
ruff check oxide tests
mypy oxide
```

## Architecture Principles

- No cross-module circular imports. Dependency order: `objects → storage → index → core → cli`
- Each subsystem must be testable in isolation
- `Repository` is the only shared context — don't use module-level globals
- Keep CLI commands thin — logic belongs in `core` or the relevant subsystem

## Adding a Command

1. Create `oxide/cli/commands/your_cmd.py` with a Click command named `cmd_your_cmd`
2. Import and register in `oxide/cli/main.py`
3. Add integration tests in `tests/`
