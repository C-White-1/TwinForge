"""Resolve simple graphical pin expressions without inferring execution edges."""
from __future__ import annotations

from dataclasses import dataclass
import re

from twinforge.model import AddOnInstructionParameter, Controller, GraphicalDiagram, GraphicalVariableReferences, Tag


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


def _resolve_diagrams(
    diagrams: list[GraphicalDiagram], container_name: str, routine_name: str, scope: str, *,
    symbols: dict[str, Tag | AddOnInstructionParameter], ambiguous: set[str],
    steps: dict[str, str], step_ambiguous: set[str],
    identifier_pattern: str, step_state_pattern: re.Pattern[str], literal_patterns: tuple[str, ...],
) -> list[GraphicalBindingIssue]:
    issues: list[GraphicalBindingIssue] = []
    for diagram_index, diagram in enumerate(diagrams):
        groups: dict[str, GraphicalVariableReferences] = {}
        diagram.shared_variables.clear()
        for object_index, obj in enumerate(diagram.objects):
            if obj.kind in {"contact", "coil"}:
                obj.operand_binding_kind = None
                obj.target_tag = None
                obj.target_step_name = None
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
                else:
                    obj.operand_binding_kind = "unresolved_expression"
                    problem = f"unresolved_{obj.kind}_expression"
                if problem:
                    issues.append(GraphicalBindingIssue(
                        container_name, routine_name, diagram_index, object_index,
                        None, problem, obj.operand or "", scope,
                    ))
            for pin_index, pin in enumerate(obj.pins):
                pin.target_tag = None
                pin.target_parameter = None
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
                        pin.binding_kind = "missing_symbol"
                        problem = "unresolved_pin_symbol"
                else:
                    pin.binding_kind = "unresolved_expression"
                    problem = "unresolved_pin_expression"
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


def resolve_graphical_bindings(
    controller: Controller, *, identifier_pattern: str,
    literal_patterns: tuple[str, ...], ambiguous_names: frozenset[str] = frozenset(),
    step_names: dict[str, str] | None = None, ambiguous_step_names: frozenset[str] = frozenset(),
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
    step_state_pattern = re.compile(rf"({identifier_pattern})\.[Xx]")
    issues = []
    for program in controller.programs.values():
        for routine in program.routines.values():
            issues.extend(_resolve_diagrams(
                routine.graphical_diagrams, program.name, routine.name, "program",
                symbols=symbols, ambiguous=ambiguous, steps=steps, step_ambiguous=step_ambiguous,
                identifier_pattern=identifier_pattern, step_state_pattern=step_state_pattern,
                literal_patterns=literal_patterns,
            ))
    return issues


def resolve_function_block_bindings(
    controller: Controller, *, identifier_pattern: str, literal_patterns: tuple[str, ...],
) -> list[GraphicalBindingIssue]:
    """Resolve pins inside a Function Block body against that FB's own namespace.

    A Function Block body sees only its own parameters and local tags, never
    the project's global tags -- IEC 61131-3 encapsulation, not an evidence
    gap. Each FB is resolved against its own isolated symbol table; the same
    name in two different FBs is not a collision.
    """
    step_state_pattern = re.compile(rf"({identifier_pattern})\.[Xx]")
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
                identifier_pattern=identifier_pattern, step_state_pattern=step_state_pattern,
                literal_patterns=literal_patterns,
            ))
    return issues
