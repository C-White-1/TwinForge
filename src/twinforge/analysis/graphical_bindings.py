"""Resolve simple graphical pin expressions without inferring execution edges."""
from __future__ import annotations

from dataclasses import dataclass
import re

from twinforge.analysis.member_paths import MemberPathResult, resolve_member_path
from twinforge.analysis.simple_expressions import resolve_binary_expression
from twinforge.model import (
    AddOnInstructionParameter, Controller, GraphicalDiagram, GraphicalObject, GraphicalPin,
    GraphicalVariableReferences, Tag,
)
from twinforge.model.datatype import Datatype
from twinforge.model.resource import Resource
from twinforge.model.library_interface import LibraryInterface
from twinforge.schema.control_expert import device_ddt_catalog


@dataclass(frozen=True)
class MemberPathContext:
    """Type definitions an index/member/bit-select expression may be proven against."""

    array_pattern: str
    datatypes: dict[str, Datatype]
    function_blocks: dict[str, dict[str, AddOnInstructionParameter | Tag]]
    library_interfaces: dict[str, LibraryInterface]


def member_path_context(
    controller: Controller, library_interfaces: list[LibraryInterface], array_pattern: str,
) -> MemberPathContext:
    datatypes = device_ddt_catalog.datatypes()
    # A project's own captured definition always wins over vendor documentation.
    datatypes.update({datatype.name.casefold(): datatype for datatype in controller.datatypes.values()})
    return MemberPathContext(
        array_pattern,
        datatypes,
        # Externally visible members of an FB instance: its parameters, plus
        # only its *public* locals -- a private local is never proven
        # reachable from outside (see the public local member-path checkpoint;
        # this is a real Control Expert visibility distinction, not a guess).
        {aoi.name.casefold(): {
            **{p.name.casefold(): p for p in aoi.parameters.values()},
            **{t.name.casefold(): t for t in aoi.local_tags.values()
               if t.metadata.get("visibility") == "public"},
        } for aoi in controller.add_on_instructions.values()},
        _unique_by_name(library_interfaces),
    )


def _unique_by_name(interfaces: list[LibraryInterface]) -> dict[str, LibraryInterface]:
    """Nothing prevents two library interface registrations (EFBSource/
    EFSource/FBSource) from sharing a name; a name that does is never
    resolvable through this map rather than silently picking one."""
    by_name: dict[str, LibraryInterface | None] = {}
    for interface in interfaces:
        if not interface.name:
            continue
        key = interface.name.casefold()
        by_name[key] = None if key in by_name else interface
    return {key: interface for key, interface in by_name.items() if interface is not None}


def _member_path(
    expression: str, symbols: dict[str, Tag | AddOnInstructionParameter], ambiguous: set[str],
    identifier_pattern: str, context: MemberPathContext | None,
) -> tuple[MemberPathResult, Tag | AddOnInstructionParameter | None] | None:
    if context is None:
        return None
    base = re.match(identifier_pattern, expression)
    key = base.group(0).casefold() if base else ""
    symbol = None if key in ambiguous else symbols.get(key)
    result = resolve_member_path(
        expression, symbol, identifier=identifier_pattern, array_pattern=context.array_pattern,
        datatypes=context.datatypes, function_blocks=context.function_blocks,
        library_interfaces=context.library_interfaces,
    )
    return result, symbol


@dataclass(frozen=True)
class GraphicalBindingIssue:
    # The enclosing Program or, when scope == "function_block", AddOnInstruction.
    program_name: str
    routine_name: str
    diagram_index: int
    object_index: int
    # None for a contact-operand issue, which has no pin to index.
    pin_index: int | None
    code: str
    expression: str
    scope: str = "program"


def _call_reference_kind(
    obj: GraphicalObject, pin: GraphicalPin, call_parameter_types: dict[str, dict[str, str]] | None,
) -> str | None:
    """The declared data type (e.g. "SFCCHART_STATE"/"SFCSTEP_STATE") of this
    pin's own formal parameter, from the library interface of the block it
    belongs to -- proves what an identifier-shaped pin *names* (a program or
    an SFC step, not a tag) without hardcoding specific block names like
    INITCHART/SETSTEP; any future call with a parameter of one of these
    documented types is covered the same way.
    """
    if call_parameter_types is None or not obj.type_name or not pin.name:
        return None
    return call_parameter_types.get(obj.type_name.casefold(), {}).get(pin.name.casefold())


