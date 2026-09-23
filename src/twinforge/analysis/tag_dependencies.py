"""Build source-neutral tag cross-references from captured software calls."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from twinforge.model import (
    Controller,
    LadderInstruction,
    LadderOperation,
    LadderParallel,
    LadderSeries,
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
class StepStateReference:
    """One ".X"/".x" SFC step-active-state reference inside a Structured
    Text expression -- the same convention already established for LD
    contacts (see resolve_graphical_bindings), resolved against the
    identical project-wide step registry. Retained as evidence that the
    step is reachable, never an execution-order or timing claim.
    """

    step_name: str
    program_name: str
    routine_name: str
    operand: str
    line_number: int | None


@dataclass(frozen=True)
class AmbiguousStepStateReference:
    """A ".X" reference whose base name matches more than one declared step."""

    identifier: str
    program_name: str
    routine_name: str
    operand: str
    line_number: int | None


@dataclass(frozen=True)
class TagDependencyGraph:
    """Deterministic routine-to-tag edges and retained unresolved evidence."""

    references: tuple[TagReference, ...]
    unresolved_references: tuple[UnresolvedTagReference, ...]
    step_state_references: tuple[StepStateReference, ...] = ()
    ambiguous_step_state_references: tuple[AmbiguousStepStateReference, ...] = ()


_IDENTIFIER = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*(?::[A-Za-z0-9_]+)*"
    r"(?:\[[^\]]+\])?(?:\.[A-Za-z0-9_]+)*"
)
_IGNORED_IDENTIFIERS = frozenset({"false", "true"})
# IEC SFC step-active-state convention (real evidence: "G1_0.X" in an ST
# IF/ELSIF condition), the same ".X"/".x" shape already recognized for LD
# contacts. Only a single trailing member is a step-state candidate -- a
# longer dotted chain (e.g. "Foo.G1_0.X") never matches a bare step name
# and falls through to ordinary tag resolution unchanged.
_STEP_STATE_SUFFIX = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\.([Xx])$")
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


def build_tag_dependency_graph(
    controller: Controller, *,
    step_names: dict[str, str] | None = None, ambiguous_step_names: frozenset[str] = frozenset(),
) -> TagDependencyGraph:
    """Resolve known tag occurrences without discarding unknown operands.

    ``step_names``/``ambiguous_step_names`` are optional, evidence-driven
    lookups (a project-wide SFC step registry, matching how
    ``resolve_graphical_bindings`` already builds one for LD contacts) that
    let a Structured Text ``.X``/``.x`` step-active-state reference resolve
    instead of staying an unresolved tag identifier. Omitting them changes
    nothing for a caller with no step evidence to offer (e.g. L5X).
    """
    references: list[TagReference] = []
    unresolved: list[UnresolvedTagReference] = []
    step_state_references: list[StepStateReference] = []
    ambiguous_step_state_references: list[AmbiguousStepStateReference] = []
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
                step_names,
                ambiguous_step_names,
                step_state_references,
                ambiguous_step_state_references,
            )
            _collect_structured_ladder_references(
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
        step_state_references=tuple(sorted(step_state_references, key=_step_state_key)),
        ambiguous_step_state_references=tuple(
            sorted(ambiguous_step_state_references, key=_ambiguous_step_state_key)),
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


# A rung's structured LadderSeries network is the portable representation
# Control Expert's and CCW's own ladder capture populate; unlike L5X, they
# never synthesize RLL mnemonic text, so _ladder_calls (which only reads
# LadderRung.text) sees nothing for them at all -- silently, not diagnosed.
# LadderInstruction.operation already carries portable read/write meaning
# (see LadderOperation), more precise than re-parsing mnemonic text the way
# _ladder_calls does for L5X, so no text synthesis or mnemonic table is
# needed here.
_LADDER_ACCESS = {
    LadderOperation.NORMALLY_OPEN_CONTACT: TagReferenceAccess.READ,
    LadderOperation.NORMALLY_CLOSED_CONTACT: TagReferenceAccess.READ,
    LadderOperation.COIL: TagReferenceAccess.WRITE,
    LadderOperation.SET_COIL: TagReferenceAccess.WRITE,
    LadderOperation.RESET_COIL: TagReferenceAccess.WRITE,
    # UNSUPPORTED intentionally has no entry: an instruction shape this
    # project does not yet recognize is never guessed at as a read or write.
}


def _walk_ladder_series(series: LadderSeries) -> tuple[LadderInstruction, ...]:
    instructions: list[LadderInstruction] = []
    for element in series.elements:
        if isinstance(element, LadderParallel):
            for branch in element.branches:
                instructions.extend(_walk_ladder_series(branch))
        else:
            instructions.append(element)
    return tuple(instructions)


def _collect_structured_ladder_references(
    program: Program,
    routine: Routine,
    program_tags: dict[str, tuple[Tag, str]],
    controller_tags: dict[str, tuple[Tag, str]],
    references: list[TagReference],
    unresolved: list[UnresolvedTagReference],
) -> None:
    for rung in routine.ladder_rungs:
        # Mutually exclusive by construction across every converter that
        # populates LadderRung (L5X: text only; Control Expert and CCW:
        # network only) -- reading .network here can never double-count an
        # L5X reference _ladder_calls already extracted from .text.
        if rung.text is not None or rung.network is None:
            continue
        for instruction in _walk_ladder_series(rung.network):
            access = _LADDER_ACCESS.get(instruction.operation)
            if access is None or not instruction.operand:
                continue
            call = SoftwareCallSite(
                callee=instruction.operation.value,
                arguments=(),
                program_name=program.name,
                routine_name=routine.name,
                language=SoftwareCallLanguage.LADDER,
                source_text=instruction.operand,
                rung_number=rung.number,
            )
            _collect_operand(
                call, 0, instruction.operand, access, program_tags, controller_tags, references, unresolved,
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
    step_names: dict[str, str] | None,
    ambiguous_step_names: frozenset[str],
    step_state_references: list[StepStateReference],
    ambiguous_step_state_references: list[AmbiguousStepStateReference],
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
            line_number = _captured_line_number(routine, source, expression)
            # A step-state ".X"/".x" reference is checked before ordinary
            # tag resolution, but a same-named declared tag still wins --
            # the same precedence already established for chart-control
            # calls (declared_symbol is tried first, a program/step
            # interpretation only once that's ruled out).
            step_match = _STEP_STATE_SUFFIX.match(operand) if step_names is not None else None
            if step_match:
                root_key = step_match.group(1).casefold()
                is_declared_tag = root_key in program_tags or root_key in controller_tags
                if not is_declared_tag and root_key in ambiguous_step_names:
                    ambiguous_step_state_references.append(AmbiguousStepStateReference(
                        identifier=step_match.group(1), program_name=program.name,
                        routine_name=routine.name, operand=operand, line_number=line_number,
                    ))
                    continue
                if not is_declared_tag and step_names is not None and root_key in step_names:
                    step_state_references.append(StepStateReference(
                        step_name=step_names[root_key], program_name=program.name,
                        routine_name=routine.name, operand=operand, line_number=line_number,
                    ))
                    continue
            call = SoftwareCallSite(
                callee=instruction,
                arguments=(),
                program_name=program.name,
                routine_name=routine.name,
                language=SoftwareCallLanguage.STRUCTURED_TEXT,
                source_text=source[expression.span.start : expression.span.end],
                line_number=line_number,
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


def _step_state_key(item: StepStateReference) -> tuple[Any, ...]:
    return (
        item.program_name,
        item.routine_name,
        item.line_number if item.line_number is not None else -1,
        item.step_name,
    )


def _ambiguous_step_state_key(item: AmbiguousStepStateReference) -> tuple[Any, ...]:
    return (
        item.program_name,
        item.routine_name,
        item.line_number if item.line_number is not None else -1,
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
        "step_state_references": [
            item.__dict__ for item in graph.step_state_references
        ],
        "ambiguous_step_state_references": [
            item.__dict__ for item in graph.ambiguous_step_state_references
        ],
    }


def tag_dependency_graph_json(graph: TagDependencyGraph) -> str:
    """Serialize a tag dependency graph deterministically."""
    return json.dumps(tag_dependency_graph_data(graph), indent=2) + "\n"
