from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from oxidize.core.repository import Repository


@dataclass
class HookResult:
    name: str
    exit_code: int
    stdout: str
    stderr: str


_HOOK_NAMES: tuple[str, ...] = (
    "pre-commit",
    "post-commit",
    "pre-add",
    "post-add",
    "pre-merge",
    "post-merge",
)


_HOOK_SUFFIXES = (".py", ".sh", ".bat", ".cmd", "")


def find_hook_file(hooks_dir: Path, name: str) -> Path | None:
    for suffix in _HOOK_SUFFIXES:
        candidate = hooks_dir / f"{name}{suffix}"
        if candidate.exists():
            return candidate
    return None


class Hooks:
    def __init__(self, repo: Repository) -> None:
        self._dir = repo.oxidize_dir / "hooks"
        self._dir.mkdir(parents=True, exist_ok=True)

    def list_hooks(self) -> dict[str, Path | None]:
        out: dict[str, Path | None] = {}
        for name in _HOOK_NAMES:
            out[name] = find_hook_file(self._dir, name)
        return out

    def install_template(self, name: str) -> Path:
        existing = find_hook_file(self._dir, name)
        if existing is not None:
            return existing
        path = self._dir / f"{name}.sh"
        path.write_text("#!/usr/bin/env sh\n# exit non-zero to block\n")
        try:
            path.chmod(0o755)
        except OSError:
            pass
        return path

    def run(
        self, name: str, args: Iterable[str] = (), env: dict[str, str] | None = None
    ) -> HookResult:
        hooks_dir = self._dir
        path = find_hook_file(hooks_dir, name)
        if path is None:
            return HookResult(name=name, exit_code=0, stdout="", stderr="")
        cmd, _exe = _select_runner(path)
        if cmd is None:
            return HookResult(
                name=name,
                exit_code=126,
                stdout="",
                stderr="hook script not executable on this platform",
            )
        try:
            proc = subprocess.run(
                cmd,
                cwd=self._repo_root(),
                capture_output=True,
                env={**__import__("os").environ, **(env or {})},
                text=True,
            )
        except OSError as e:
            return HookResult(name=name, exit_code=127, stdout="", stderr=str(e))
        return HookResult(
            name=name,
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )

    def _repo_root(self) -> Path:
        return self._dir.parent.parent


def _select_runner(path: Path) -> tuple[list[str] | None, str]:
    import os
    import sys

    suffix = path.suffix.lower()
    if suffix == ".py":
        return [sys.executable, str(path)], "python"
    if os.name == "nt":
        if suffix in ("", ".bat", ".cmd"):
            return ["cmd", "/c", str(path)], "cmd"
        return [str(path)], suffix or "exe"
    return [str(path)], "shell"


def run_hooks(
    repo: Repository, name: str, args: Iterable[str] = (), *, blocking: bool = True
) -> list[HookResult]:
    h = Hooks(repo)
    if find_hook_file(h._dir, name) is None:
        return []
    result = h.run(name, args)
    if result.exit_code != 0 and blocking:
        raise RuntimeError(f"hook {name} failed (exit {result.exit_code}): {result.stderr.strip()}")
    return [result]
