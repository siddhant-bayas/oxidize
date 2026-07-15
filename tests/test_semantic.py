from __future__ import annotations

from oxidize.semantic.entities import EntityType, extract_entities
from oxidize.semantic.differ import format_semantic_diff, semantic_diff


def test_extract_function() -> None:
    source = "def hello():\n    print('hi')\n"
    entities = extract_entities(source)
    assert len(entities) == 1
    assert entities[0].name == "hello"
    assert entities[0].entity_type == EntityType.FUNCTION


def test_extract_class() -> None:
    source = "class Foo:\n    pass\n"
    entities = extract_entities(source)
    assert len(entities) == 1
    assert entities[0].name == "Foo"
    assert entities[0].entity_type == EntityType.CLASS


def test_extract_multiple() -> None:
    source = "def a():\n    pass\n\ndef b():\n    pass\n\nclass C:\n    pass\n"
    entities = extract_entities(source)
    assert len(entities) == 3


def test_extract_empty() -> None:
    entities = extract_entities("")
    assert len(entities) == 0


def test_semantic_diff_no_change() -> None:
    source = "def foo():\n    return 1\n"
    changes = semantic_diff(source, source)
    assert len(changes) == 0


def test_semantic_diff_add_function() -> None:
    old = "def foo():\n    return 1\n"
    new = "def foo():\n    return 1\n\ndef bar():\n    return 2\n"
    changes = semantic_diff(old, new)
    assert any(c.change_type == "added" and c.entity_name == "bar" for c in changes)


def test_semantic_diff_delete_function() -> None:
    old = "def foo():\n    return 1\n\ndef bar():\n    return 2\n"
    new = "def foo():\n    return 1\n"
    changes = semantic_diff(old, new)
    assert any(c.change_type == "deleted" and c.entity_name == "bar" for c in changes)


def test_semantic_diff_rename_function() -> None:
    old = "def old_name():\n    return 1\n"
    new = "def new_name():\n    return 1\n"
    changes = semantic_diff(old, new)
    assert any(c.change_type == "renamed" and c.entity_name == "old_name" for c in changes)


def test_semantic_diff_modify_function() -> None:
    old = "def foo():\n    return 1\n"
    new = "def foo():\n    return 2\n"
    changes = semantic_diff(old, new)
    assert any(c.change_type == "modified" and c.entity_name == "foo" for c in changes)


def test_format_semantic_diff() -> None:
    old = "def foo():\n    return 1\n\ndef bar():\n    return 2\n"
    new = "def foo():\n    return 1\n"
    changes = semantic_diff(old, new)
    output = format_semantic_diff(changes)
    assert "bar" in output