def _resolve_diagrams(
    diagrams: list[GraphicalDiagram], container_name: str, routine_name: str, scope: str, *,
    symbols: dict[str, Tag | AddOnInstructionParameter], ambiguous: set[str],
    # `steps`/`step_ambiguous`: the `<step>.X` contact convention's own
    # namespace -- deliberately FB-scope-empty (IEC 61131-3 encapsulation; a
    # DFB body hardcoding a specific project's chart step would not be
    # reusable). `call_step_names`/`ambiguous_call_step_names`: a *separate*
    # namespace for a chart-control call's own SFCSTEP_STATE parameter (see
    # `_call_reference_kind`) -- that call names an external step explicitly
    # by its own argument regardless of scope, the same reasoning
    # `program_names` already applies; defaults to `steps` when not given
    # separately, which is correct for program scope (the same full
    # project-wide namespace either way) and lets FB-body callers supply a
    # real one without also, as a side effect, enabling `.X` contacts there.
    steps: dict[str, str], step_ambiguous: set[str],
    call_step_names: dict[str, str] | None = None, ambiguous_call_step_names: set[str] | None = None,
    program_names: dict[str, str] | None = None, ambiguous_program_names: set[str] | None = None,
    call_parameter_types: dict[str, dict[str, str]] | None = None,
    identifier_pattern: str, step_state_pattern: re.Pattern[str], literal_patterns: tuple[str, ...],
    member_paths: MemberPathContext | None = None, direct_address_pattern: str | None = None,
) -> list[GraphicalBindingIssue]:
    call_step_names = steps if call_step_names is None else call_step_names
    ambiguous_call_step_names = step_ambiguous if ambiguous_call_step_names is None else ambiguous_call_step_names
    program_names = program_names or {}
    ambiguous_program_names = ambiguous_program_names or set()
    issues: list[GraphicalBindingIssue] = []
    for diagram_index, diagram in enumerate(diagrams):
        groups: dict[str, GraphicalVariableReferences] = {}
        diagram.shared_variables.clear()
        for object_index, obj in enumerate(diagram.objects):
            if obj.kind in {"contact", "coil"}:
                obj.operand_binding_kind = None
                obj.target_tag = None
                obj.target_step_name = None
                obj.operand_member_path = None
                obj.operand_binary_expression = None
                expression = obj.operand.strip() if obj.operand is not None else ""
                problem = None
                # A coil cannot legitimately target a step's active-state
                # bit -- that convention is read-only, SFC-engine-owned.
                # Only a contact operand is tested against it.
                step_match = step_state_pattern.fullmatch(expression) if obj.kind == "contact" else None
                if obj.operand is None:
                    obj.operand_binding_kind = "unbound"
                elif step_match:
                    key = step_match.group(1).casefold()
                    if key in step_ambiguous:
                        obj.operand_binding_kind = "ambiguous_step_state"
                        problem = "ambiguous_contact_step_state"
                    elif key in steps:
                        obj.operand_binding_kind = "declared_step_state"
                        obj.target_step_name = steps[key]
                    else:
                        obj.operand_binding_kind = "missing_step_state"
                        problem = "unresolved_contact_step_state"
                elif re.fullmatch(identifier_pattern, expression):
                    key = expression.casefold()
                    if key in ambiguous:
                        obj.operand_binding_kind = "ambiguous_symbol"
                        problem = f"ambiguous_{obj.kind}_symbol"
                    elif key in symbols and isinstance(symbols[key], Tag):
                        obj.operand_binding_kind = "declared_symbol"
                        obj.target_tag = symbols[key]  # type: ignore[assignment]
                    else:
                        obj.operand_binding_kind = "missing_symbol"
                        problem = f"unresolved_{obj.kind}_symbol"
                elif direct_address_pattern is not None and re.fullmatch(direct_address_pattern, expression):
                    # A direct/system address (e.g. "%S1"): real evidence, not a
                    # declared symbol -- classified, not resolved to a target.
                    obj.operand_binding_kind = "direct_address"
                else:
                    obj.operand_binding_kind = "unresolved_expression"
                    problem = f"unresolved_{obj.kind}_expression"
                    proven = _member_path(expression, symbols, ambiguous, identifier_pattern, member_paths)
                    if proven is not None and proven[0].status == "resolved":
                        obj.operand_binding_kind = "declared_member_path"
                        obj.operand_member_path = proven[0].path
                        if isinstance(proven[1], Tag):
                            obj.target_tag = proven[1]
                        problem = None
                    elif proven is not None and proven[0].status == "index_out_of_bounds":
                        obj.operand_binding_kind = "member_path_out_of_bounds"
                        problem = f"{obj.kind}_member_path_out_of_bounds"
                    if problem:
                        binary = resolve_binary_expression(
                            expression, symbols, ambiguous, identifier_pattern, literal_patterns, member_paths)
                        if binary is not None:
                            obj.operand_binding_kind = "declared_expression"
                            obj.operand_binary_expression = binary
                            problem = None
                if problem:
                    issues.append(GraphicalBindingIssue(
                        container_name, routine_name, diagram_index, object_index,
                        None, problem, obj.operand or "", scope,
                    ))
            for pin_index, pin in enumerate(obj.pins):
                pin.target_tag = None
                pin.target_parameter = None
                pin.member_path = None
                pin.binary_expression = None
                pin.target_program_name = None
                pin.target_step_name = None
                expression = pin.expression.strip() if pin.expression is not None else ""
                problem = None
                if pin.expression is None:
                    pin.binding_kind = "unbound"
                elif any(re.fullmatch(pattern, expression, re.IGNORECASE) for pattern in literal_patterns):
                    if pin.direction == "input":
                        pin.binding_kind = "literal"
                    else:
                        pin.binding_kind = "invalid_output_literal"
                        problem = "invalid_output_literal"
                elif direct_address_pattern is not None and re.fullmatch(direct_address_pattern, expression):
                    pin.binding_kind = "direct_address"
                elif re.fullmatch(identifier_pattern, expression):
                    key = expression.casefold()
                    if key in ambiguous:
                        pin.binding_kind = "ambiguous_symbol"
                        problem = "ambiguous_pin_symbol"
                    elif key in symbols:
                        pin.binding_kind = "declared_symbol"
                        target = symbols[key]
                        if isinstance(target, Tag):
                            pin.target_tag = target
                        else:
                            pin.target_parameter = target
                        group = groups.setdefault(key, GraphicalVariableReferences(target.name))
                        if pin.direction == "input":
                            group.input_pins.append((object_index, pin_index))
                        elif pin.direction == "output":
                            group.output_pins.append((object_index, pin_index))
                    else:
                        reference_kind = _call_reference_kind(obj, pin, call_parameter_types)
                        if reference_kind == "SFCCHART_STATE" and key in ambiguous_program_names:
                            pin.binding_kind = "ambiguous_symbol"
                            problem = "ambiguous_pin_symbol"
                        elif reference_kind == "SFCCHART_STATE" and key in program_names:
                            pin.binding_kind = "declared_program_reference"
                            pin.target_program_name = program_names[key]
                        elif reference_kind == "SFCSTEP_STATE" and key in ambiguous_call_step_names:
                            pin.binding_kind = "ambiguous_symbol"
                            problem = "ambiguous_pin_symbol"
                        elif reference_kind == "SFCSTEP_STATE" and key in call_step_names:
                            pin.binding_kind = "declared_step_reference"
                            pin.target_step_name = call_step_names[key]
                        else:
                            pin.binding_kind = "missing_symbol"
                            problem = "unresolved_pin_symbol"
                else:
                    pin.binding_kind = "unresolved_expression"
                    problem = "unresolved_pin_expression"
                    proven = _member_path(expression, symbols, ambiguous, identifier_pattern, member_paths)
                    if proven is not None and proven[0].status == "resolved":
                        # target_tag/target_parameter name the base symbol only. The
                        # pin is deliberately not added to shared-variable groups.
                        pin.binding_kind = "declared_member_path"
                        pin.member_path = proven[0].path
                        if isinstance(proven[1], Tag):
                            pin.target_tag = proven[1]
                        else:
                            pin.target_parameter = proven[1]
                        problem = None
                    elif proven is not None and proven[0].status == "index_out_of_bounds":
                        pin.binding_kind = "member_path_out_of_bounds"
                        problem = "pin_member_path_out_of_bounds"
                    if problem:
                        binary = resolve_binary_expression(
                            expression, symbols, ambiguous, identifier_pattern, literal_patterns, member_paths)
                        if binary is not None:
                            # Not added to shared_variables: a composite expression's
                            # operands are evidence of what it reads, not a wire.
                            pin.binding_kind = "declared_expression"
                            pin.binary_expression = binary
                            problem = None
                if problem:
                    issues.append(GraphicalBindingIssue(
                        container_name, routine_name, diagram_index, object_index,
                        pin_index, problem, pin.expression or "", scope,
                    ))
        diagram.shared_variables.extend(
            group for group in groups.values()
            if len(group.input_pins) + len(group.output_pins) > 1
        )
    return issues


