from __future__ import annotations

from oxidize.semantic.entities import EntityType, extract_entities
from oxidize.semantic.differ import format_semantic_diff, semantic_diff
from oxidize.semantic.parser import HAS_TREE_SITTER


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


def test_cross_class_method_collision() -> None:
    old = "class Dog:\n    def save(self):\n        pass\n\nclass Cat:\n    def save(self):\n        pass\n"
    new = "class Dog:\n    def save(self):\n        pass\n\nclass Cat:\n    def save(self):\n        return True\n"
    changes = semantic_diff(old, new)
    assert any(c.change_type == "modified" and c.entity_name == "Cat.save" for c in changes)
    assert not any(c.change_type == "modified" and c.entity_name == "Dog.save" for c in changes)


def test_qualified_names_on_entities() -> None:
    source = "class Foo:\n    def bar(self):\n        pass\n"
    entities = extract_entities(source)
    methods = [e for e in entities if e.entity_type == EntityType.METHOD]
    assert len(methods) == 1
    assert methods[0].qualified_name == "Foo.bar"
    assert methods[0].parent_class == "Foo"


def test_top_level_function_qualified_name() -> None:
    source = "def greet():\n    return 'hi'\n"
    entities = extract_entities(source)
    assert len(entities) == 1
    assert entities[0].qualified_name == "greet"
    assert entities[0].parent_class == ""


def test_decorated_function() -> None:
    source = "class Service:\n    @property\n    def foo(self):\n        return 1\n"
    entities = extract_entities(source)
    assert any(e.name == "foo" for e in entities)


def test_async_function() -> None:
    source = "async def fetch():\n    pass\n"
    entities = extract_entities(source)
    assert any(e.name == "fetch" for e in entities)


def test_class_with_multiple_methods() -> None:
    source = "class Service:\n    def __init__(self):\n        pass\n    def start(self):\n        pass\n    def stop(self):\n        pass\n"
    entities = extract_entities(source)
    methods = [e for e in entities if e.entity_type == EntityType.METHOD]
    assert len(methods) == 3
    qualified_names = {e.qualified_name for e in methods}
    assert qualified_names == {"Service.__init__", "Service.start", "Service.stop"}


def test_same_method_different_classes_no_false_rename() -> None:
    old = (
        "class A:\n    def run(self):\n        pass\n\nclass B:\n    def run(self):\n        pass\n"
    )
    new = (
        "class A:\n    def run(self):\n        pass\n\nclass B:\n    def run(self):\n        pass\n"
    )
    changes = semantic_diff(old, new)
    assert len(changes) == 0


def test_parser_availability() -> None:
    assert isinstance(HAS_TREE_SITTER, bool)
