"""Build source-neutral tag cross-references from captured software calls."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from twinforge.model import (
    Controller,
    Program,
    Routine,
    SoftwareCallLanguage,
    SoftwareCallSite,
    SoftwareTagScope,
    Tag,
)
from twinforge.structured_text import (
    AssignmentStatement,
    BinaryExpression,
    CallExpression,
    Expression,
    IfStatement,
    IndexExpression,
    MemberExpression,
    NameExpression,
    ParenthesizedExpression,
    Statement,
    UnaryExpression,
    WhileStatement,
    parse_structured_text,
)

from .software_calls import extract_program_calls


class TagReferenceAccess(str, Enum):
    """Data-flow meaning supported by an instruction or named argument."""

    READ = "read"
    WRITE = "write"
    READ_WRITE = "read_write"
    ALIAS = "alias"
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
    source_tag_key: str | None = None


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
    source_tag_key: str | None = None


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
    _collect_alias_definitions(
        "<controller>",
        controller.tags,
        {},
        controller_tags,
        references,
        unresolved,
    )
    for program in controller.iter_programs():
        program_tags = _tag_lookup(program.tags)
        _collect_alias_definitions(
            program.name,
            program.tags,
            program_tags,
            controller_tags,
            references,
            unresolved,
        )
        for call in extract_program_calls(program):
            for argument in call.arguments:
                access = _argument_access(call, argument.position, argument.direction)
                _collect_operand(
                    call,
                    argument.position,
                    argument.source,
                    access,
                    program_tags,
                    controller_tags,
                    references,
                    unresolved,
                )
        for routine in program.iter_routines():
            _collect_structured_text_direct_references(
                program,
                routine,
                program_tags,
                controller_tags,
                references,
                unresolved,
            )
    return TagDependencyGraph(
        references=tuple(sorted(references, key=_reference_key)),
        unresolved_references=tuple(sorted(unresolved, key=_unresolved_key)),
    )


def _tag_lookup(tags: dict[str, Tag]) -> dict[str, tuple[Tag, str]]:
    return {name.casefold(): (tag, name) for name, tag in tags.items()}


def _collect_operand(
    call: SoftwareCallSite,
    position: int,
    operand: str,
    access: TagReferenceAccess,
    program_tags: dict[str, tuple[Tag, str]],
    controller_tags: dict[str, tuple[Tag, str]],
    references: list[TagReference],
    unresolved: list[UnresolvedTagReference],
    source_tag_key: str | None = None,
) -> None:
    for identifier in _identifiers(operand):
        root, member_path = _root_and_member(identifier)
        resolved = program_tags.get(root.casefold())
        scope = SoftwareTagScope.PROGRAM
        if resolved is None:
            resolved = controller_tags.get(root.casefold())
            scope = SoftwareTagScope.CONTROLLER
        if resolved is not None:
            tag, canonical_name = resolved
            references.append(
                _reference(
                    call,
                    position,
                    operand,
                    tag,
                    canonical_name,
                    scope,
                    member_path,
                    access,
                    source_tag_key,
                )
            )
            continue
        unresolved.append(
            UnresolvedTagReference(
                identifier=identifier,
                instruction=call.callee,
                argument_position=position,
                operand=operand,
                program_name=call.program_name,
                routine_name=call.routine_name,
                rung_number=call.rung_number,
                line_number=call.line_number,
                source_tag_key=source_tag_key,
            )
        )


def _collect_alias_definitions(
    program_name: str,
    tags: dict[str, Tag],
    program_tags: dict[str, tuple[Tag, str]],
    controller_tags: dict[str, tuple[Tag, str]],
    references: list[TagReference],
    unresolved: list[UnresolvedTagReference],
) -> None:
    for name, tag in tags.items():
        if not tag.alias_for:
            continue
        is_controller = program_name == "<controller>"
        source_tag_key = (
            f"controller:{name}"
            if is_controller
            else f"program:{program_name}:{name}"
        )
        call = SoftwareCallSite(
            callee="ALIAS",
            arguments=(),
            program_name=program_name,
            routine_name="<tag-definition>",
            language=SoftwareCallLanguage.LADDER,
            source_text=tag.alias_for,
        )
        _collect_operand(
            call,
            0,
            tag.alias_for,
            TagReferenceAccess.ALIAS,
            program_tags,
            controller_tags,
            references,
            unresolved,
            source_tag_key,
        )


def _identifiers(operand: str) -> tuple[str, ...]:
    return tuple(
        match.group()
        for match in _IDENTIFIER.finditer(operand)
        if match.group().casefold() not in _IGNORED_IDENTIFIERS
    )


def _collect_structured_text_direct_references(
    program: Program,
    routine: Routine,
    program_tags: dict[str, tuple[Tag, str]],
    controller_tags: dict[str, tuple[Tag, str]],
    references: list[TagReference],
    unresolved: list[UnresolvedTagReference],
) -> None:
    source = routine.structured_text
    if not source:
        return
    document = parse_structured_text(source)

    def collect_expression(
        expression: Expression,
        access: TagReferenceAccess,
        instruction: str,
        position: int,
    ) -> None:
        for operand in _direct_expression_operands(expression, source):
            call = SoftwareCallSite(
                callee=instruction,
                arguments=(),
                program_name=program.name,
                routine_name=routine.name,
                language=SoftwareCallLanguage.STRUCTURED_TEXT,
                source_text=source[expression.span.start : expression.span.end],
                line_number=_captured_line_number(routine, source, expression),
            )
            _collect_operand(
                call,
                position,
                operand,
                access,
                program_tags,
                controller_tags,
                references,
                unresolved,
            )

    def collect_statements(statements: tuple[Statement, ...]) -> None:
        for statement in statements:
            if isinstance(statement, AssignmentStatement):
                collect_expression(
                    statement.target,
                    TagReferenceAccess.WRITE,
                    "ST_ASSIGN",
                    0,
                )
                collect_expression(
                    statement.value,
                    TagReferenceAccess.READ,
                    "ST_ASSIGN",
                    1,
                )
            elif isinstance(statement, IfStatement):
                for branch in statement.branches:
                    collect_expression(
                        branch.condition,
                        TagReferenceAccess.READ,
                        "ST_IF",
                        0,
                    )
                    collect_statements(branch.statements)
                collect_statements(statement.else_statements)
            elif isinstance(statement, WhileStatement):
                collect_expression(
                    statement.condition,
                    TagReferenceAccess.READ,
                    "ST_WHILE",
                    0,
                )
                collect_statements(statement.statements)

    collect_statements(document.statements)


def _direct_expression_operands(
    expression: Expression,
    source: str,
) -> tuple[str, ...]:
    if isinstance(expression, NameExpression | MemberExpression):
        operands = [source[expression.span.start : expression.span.end]]
        if isinstance(expression, MemberExpression) and isinstance(
            expression.target, IndexExpression
        ):
            operands.extend(
                item
                for index in expression.target.indices
                for item in _direct_expression_operands(index, source)
            )
        return tuple(operands)
    if isinstance(expression, IndexExpression):
        return (
            source[expression.span.start : expression.span.end],
            *(
                item
                for index in expression.indices
                for item in _direct_expression_operands(index, source)
            ),
        )
    if isinstance(expression, UnaryExpression):
        return _direct_expression_operands(expression.operand, source)
    if isinstance(expression, BinaryExpression):
        return (
            *_direct_expression_operands(expression.left, source),
            *_direct_expression_operands(expression.right, source),
        )
    if isinstance(expression, ParenthesizedExpression):
        return _direct_expression_operands(expression.expression, source)
    if isinstance(expression, CallExpression):
        return ()
    return ()


def _captured_line_number(
    routine: Routine,
    source: str,
    expression: Expression,
) -> int | None:
    physical_line = source.count("\n", 0, expression.span.start)
    if physical_line >= len(routine.structured_text_lines):
        return None
    return routine.structured_text_lines[physical_line].number


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
    source_tag_key: str | None = None,
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
        source_tag_key=source_tag_key,
    )


def _reference_key(item: TagReference) -> tuple[Any, ...]:
    return (
        item.program_name,
        item.routine_name,
        item.rung_number if item.rung_number is not None else -1,
        item.line_number if item.line_number is not None else -1,
        item.instruction,
        item.argument_position,
        item.source_tag_key or "",
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
        item.source_tag_key or "",
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