def _program_resources(controller: Controller) -> dict[str, "Resource"]:
    """Program name -> its resource, only when every task scheduling it agrees on one."""
    owners: dict[str, set[str]] = {}
    for task in controller.tasks.values():
        name = task.metadata.get("resource") or ""
        for program in task.scheduled_programs:
            owners.setdefault(program.name, set()).add(name)
    return {
        program: controller.resources[next(iter(names))]
        for program, names in owners.items()
        if len(names) == 1 and next(iter(names)) in controller.resources
    }


def resolve_graphical_bindings(
    controller: Controller, *, identifier_pattern: str,
    literal_patterns: tuple[str, ...], ambiguous_names: frozenset[str] = frozenset(),
    step_names: dict[str, str] | None = None, ambiguous_step_names: frozenset[str] = frozenset(),
    program_names: dict[str, str] | None = None, ambiguous_program_names: frozenset[str] = frozenset(),
    call_parameter_types: dict[str, dict[str, str]] | None = None,
    member_paths: MemberPathContext | None = None, direct_address_pattern: str | None = None,
) -> list[GraphicalBindingIssue]:
    """Classify pins and contact operands in place; retained source text is unchanged.

    Ambiguous declarations must be supplied by a reader when its name-keyed
    model cannot represent all source declarations. Repeated calls rebuild all
    derived bindings and groups rather than accumulating stale results.

    A contact operand shaped ``<name>.X``/``<name>.x`` is Control Expert's
    IEC 61131 step-active-state convention, not a general member grammar; it
    is only recognized when ``<name>`` is a uniquely declared SFC step.
    """
    ambiguous = {name.casefold() for name in ambiguous_names}
    symbols: dict[str, Tag | AddOnInstructionParameter] = {}
    for tag in controller.tags.values():
        key = tag.name.casefold()
        if key in symbols:
            ambiguous.add(key)
        symbols[key] = tag
    steps = dict(step_names or {})
    step_ambiguous = {name.casefold() for name in ambiguous_step_names}
    resolved_program_names = dict(program_names or {})
    resolved_ambiguous_program_names = {name.casefold() for name in ambiguous_program_names}
    step_state_pattern = re.compile(rf"({identifier_pattern})\.[Xx]")
    issues = []
    resources = _program_resources(controller)
    for program in controller.programs.values():
        program_symbols, program_ambiguous = symbols, ambiguous
        resource = resources.get(program.name)
        if resource is not None:
            # A program sees the controller's variables plus its own resource's;
            # a name declared in both scopes is ambiguous, never picked.
            program_symbols, program_ambiguous = dict(symbols), set(ambiguous) | resource.ambiguous_names
            for tag in resource.tags.values():
                key = tag.name.casefold()
                if key in program_symbols:
                    program_ambiguous.add(key)
                program_symbols[key] = tag
        for routine in program.routines.values():
            issues.extend(_resolve_diagrams(
                routine.graphical_diagrams, program.name, routine.name, "program",
                symbols=program_symbols, ambiguous=program_ambiguous, steps=steps,
                step_ambiguous=step_ambiguous, program_names=resolved_program_names,
                ambiguous_program_names=resolved_ambiguous_program_names,
                call_parameter_types=call_parameter_types,
                identifier_pattern=identifier_pattern, step_state_pattern=step_state_pattern,
                literal_patterns=literal_patterns, member_paths=member_paths,
                direct_address_pattern=direct_address_pattern,
            ))
    return issues


