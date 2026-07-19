"""Per-file git commits with minimal lowercase messages.

Splits directory adds into per-file commits so each entrypoint gets its own.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent  # project root (oxidize/)

MSGS: dict[str, str] = {
    "pyproject.toml": "add pathspec dep and mypy config",
    "README.md": "refresh readme with status table and why-not-git",
    "AGENTS.md": "add agents guide for oxi workflows",
    "src/main.py": "remove unused os import",
    "docs/cli-reference.md": "document oxignore and conflict resolution",
    "docs/security.md": "document scan oxignore integration",
    "docs/branching.md": "add branching and merge docs",
    "docs/ignores.md": "add oxignore documentation",
    "docs/workflow.md": "add workflow commands documentation",
    "docs/remote.md": "add filesystem remote docs",
    "oxidize/core/ignores.py": "add oxignore matcher",
    "oxidize/core/refs.py": "extend refstore with tags and delete",
    "oxidize/core/repository.py": "wire ignore matcher and seed oxignore",
    "oxidize/security/scanner.py": "respect oxignore in security scan",
    "oxidize/undo/reverser.py": "record commit message in undo journal",
    "oxidize/merge/text.py": "add three way text merge",
    "oxidize/merge/treewalk.py": "add merge base walker",
    "oxidize/network/__init__.py": "create network package",
    "oxidize/network/remote.py": "add filesystem remote sync",
    "oxidize/staging/__init__.py": "create staging package",
    "oxidize/staging/stash.py": "add stash snapshot helper",
    "oxidize/workflow/__init__.py": "create workflow package",
    "oxidize/workflow/bisect.py": "add bisect state helper",
    "oxidize/workflow/blame.py": "add line blamer",
    "oxidize/workflow/hooks.py": "add hooks runner",
    "oxidize/cli/commands/add.py": "support force flag and ignore filter",
    "oxidize/cli/commands/branch.py": "add branch command",
    "oxidize/cli/commands/bisect.py": "add bisect command",
    "oxidize/cli/commands/blame.py": "add blame command",
    "oxidize/cli/commands/checkout.py": "add checkout command",
    "oxidize/cli/commands/commit.py": "skip when no changes",
    "oxidize/cli/commands/diff.py": "filter diff by ignore matcher",
    "oxidize/cli/commands/hooks.py": "add hooks command",
    "oxidize/cli/commands/ignores.py": "add ignores command",
    "oxidize/cli/commands/init.py": "seed oxignore on init",
    "oxidize/cli/commands/log.py": "support agent and author filters",
    "oxidize/cli/commands/main.py": "register new commands",
    "oxidize/cli/commands/merge.py": "add merge command",
    "oxidize/cli/commands/notebook.py": "add notebook diff command",
    "oxidize/cli/commands/remote.py": "add remote command",
    "oxidize/cli/commands/repl.py": "update repl completer",
    "oxidize/cli/commands/resolve.py": "add resolve command",
    "oxidize/cli/commands/scan.py": "respect oxignore in scan",
    "oxidize/cli/commands/show.py": "add show command",
    "oxidize/cli/commands/stash.py": "add stash command",
    "oxidize/cli/commands/status.py": "filter status by ignore matcher",
    "oxidize/cli/commands/tag.py": "add tag command",
    "oxidize/cli/commands/undo.py": "add undo list subcommand",
    "tests/test_ignores.py": "add ignores tests",
    "tests/test_refs_branches_tags.py": "add branch and tag tests",
    "tests/test_workflow.py": "add stash hooks and bisect tests",
    "tests/test_merge_conflict_blame_remote.py": "add merge and blame tests",
    "tests/test_scanner.py": "extend scanner tests with oxignore",
    "tests/test_notebook.py": "annotate notebook tests",
}

SKIP_DIRS = {
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "dist",
    "build",
    "pyoxidize.egg-info",
    "oxidize.egg-info",
    ".oxidize",
    ".git",
}


def run(*args: str, cwd: Path = REPO) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def list_pending() -> list[str]:
    out = run("status", "--porcelain").stdout
    items: list[str] = []
    for line in out.splitlines():
        if not line:
            continue
        # line format: 'XY <path>'
        # `XY` may contain trailing space for renames, eg. `R  old -> new`
        path = line[3:].strip()
        path = path.strip('"')
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip().strip('"')
        items.append(path.replace("\\", "/"))

    expanded: list[str] = []
    for path in items:
        full = REPO / path
        if full.is_dir():
            for child in sorted(full.rglob("*")):
                if child.is_file():
                    rel = child.relative_to(REPO).as_posix()
                    if all(part not in SKIP_DIRS for part in child.relative_to(REPO).parts):
                        expanded.append(rel)
        else:
            if all(part not in SKIP_DIRS for part in Path(path).parts):
                expanded.append(path)

    seen: set[str] = set()
    unique: list[str] = []
    for p in expanded:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def commit_one(rel: str) -> None:
    msg = MSGS.get(rel, f"add {rel}")
    add = run("add", "--", rel)
    if add.returncode != 0:
        print(f"  add-fail [{rel}]: {add.stderr.strip()}")
        sys.exit(1)
    commit = run(
        "commit",
        "-m",
        msg,
        "--no-verify",
    )
    if commit.returncode != 0:
        print(f"  commit-fail [{rel}]: {commit.stderr.strip() or commit.stdout.strip()}")
        sys.exit(1)
    short = run("rev-parse", "--short", "HEAD").stdout.strip()
    print(f"  [{short}] {rel}")


def main() -> None:
    count = 0
    for rel in list_pending():
        commit_one(rel)
        count += 1
    print(f"\ncommitted {count} files individually")


if __name__ == "__main__":
    main()
