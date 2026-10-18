from __future__ import annotations

from typing import Callable

from pathlib import PurePosixPath


def _basename(path: str) -> str:
    return PurePosixPath(path).name


def detect_renames(
    base_paths: set[str],
    side_paths: set[str],
    get_base: Callable[[str], str],
    get_side: Callable[[str], str],
) -> dict[str, str]:
    """Return mapping of base path -> side path for renamed files."""
    renames: dict[str, str] = {}
    deleted = base_paths - side_paths
    added = set(side_paths - base_paths)

    # 1. exact content match (pure rename)
    added_by_content: dict[str, list[str]] = {}
    for a in added:
        added_by_content.setdefault(get_side(a), []).append(a)

    for d in list(deleted):
        content = get_base(d)
        candidates = added_by_content.get(content, [])
        if len(candidates) == 1:
            renames[d] = candidates[0]
            deleted.discard(d)
            added.discard(candidates[0])

    # 2. same basename, single candidate
    by_name: dict[str, list[str]] = {}
    for a in added:
        by_name.setdefault(_basename(a), []).append(a)

    for d in list(deleted):
        candidates = by_name.get(_basename(d), [])
        if len(candidates) == 1:
            renames[d] = candidates[0]
            deleted.discard(d)
            added.discard(candidates[0])

    return renames
