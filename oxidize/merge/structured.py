from __future__ import annotations

import copy
from typing import Any


def deep_merge(base: dict[str, Any], head: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in head.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(dict(result[key]), dict(value))
        else:
            result[key] = copy.deepcopy(value)
    return result


def three_way_merge(
    base: dict[str, Any], ours: dict[str, Any], theirs: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    result = copy.deepcopy(base)
    conflicts: list[str] = []
    all_keys = set(base) | set(ours) | set(theirs)

    for key in sorted(all_keys):
        in_base = key in base
        in_ours = key in ours
        in_theirs = key in theirs

        if in_ours and not in_theirs:
            result[key] = copy.deepcopy(ours[key])
        elif in_theirs and not in_ours:
            result[key] = copy.deepcopy(theirs[key])
        elif not in_ours and not in_theirs:
            result.pop(key, None)
        elif in_base:
            if base[key] == ours[key]:
                result[key] = copy.deepcopy(theirs[key])
            elif base[key] == theirs[key]:
                result[key] = copy.deepcopy(ours[key])
            else:
                if isinstance(ours[key], dict) and isinstance(theirs[key], dict):
                    merged, sub_conflicts = three_way_merge(base[key], ours[key], theirs[key])
                    result[key] = merged
                    conflicts.extend(f"{key}.{c}" for c in sub_conflicts)
                else:
                    conflicts.append(key)
                    result[key] = ours[key]
        else:
            if ours[key] == theirs[key]:
                result[key] = copy.deepcopy(ours[key])
            else:
                conflicts.append(key)
                result[key] = ours[key]

    return result, conflicts
