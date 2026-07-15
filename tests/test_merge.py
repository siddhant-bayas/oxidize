from __future__ import annotations

from oxidize.merge.structured import deep_merge, three_way_merge


def test_deep_merge_simple() -> None:
    base = {"a": 1, "b": 2}
    head = {"b": 3, "c": 4}
    result = deep_merge(base, head)
    assert result == {"a": 1, "b": 3, "c": 4}


def test_deep_merge_nested() -> None:
    base = {"db": {"host": "localhost", "port": 5432}}
    head = {"db": {"port": 5433}}
    result = deep_merge(base, head)
    assert result["db"]["host"] == "localhost"
    assert result["db"]["port"] == 5433


def test_deep_merge_no_mutate() -> None:
    base = {"a": {"x": 1}}
    head = {"a": {"y": 2}}
    deep_merge(base, head)
    assert base == {"a": {"x": 1}}


def test_three_way_no_conflict() -> None:
    base = {"a": 1, "b": 2}
    ours = {"a": 1, "b": 3}
    theirs = {"a": 1, "b": 2}
    result, conflicts = three_way_merge(base, ours, theirs)
    assert result["b"] == 3
    assert conflicts == []


def test_three_way_conflict() -> None:
    base = {"x": 1}
    ours = {"x": 2}
    theirs = {"x": 3}
    result, conflicts = three_way_merge(base, ours, theirs)
    assert len(conflicts) == 1
    assert "x" in conflicts


def test_three_way_add_delete() -> None:
    base = {"a": 1}
    ours = {"a": 1, "b": 2}
    theirs = {"a": 1}
    result, conflicts = three_way_merge(base, ours, theirs)
    assert result["b"] == 2
    assert conflicts == []


def test_three_way_both_add_same() -> None:
    base = {"a": 1}
    ours = {"a": 1, "b": 2}
    theirs = {"a": 1, "b": 2}
    result, conflicts = three_way_merge(base, ours, theirs)
    assert result["b"] == 2
    assert conflicts == []


def test_three_way_nested_conflict() -> None:
    base = {"db": {"host": "localhost", "port": 5432}}
    ours = {"db": {"port": 5433}}
    theirs = {"db": {"port": 5434}}
    result, conflicts = three_way_merge(base, ours, theirs)
    assert len(conflicts) == 1
    assert "db.port" in conflicts