def resolve_function_block_bindings(
    controller: Controller, *, identifier_pattern: str, literal_patterns: tuple[str, ...],
    program_names: dict[str, str] | None = None, ambiguous_program_names: frozenset[str] = frozenset(),
    step_names: dict[str, str] | None = None, ambiguous_step_names: frozenset[str] = frozenset(),
    call_parameter_types: dict[str, dict[str, str]] | None = None,
    member_paths: MemberPathContext | None = None, direct_address_pattern: str | None = None,
) -> list[GraphicalBindingIssue]:
    """Resolve pins inside a Function Block body against that FB's own namespace.

    A Function Block body sees only its own parameters and local tags, never
    the project's global tags -- IEC 61131-3 encapsulation, not an evidence
    gap. Each FB is resolved against its own isolated symbol table; the same
    name in two different FBs is not a collision.

    A chart-control call's own project-wide identity references (program/
    chart names, SFC step names -- see ``_call_reference_kind``) are the
    single exception: unlike a step-state ``.X`` contact (deliberately kept
    FB-scope-empty, since it tests a specific project's own chart), a call
    like SETSTEP/INITCHART names an external chart/step explicitly by its own
    parameter, so it is resolved the same project-wide way regardless of
    which scope the call is textually written in -- not itself separately
    evidenced from inside an FB body, but the consistent generalization of
    the same reasoning ``program_names`` already applies here.
    """
    step_state_pattern = re.compile(rf"({identifier_pattern})\.[Xx]")
    resolved_program_names = dict(program_names or {})
    resolved_ambiguous_program_names = {name.casefold() for name in ambiguous_program_names}
    resolved_call_step_names = dict(step_names or {})
    resolved_ambiguous_call_step_names = {name.casefold() for name in ambiguous_step_names}
    issues: list[GraphicalBindingIssue] = []
    for aoi in controller.add_on_instructions.values():
        symbols: dict[str, Tag | AddOnInstructionParameter] = {}
        ambiguous: set[str] = set()
        for source in (aoi.parameters.values(), aoi.local_tags.values()):
            for item in source:
                key = item.name.casefold()
                if key in symbols:
                    ambiguous.add(key)
                symbols[key] = item
        for routine in aoi.routines.values():
            issues.extend(_resolve_diagrams(
                routine.graphical_diagrams, aoi.name, routine.name, "function_block",
                symbols=symbols, ambiguous=ambiguous, steps={}, step_ambiguous=set(),
                call_step_names=resolved_call_step_names, ambiguous_call_step_names=resolved_ambiguous_call_step_names,
                program_names=resolved_program_names, ambiguous_program_names=resolved_ambiguous_program_names,
                call_parameter_types=call_parameter_types,
                identifier_pattern=identifier_pattern, step_state_pattern=step_state_pattern,
                literal_patterns=literal_patterns, member_paths=member_paths,
                direct_address_pattern=direct_address_pattern,
            ))
    return issues


