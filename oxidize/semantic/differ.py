from __future__ import annotations

from dataclasses import dataclass

from oxidize.semantic.entities import EntityType, EntitySnapshot, extract_entities


@dataclass(frozen=True)
class SemanticChange:
    change_type: str
    entity_name: str
    entity_type: EntityType
    detail: str


def semantic_diff(old_source: str, new_source: str) -> list[SemanticChange]:
    old_entities = EntitySnapshot(extract_entities(old_source))
    new_entities = EntitySnapshot(extract_entities(new_source))

    changes: list[SemanticChange] = []

    old_by_qn = old_entities.by_qualified_name()
    new_by_qn = new_entities.by_qualified_name()

    renamed: dict[str, str] = {}
    old_by_hash = old_entities.by_hash()
    new_by_hash = new_entities.by_hash()
    for h in set(old_by_hash) & set(new_by_hash):
        old_e = old_by_hash[h][0]
        new_e = new_by_hash[h][0]
        if old_e.qualified_name != new_e.qualified_name:
            renamed[old_e.qualified_name] = new_e.qualified_name

    for qn, entity in old_by_qn.items():
        if qn in renamed:
            changes.append(
                SemanticChange(
                    change_type="renamed",
                    entity_name=qn,
                    entity_type=entity.entity_type,
                    detail=f"renamed to '{renamed[qn]}'",
                )
            )
        elif qn not in new_by_qn:
            changes.append(
                SemanticChange(
                    change_type="deleted",
                    entity_name=qn,
                    entity_type=entity.entity_type,
                    detail=f"removed {entity.entity_type.value} '{qn}'",
                )
            )

    for qn, entity in new_by_qn.items():
        if qn in renamed:
            continue
        if qn not in old_by_qn:
            changes.append(
                SemanticChange(
                    change_type="added",
                    entity_name=qn,
                    entity_type=entity.entity_type,
                    detail=f"added {entity.entity_type.value} '{qn}'",
                )
            )
        else:
            old_e = old_by_qn[qn]
            if old_e.body_hash != entity.body_hash:
                changes.append(
                    SemanticChange(
                        change_type="modified",
                        entity_name=qn,
                        entity_type=entity.entity_type,
                        detail=f"body of '{qn}' changed",
                    )
                )

    return changes


def format_semantic_diff(changes: list[SemanticChange]) -> str:
    if not changes:
        return "no semantic changes"
    lines: list[str] = []
    icons = {"added": "+", "deleted": "-", "modified": "~", "renamed": ">"}
    for c in changes:
        icon = icons.get(c.change_type, "?")
        lines.append(f"  {icon} {c.detail}")
    return "\n".join(lines)
