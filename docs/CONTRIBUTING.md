# contributing

## setup

```bash
git clone https://github.com/siddhant-bayas/oxidize
cd oxidize
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## running tests

```bash
pytest
pytest --cov=oxidize --cov-report=term-missing
```

## linting

```bash
ruff check oxidize tests
ruff format --check oxidize tests
mypy oxidize
```

## ci

pull requests run lint typecheck and tests on python 3.11 3.12 and 3.13

releases are published to pypi automatically via trusted publishing

## architecture principles

- no cross-module circular imports dependency order objects -> storage -> index -> core -> cli
- each subsystem must be testable in isolation
- repository is the only shared context do not use module-level globals
- keep cli commands thin logic belongs in core or the relevant subsystem

## adding a command

1. create oxidize/cli/commands/your_cmd.py with a click command named cmd_your_cmd
2. import and register in oxidize/cli/main.py
3. add integration tests in tests/
