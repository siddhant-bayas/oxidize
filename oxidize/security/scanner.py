from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oxidize.core.ignores import IgnoreMatcher


PATTERNS: dict[str, str] = {
    "AWS Access Key": r"AKIA[0-9A-Z]{16}",
    "AWS Secret Key": r"(?i)aws(.{0,20})?(secret|private)?(.{0,20})?['\"]([0-9a-zA-Z/+=]{40})['\"]",
    "GCP API Key": r"AIza[0-9A-Za-z\-_]{35}",
    "Google OAuth Token": r"ya29\.[0-9A-Za-z\-_]+",
    "GitHub PAT": r"ghp_[A-Za-z0-9]{36}",
    "GitHub Fine-Grained": r"github_pat_[A-Za-z0-9]{82}",
    "GitLab PAT": r"glpat-[a-zA-Z0-9\-_]{20,}",
    "Slack Token": r"xox[baprs]-[0-9a-zA-Z]{10,48}",
    "Slack Webhook": r"https://hooks\.slack\.com/services/T[A-Z0-9]{8,}/B[A-Z0-9]{8,}/[A-Za-z0-9]{24}",
    "Stripe Secret Key": r"sk_live_[0-9a-zA-Z]{24,}",
    "OpenAI API Key": r"sk-[A-Za-z0-9]{20}T3BlbkFJ[A-Za-z0-9]{20}",
    "OpenAI Project Key": r"sk-proj-[A-Za-z0-9\-_]{80,}",
    "Anthropic API Key": r"sk-ant-[A-Za-z0-9\-_]{80,}",
    "HuggingFace Token": r"hf_[A-Za-z0-9]{34}",
    "SendGrid API": r"SG\.[A-Za-z0-9\-_]{22,}\.[A-Za-z0-9\-_]{43,}",
    "Twilio SID": r"AC[a-zA-Z0-9_\-]{32}",
    "Mailgun API": r"key-[0-9a-zA-Z]{32}",
    "Generic API Key": r"(?i)(?:api[_-]?key|access[_-]?token|secret)[\s:=]+['\"]?([A-Za-z0-9_\-/+=]{20,})['\"]?",
    "Private Key Block": r"-----BEGIN\s+(RSA\s+|EC\s+|DSA\s+|OPENSSH\s+)?PRIVATE\s+KEY-----",
    "JWT Token": r"eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+",
    "Connection String": r"(?i)(?:postgres|mysql|mongodb|redis|amqp)://[^\s\"']+",
    "Bearer Token": r"(?i)bearer\s+[a-zA-Z0-9_\-\.]+",
    "Generic Password": r"(?i)(?:password|passwd|pwd|token|secret)[\s:=]+['\"]?([^\s'\"]{8,})['\"]?",
}

_COMPILED = {name: re.compile(p) for name, p in PATTERNS.items()}

_IGNORE_DIRS = {
    ".oxidize",
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".egg-info",
    "pyoxidize.egg-info",
    "oxidize.egg-info",
    "dist",
    "build",
}


def scan_text(text: str, filepath: str = "<input>") -> list[dict[str, str | int]]:
    findings: list[dict[str, str | int]] = []
    for name, pattern in _COMPILED.items():
        for match in pattern.finditer(text):
            line_num = text[: match.start()].count("\n") + 1
            matched = match.group()
            if len(matched) > 60:
                matched = matched[:60] + "..."
            findings.append({"type": name, "file": filepath, "line": line_num, "match": matched})
    return findings


def scan_file(path: Path, root: Path, *, is_ignored: bool = False) -> list[dict[str, str | int]]:
    if is_ignored:
        return []
    try:
        text = path.read_text(errors="replace")
    except (OSError, PermissionError):
        return []
    rel = path.relative_to(root).as_posix()
    return scan_text(text, rel)


def scan_directory(
    root: Path,
    ignore_matcher: "IgnoreMatcher | None" = None,
) -> list[dict[str, str | int]]:
    findings: list[dict[str, str | int]] = []
    for p in sorted(root.rglob("*")):
        if any(part in _IGNORE_DIRS for part in p.parts):
            continue
        if not p.is_file():
            continue
        try:
            rel = p.relative_to(root).as_posix()
        except ValueError:
            rel = p.as_posix()
        if ignore_matcher is not None and ignore_matcher.is_ignored(rel):
            continue
        findings.extend(scan_file(p, root))
    return findings


def scan_paths(
    paths: list[Path],
    root: Path,
    ignore_matcher: "IgnoreMatcher | None" = None,
) -> list[dict[str, str | int]]:
    findings: list[dict[str, str | int]] = []
    for p in paths:
        if not p.exists():
            continue
        try:
            rel = p.relative_to(root).as_posix()
        except ValueError:
            rel = p.as_posix()
        if ignore_matcher is not None and ignore_matcher.is_ignored(rel):
            continue
        if p.is_dir():
            findings.extend(scan_directory(p, ignore_matcher))
        else:
            findings.extend(scan_file(p, root))
    return findings
