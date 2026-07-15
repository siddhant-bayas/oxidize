from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence


class LineOp(str, Enum):
    EQUAL = "equal"
    INSERT = "insert"
    DELETE = "delete"


@dataclass(frozen=True)
class DiffLine:
    op: LineOp
    content: str
    old_lineno: int | None = None
    new_lineno: int | None = None


def diff_lines(old: str, new: str) -> list[DiffLine]:
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    return _myers(old_lines, new_lines)


def _myers(a: Sequence[str], b: Sequence[str]) -> list[DiffLine]:
    """Myers diff algorithm — O(ND) where D is edit distance."""
    n, m = len(a), len(b)
    max_d = n + m
    if max_d == 0:
        return []

    v: dict[int, int] = {1: 0}
    trace: list[dict[int, int]] = []

    for d in range(max_d + 1):
        trace.append(dict(v))
        for k in range(-d, d + 1, 2):
            if k == -d or (k != d and v.get(k - 1, -1) < v.get(k + 1, -1)):
                x = v.get(k + 1, 0)
            else:
                x = v.get(k - 1, 0) + 1
            y = x - k
            while x < n and y < m and a[x] == b[y]:
                x += 1
                y += 1
            v[k] = x
            if x >= n and y >= m:
                return _backtrack(a, b, trace, d)
    return []


def _backtrack(
    a: Sequence[str], b: Sequence[str], trace: list[dict[int, int]], d: int
) -> list[DiffLine]:
    x, y = len(a), len(b)
    result: list[DiffLine] = []

    for current_d in range(d, 0, -1):
        v = trace[current_d]
        k = x - y
        if k == -current_d or (k != current_d and v.get(k - 1, -1) < v.get(k + 1, -1)):
            prev_k = k + 1
        else:
            prev_k = k - 1

        prev_x = v.get(prev_k, 0)
        prev_y = prev_x - prev_k

        while x > prev_x and y > prev_y:
            x -= 1
            y -= 1
            result.append(DiffLine(LineOp.EQUAL, a[x], old_lineno=x + 1, new_lineno=y + 1))

        if current_d > 0:
            if x == prev_x:
                y -= 1
                result.append(DiffLine(LineOp.INSERT, b[y], new_lineno=y + 1))
            else:
                x -= 1
                result.append(DiffLine(LineOp.DELETE, a[x], old_lineno=x + 1))

    while x > 0 and y > 0:
        x -= 1
        y -= 1
        result.append(DiffLine(LineOp.EQUAL, a[x], old_lineno=x + 1, new_lineno=y + 1))

    result.reverse()
    return result
