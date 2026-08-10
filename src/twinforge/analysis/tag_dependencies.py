"""Build source-neutral tag cross-references from captured software calls."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from twinforge.model import Controller, SoftwareCallSite, SoftwareTagScope, Tag

from .software_calls import extract_program_calls


class TagReferenceAccess(str, Enum):
    """Data-flow meaning supported by an instruction or named argument."""

    READ = "read"
    WRITE = "write"
    READ_WRITE = "read_write"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class TagReference:
    """One resolved tag occurrence with exact source location and operand."""

    tag_key: str
    tag_name: str
    tag_scope: SoftwareTagScope
    member_path: str | None
    access: TagReferenceAccess
    instruction: str
    argument_position: int
    operand: str
    program_name: str
    routine_name: str
    rung_number: int | None
    line_number: int | None


@dataclass(frozen=True)
class UnresolvedTagReference:
    """Identifier-like operand evidence that did not resolve to a known tag."""

    identifier: str
    instruction: str
    argument_position: int
    operand: str
    program_name: str
    routine_name: str
    rung_number: int | None
    line_number: int | None


@dataclass(frozen=True)
class TagDependencyGraph:
    """Deterministic routine-to-tag edges and retained unresolved evidence."""

    references: tuple[TagReference, ...]
    unresolved_references: tuple[UnresolvedTagReference, ...]


_IDENTIFIER = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*(?::[A-Za-z0-9_]+)*"
    r"(?:\[[^\]]+\])?(?:\.[A-Za-z0-9_]+)*"
)
_IGNORED_IDENTIFIERS = frozenset({"false", "true"})
_READ_ALL = frozenset({"XIC", "XIO", "EQU", "NEQ", "GRT", "GEQ", "LES", "LEQ"})
_WRITE_FIRST = frozenset({"OTE", "OTL", "OTU"})
_STATE_FIRST = frozenset({"TON", "TOF", "RTO", "CTU", "CTD", "RES", "ONS"})
_VALUE_WRITES = {
    "MOV": 1,
    "ADD": 2,
    "SUB": 2,
    "MUL": 2,
    "DIV": 2,
}


def build_tag_dependency_graph(controller: Controller) -> TagDependencyGraph:
    """Resolve known tag occurrences without discarding unknown operands."""
    references: list[TagReference] = []
    unresolved: list[UnresolvedTagReference] = []
    controller_tags = _tag_lookup(controller.tags)
    for program in controller.iter_programs():
        program_tags = _tag_lookup(program.tags)
        for call in extract_program_calls(program):
            for argument in call.arguments:
                access = _argument_access(call, argument.position, argument.direction)
                for identifier in _identifiers(argument.source):
                    root, member_path = _root_and_member(identifier)
                    resolved = program_tags.get(root.casefold())
                    if resolved is not None:
                        tag, canonical_name = resolved
                        references.append(
                            _reference(
                                call,
                                argument.position,
                                argument.source,
                                tag,
                                canonical_name,
                                SoftwareTagScope.PROGRAM,
                                member_path,
                                access,
                            )
                        )
                        continue
                    resolved = controller_tags.get(root.casefold())
                    if resolved is not None:
                        tag, canonical_name = resolved
                        references.append(
                            _reference(
                                call,
                                argument.position,
                                argument.source,
                                tag,
                                canonical_name,
                                SoftwareTagScope.CONTROLLER,
                                member_path,
                                access,
                            )
                        )
                        continue
                    unresolved.append(
                        UnresolvedTagReference(
                            identifier=identifier,
                            instruction=call.callee,
                            argument_position=argument.position,
                            operand=argument.source,
                            program_name=call.program_name,
                            routine_name=call.routine_name,
                            rung_number=call.rung_number,
                            line_number=call.line_number,
                        )
                    )
    return TagDependencyGraph(
        references=tuple(sorted(references, key=_reference_key)),
        unresolved_references=tuple(sorted(unresolved, key=_unresolved_key)),
    )


def _tag_lookup(tags: dict[str, Tag]) -> dict[str, tuple[Tag, str]]:
    return {name.casefold(): (tag, name) for name, tag in tags.items()}


def _identifiers(operand: str) -> tuple[str, ...]:
    return tuple(
        match.group()
        for match in _IDENTIFIER.finditer(operand)
        if match.group().casefold() not in _IGNORED_IDENTIFIERS
    )


def _root_and_member(identifier: str) -> tuple[str, str | None]:
    bracket = identifier.find("[")
    dot = identifier.find(".")
    boundaries = [item for item in (bracket, dot) if item >= 0]
    end = min(boundaries) if boundaries else len(identifier)
    member = identifier[end:] or None
    return identifier[:end], member


def _argument_access(
    call: SoftwareCallSite,
    position: int,
    direction: str | None,
) -> TagReferenceAccess:
    if direction == ":=":
        return TagReferenceAccess.READ
    if direction == "=>":
        return TagReferenceAccess.WRITE
    opcode = call.callee.upper()
    if opcode in _READ_ALL:
        return TagReferenceAccess.READ
    if opcode in _WRITE_FIRST and position == 0:
        return TagReferenceAccess.WRITE
    if opcode in _STATE_FIRST:
        return TagReferenceAccess.READ_WRITE if position == 0 else TagReferenceAccess.READ
    destination = _VALUE_WRITES.get(opcode)
    if destination is not None:
        return TagReferenceAccess.WRITE if position == destination else TagReferenceAccess.READ
    return TagReferenceAccess.UNKNOWN


def _reference(
    call: SoftwareCallSite,
    position: int,
    operand: str,
    tag: Tag,
    canonical_name: str,
    scope: SoftwareTagScope,
    member_path: str | None,
    access: TagReferenceAccess,
) -> TagReference:
    prefix = "program" if scope is SoftwareTagScope.PROGRAM else "controller"
    owner = f"{call.program_name}:" if scope is SoftwareTagScope.PROGRAM else ""
    return TagReference(
        tag_key=f"{prefix}:{owner}{canonical_name}",
        tag_name=tag.name,
        tag_scope=scope,
        member_path=member_path,
        access=access,
        instruction=call.callee,
        argument_position=position,
        operand=operand,
        program_name=call.program_name,
        routine_name=call.routine_name,
        rung_number=call.rung_number,
        line_number=call.line_number,
    )


def _reference_key(item: TagReference) -> tuple[Any, ...]:
    return (
        item.program_name,
        item.routine_name,
        item.rung_number if item.rung_number is not None else -1,
        item.line_number if item.line_number is not None else -1,
        item.instruction,
        item.argument_position,
        item.tag_key,
        item.member_path or "",
    )


def _unresolved_key(item: UnresolvedTagReference) -> tuple[Any, ...]:
    return (
        item.program_name,
        item.routine_name,
        item.rung_number if item.rung_number is not None else -1,
        item.line_number if item.line_number is not None else -1,
        item.instruction,
        item.argument_position,
        item.identifier,
    )


def tag_dependency_graph_data(graph: TagDependencyGraph) -> dict[str, Any]:
    """Return deterministic JSON-compatible cross-reference data."""
    return {
        "references": [
            {
                **item.__dict__,
                "tag_scope": item.tag_scope.value,
                "access": item.access.value,
            }
            for item in graph.references
        ],
        "unresolved_references": [
            item.__dict__ for item in graph.unresolved_references
        ],
    }


def tag_dependency_graph_json(graph: TagDependencyGraph) -> str:
    """Serialize a tag dependency graph deterministically."""
    return json.dumps(tag_dependency_graph_data(graph), indent=2) + "\n"
