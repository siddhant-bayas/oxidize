from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TextMergeResult:
    merged: str
    conflicted: bool


def three_way_text_merge(base: str, ours: str, theirs: str) -> TextMergeResult:
    """
    line-level three-way merge.

    rules:
      base == ours → use theirs
      base == theirs → use ours
      ours == theirs → use either
      otherwise → conflict, deferring to "ours" with markers
    """

    base_strip = _strip(base)
    ours_strip = _strip(ours)
    theirs_strip = _strip(theirs)

    if base_strip == ours_strip:
        return TextMergeResult(theirs, False)
    if base_strip == theirs_strip:
        return TextMergeResult(ours, False)
    if ours_strip == theirs_strip:
        return TextMergeResult(ours, False)

    suffix = ""
    if ours.endswith("\n") != theirs.endswith("\n"):
        suffix = "\n" if ours.endswith("\n") or theirs.endswith("\n") else ""

    merged = f"<<<<<<< OURS\n{ours}||||||| BASE\n{base}======= THEIRS\n{theirs}>>>>>>> THEIRS\n"
    if suffix:
        merged = merged.rstrip("\n") + suffix
    return TextMergeResult(merged, True)


def _strip(text: str) -> list[str]:
    return text.replace("\r\n", "\n").splitlines()


_BLOCK_RE = __import__("re").compile(r"^(<<<<<<<|=======|>>>>>>>)")


def is_conflict(text: str) -> bool:
    return any(_BLOCK_RE.match(line) for line in text.splitlines())
