"""Validation of RFC 6933 physical-entity containment evidence."""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import SnmpPhysicalEntityObservation


@dataclass(frozen=True)
class SnmpEntityContainmentIssue:
    """One structural issue found without changing observed evidence."""

    code: str
    entity_index: int
    parent_index: int | None
    message: str


def validate_entity_containment(
    entities: tuple[SnmpPhysicalEntityObservation, ...],
) -> tuple[SnmpEntityContainmentIssue, ...]:
    """Check parent references and cycles while accepting RFC root value zero."""
    by_index = {entity.index: entity for entity in entities}
    issues: list[SnmpEntityContainmentIssue] = []
    for entity in entities:
        parent = entity.contained_in
        if parent in {None, 0}:
            continue
        if parent == entity.index:
            issues.append(
                SnmpEntityContainmentIssue(
                    "self_parent",
                    entity.index,
                    parent,
                    "physical entity contains itself",
                )
            )
        elif parent not in by_index:
            issues.append(
                SnmpEntityContainmentIssue(
                    "missing_parent",
                    entity.index,
                    parent,
                    "contained-in entity is absent from the observation",
                )
            )

    for entity in entities:
        visited: set[int] = set()
        current = entity.index
        while current in by_index:
            if current in visited:
                issues.append(
                    SnmpEntityContainmentIssue(
                        "containment_cycle",
                        entity.index,
                        current,
                        "physical-entity containment contains a cycle",
                    )
                )
                break
            visited.add(current)
            parent = by_index[current].contained_in
            if parent in {None, 0}:
                break
            current = parent
    unique = {
        (issue.code, issue.entity_index, issue.parent_index): issue
        for issue in issues
    }
    return tuple(unique[key] for key in sorted(unique))
