"""Resolve simple graphical pin expressions without inferring execution edges."""
from __future__ import annotations

from dataclasses import dataclass
import re

from twinforge.model import Controller, GraphicalVariableReferences


@dataclass(frozen=True)
class GraphicalBindingIssue:
    program_name: str
    routine_name: str
    diagram_index: int
    object_index: int
    pin_index: int
    code: str
    expression: str


def resolve_graphical_bindings(
    controller: Controller, *, identifier_pattern: str,
    literal_patterns: tuple[str, ...], ambiguous_names: frozenset[str] = frozenset(),
) -> list[GraphicalBindingIssue]:
    """Classify pins in place; retained source expressions remain unchanged.

    Ambiguous declarations must be supplied by a reader when its name-keyed
    model cannot represent all source declarations. Repeated calls rebuild all
    derived bindings and groups rather than accumulating stale results.
    """
    ambiguous = {name.casefold() for name in ambiguous_names}
    symbols = {}
    for tag in controller.tags.values():
        key = tag.name.casefold()
        if key in symbols:
            ambiguous.add(key)
        symbols[key] = tag
    issues = []
    for program in controller.programs.values():
        for routine in program.routines.values():
            for diagram_index, diagram in enumerate(routine.graphical_diagrams):
                groups: dict[str, GraphicalVariableReferences] = {}
                diagram.shared_variables.clear()
                for object_index, obj in enumerate(diagram.objects):
                    for pin_index, pin in enumerate(obj.pins):
                        pin.target_tag = None
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
                                pin.target_tag = symbols[key]
                                group = groups.setdefault(key, GraphicalVariableReferences(symbols[key].name))
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
                                program.name, routine.name, diagram_index, object_index,
                                pin_index, problem, pin.expression or "",
                            ))
                diagram.shared_variables.extend(
                    group for group in groups.values()
                    if len(group.input_pins) + len(group.output_pins) > 1
                )
    return issues
