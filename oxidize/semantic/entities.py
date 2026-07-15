from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum


class EntityType(str, Enum):
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    ASSIGNMENT = "assignment"


@dataclass(frozen=True)
class Entity:
    name: str
    entity_type: EntityType
    start_line: int
    end_line: int
    body_hash: str = ""
    source: str = ""

    def structural_hash(self) -> str:
        content = f"{self.entity_type.value}:{self.body_hash}"
        return hashlib.sha256(content.encode()).hexdigest()


def extract_entities(source: str) -> list[Entity]:
    entities: list[Entity] = []
    lines = source.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if stripped.startswith("def "):
            match = re.match(r"def\s+(\w+)\s*\(", stripped)
            if match:
                name = match.group(1)
                body_lines, end = _extract_body(lines, i + 1, indent + 4)
                body = "\n".join(body_lines)
                h = hashlib.sha256(body.encode()).hexdigest()[:16]
                entities.append(
                    Entity(
                        name=name,
                        entity_type=EntityType.METHOD
                        if _is_indented(indent)
                        else EntityType.FUNCTION,
                        start_line=i + 1,
                        end_line=end + 1,
                        body_hash=h,
                        source=body,
                    )
                )
                i = end + 1
                continue

        elif stripped.startswith("class "):
            match = re.match(r"class\s+(\w+)", stripped)
            if match:
                name = match.group(1)
                body_lines, end = _extract_body(lines, i + 1, indent + 4)
                body = "\n".join(body_lines)
                h = hashlib.sha256(body.encode()).hexdigest()[:16]
                entities.append(
                    Entity(
                        name=name,
                        entity_type=EntityType.CLASS,
                        start_line=i + 1,
                        end_line=end + 1,
                        body_hash=h,
                        source=body,
                    )
                )
                i = end + 1
                continue

        i += 1

    return entities


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

    def by_name(self) -> dict[str, Entity]:
        return {e.name: e for e in self.entities}

    def by_hash(self) -> dict[str, list[Entity]]:
        result: dict[str, list[Entity]] = {}
        for e in self.entities:
            h = e.structural_hash()
            result.setdefault(h, []).append(e)
        return result
