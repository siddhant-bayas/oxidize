from __future__ import annotations

from oxidize.merge.rename import detect_renames


def test_pure_rename_by_content() -> None:
    base = {"old.txt": "hello\n"}
    side = {"new.txt": "hello\n"}
    renames = detect_renames(
        set(base), set(side), lambda p: base[p], lambda p: side[p]
    )
    assert renames == {"old.txt": "new.txt"}


def test_rename_by_basename() -> None:
    base = {"dir/old.txt": "v1\n"}
    side = {"other/old.txt": "v2\n"}
    renames = detect_renames(
        set(base), set(side), lambda p: base[p], lambda p: side[p]
    )
    assert renames == {"dir/old.txt": "other/old.txt"}


def test_no_rename() -> None:
    base = {"a.txt": "a\n"}
    side = {"a.txt": "a\n", "b.txt": "b\n"}
    renames = detect_renames(
        set(base), set(side), lambda p: base[p], lambda p: side[p]
    )
    assert renames == {}