@dataclass(frozen=True)
class CoilWriteLocation:
    """One resolved coil write, by source location -- not itself a diagnostic."""

    program_name: str
    routine_name: str
    diagram_index: int
    object_index: int


@dataclass(frozen=True)
class TagWriteEvidence:
    """Every coil across a controller's programs that writes a given declared
    tag, grouped by tag identity. More than one location is real and common
    (e.g. a conditional set in one section, a conditional reset in another)
    -- this never claims the writes are erroneous, redundant, or mutually
    exclusive, only that they exist. Consumers checking "multiple writers"
    filter on ``len(locations) > 1`` themselves.
    """

    tag_name: str
    locations: tuple[CoilWriteLocation, ...]


def resolve_coil_write_evidence(controller: Controller) -> list[TagWriteEvidence]:
    """Group every resolved coil write by its declared target tag, across all
    top-level programs.

    Deliberately scoped to LD coils only -- the one graphical shape this
    project's own prior work already treats as an unconditional write (see
    the coil operand binding checkpoint: "a coil cannot legitimately write a
    step's active-state bit"). A general FBD/EFB "output" pin is excluded on
    purpose: source pin direction alone does not prove memory read/write
    effects (see ``GraphicalPin.direction``), so claiming one is a write
    would be exactly the inference this project has repeatedly declined to
    make elsewhere. Function Block bodies are excluded too -- a coil there
    writes the FB *definition*'s own local tag, shared textually across
    every instantiation, not a single project-wide storage location the way
    a program-scope tag is.
    """
    by_tag: dict[int, tuple[Tag, list[CoilWriteLocation]]] = {}
    for program in controller.programs.values():
        for routine in program.routines.values():
            for diagram_index, diagram in enumerate(routine.graphical_diagrams):
                for object_index, obj in enumerate(diagram.objects):
                    if obj.kind != "coil" or obj.target_tag is None:
                        continue
                    key = id(obj.target_tag)
                    _, locations = by_tag.setdefault(key, (obj.target_tag, []))
                    locations.append(CoilWriteLocation(
                        program_name=program.name, routine_name=routine.name,
                        diagram_index=diagram_index, object_index=object_index,
                    ))
    return [TagWriteEvidence(tag_name=tag.name, locations=tuple(locations))
            for tag, locations in by_tag.values()]
