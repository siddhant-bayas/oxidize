from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from oxidize.semantic.parser import HAS_TREE_SITTER, parse_source


class EntityType(str, Enum):
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    ASSIGNMENT = "assignment"


@dataclass(frozen=True)
class Entity:
    name: str
    qualified_name: str
    entity_type: EntityType
    parent_class: str
    start_line: int
    end_line: int
    body_hash: str = ""
    source: str = ""

    def structural_hash(self) -> str:
        content = f"{self.entity_type.value}:{self.body_hash}"
        return hashlib.sha256(content.encode()).hexdigest()


def extract_entities(source: str) -> list[Entity]:
    if HAS_TREE_SITTER:
        result = _extract_tree_sitter(source)
        if result is not None:
            return result
    return _extract_regex(source)


def _unwrap(node: Any) -> Any:
    if getattr(node, "type", None) == "decorated_definition":
        for child in node.children:
            if child.type in ("function_definition", "class_definition"):
                return child
    return node


def _node_name(node: Any) -> str | None:
    name_field = node.child_by_field_name("name")
    if name_field is None:
        return None
    decoded: str = name_field.text.decode()
    return decoded


def _node_source(node: Any, source: str) -> str:
    start_byte = node.start_byte
    end_byte = node.end_byte
    return source.encode()[start_byte:end_byte].decode()


def _parse_function(node: Any, source: str, *, parent: str) -> Entity | None:
    name = _node_name(node)
    if name is None:
        return None
    block = node.child_by_field_name("body")
    if block is None:
        return None
    body_source = _node_source(block, source)
    body_hash = hashlib.sha256(body_source.encode()).hexdigest()[:16]
    start = node.start_point.row + 1
    end = node.end_point.row + 1
    qualified = f"{parent}.{name}" if parent else name
    ent_type = EntityType.METHOD if parent else EntityType.FUNCTION
    return Entity(
        name=name,
        qualified_name=qualified,
        entity_type=ent_type,
        parent_class=parent,
        start_line=start,
        end_line=end,
        body_hash=body_hash,
        source=body_source,
    )


def _extract_class(class_node: Any, source: str) -> list[Entity]:
    name = _node_name(class_node)
    if name is None:
        return []
    block = class_node.child_by_field_name("body")
    if block is None:
        return []
    body_source = _node_source(block, source)
    body_hash = hashlib.sha256(body_source.encode()).hexdigest()[:16]
    start = class_node.start_point.row + 1
    end = class_node.end_point.row + 1
    entities: list[Entity] = [
        Entity(
            name=name,
            qualified_name=name,
            entity_type=EntityType.CLASS,
            parent_class="",
            start_line=start,
            end_line=end,
            body_hash=body_hash,
            source=body_source,
        )
    ]
    for child in block.children:
        inner = _unwrap(child)
        if getattr(inner, "type", None) == "function_definition":
            ent = _parse_function(inner, source, parent=name)
            if ent is not None:
                entities.append(ent)
    return entities


def _extract_tree_sitter(source: str) -> list[Entity] | None:
    tree = parse_source(source)
    if tree is None:
        return None
    root = tree.root_node
    entities: list[Entity] = []
    for node in root.children:
        inner = _unwrap(node)
        if getattr(inner, "type", None) == "function_definition":
            ent = _parse_function(inner, source, parent="")
            if ent is not None:
                entities.append(ent)
        elif getattr(inner, "type", None) == "class_definition":
            entities.extend(_extract_class(inner, source))
    return entities


def _extract_regex(source: str) -> list[Entity]:
    entities: list[Entity] = []
    lines = source.split("\n")
    _DEF_RE = re.compile(r"(?:async\s+)?def\s+(\w+)\s*\(")
    _CLASS_RE = re.compile(r"class\s+(\w+)")

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if stripped.startswith("@"):
            i += 1
            if i >= len(lines):
                break
            stripped = lines[i].lstrip()
            indent = len(lines[i]) - len(stripped)

        def_match = _DEF_RE.match(stripped)
        if def_match:
            name = def_match.group(1)
            body_lines, end = _extract_body(lines, i + 1, indent + 4)
            body = "\n".join(body_lines)
            h = hashlib.sha256(body.encode()).hexdigest()[:16]
            ent_type = EntityType.METHOD if _is_indented(indent) else EntityType.FUNCTION
            parent = _find_enclosing_class(entities) if ent_type == EntityType.METHOD else ""
            qualified = f"{parent}.{name}" if parent else name
            entities.append(
                Entity(
                    name=name,
                    qualified_name=qualified,
                    entity_type=ent_type,
                    parent_class=parent,
                    start_line=i + 1,
                    end_line=end + 1,
                    body_hash=h,
                    source=body,
                )
            )
            i = end + 1
            continue

        class_match = _CLASS_RE.match(stripped)
        if class_match:
            name = class_match.group(1)
            body_lines, end = _extract_body(lines, i + 1, indent + 4)
            body = "\n".join(body_lines)
            h = hashlib.sha256(body.encode()).hexdigest()[:16]
            entities.append(
                Entity(
                    name=name,
                    qualified_name=name,
                    entity_type=EntityType.CLASS,
                    parent_class="",
                    start_line=i + 1,
                    end_line=end + 1,
                    body_hash=h,
                    source=body,
                )
            )
            i += 1
            continue

        i += 1

    return entities


def _find_enclosing_class(entities: list[Entity]) -> str:
    for ent in reversed(entities):
        if ent.entity_type == EntityType.CLASS:
            return ent.name
    return ""


def _extract_body(lines: list[str], start: int, expected_indent: int) -> tuple[list[str], int]:
    body: list[str] = []
    i = start
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        if stripped == "" or stripped.startswith("#"):
            body.append(line)
            i += 1
            continue
        current_indent = len(line) - len(stripped)
        if current_indent < expected_indent:
            break
        body.append(line)
        i += 1
    end = i - 1 if i > start else start
    return body, end


def _is_indented(indent: int) -> bool:
    return indent > 0


@dataclass
class EntitySnapshot:
    entities: list[Entity] = field(default_factory=list)

    def by_qualified_name(self) -> dict[str, Entity]:
        return {e.qualified_name: e for e in self.entities}

    def by_name(self) -> dict[str, Entity]:
        return {e.name: e for e in self.entities}

    def by_hash(self) -> dict[str, list[Entity]]:
        result: dict[str, list[Entity]] = {}
        for e in self.entities:
            h = e.structural_hash()
            result.setdefault(h, []).append(e)
        return result
