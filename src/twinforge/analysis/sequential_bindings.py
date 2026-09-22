"""Conservative chart variable binding, independent of vendor XML and execution."""
import re

from twinforge.model import Controller, Tag
from twinforge.model.sequential import SequentialElement


def resolve_sequential_bindings(
    controller: Controller, *, identifier_pattern: str,
    ambiguous_names: frozenset[str] = frozenset(),
) -> list[tuple[str, SequentialElement]]:
    """Rebuild simple symbol bindings; do not interpret member expressions or effects."""
    symbols: dict[str, Tag] = {}
    ambiguous = {name.casefold() for name in ambiguous_names}
    for tag in controller.tags.values():
        key = tag.name.casefold()
        if key in symbols:
            ambiguous.add(key)
        symbols[key] = tag
    issues: list[tuple[str, SequentialElement]] = []

    def visit(element: SequentialElement, parent_kind: str | None = None) -> None:
        element.binding_kind = None
        element.target_symbol_name = None
        element.target_member_name = None
        element.member_data_type = None
        if element.kind == "variable_reference" and parent_kind in {"condition", "action_target"}:
            expression = (element.text or "").strip()
            key = expression.casefold()
            parts = expression.split(".")
            if len(parts) == 2 and all(re.fullmatch(identifier_pattern, part) for part in parts):
                base, member = parts
                base_key = base.casefold()
                status = "unresolved_member"
                if base_key in ambiguous:
                    status = "ambiguous_symbol"
                elif base_key in symbols:
                    tag = symbols[base_key]
                    # The canonical source of "what is this tag's type", the
                    # same one member-path resolution and unresolved_type
                    # gating already use -- a DFB instance's own parameters
                    # (function_block_instance) take precedence the same way
                    # there, over a library (EFB) interface's (library_type).
                    parameter = None
                    if tag.function_block_instance is not None:
                        parameter = tag.function_block_instance.parameters.get(member)
                        if parameter is None:
                            parameter = next(
                                (p for p in tag.function_block_instance.parameters.values()
                                 if p.name.casefold() == member.casefold()), None)
                    elif tag.library_type is not None:
                        matches = [p for p in tag.library_type.parameters
                                  if p.name and p.name.casefold() == member.casefold()]
                        if len(matches) == 1:
                            parameter = matches[0]
                    if parameter is not None:
                        status = "declared_member"
                        element.target_symbol_name = tag.name
                        element.target_member_name = parameter.name
                        element.member_data_type = parameter.data_type
            elif not re.fullmatch(identifier_pattern, expression):
                status = "unresolved_expression"
            elif key in ambiguous:
                status = "ambiguous_symbol"
            elif key in symbols:
                status = "declared_symbol"
                element.target_symbol_name = symbols[key].name
            else:
                status = "missing_symbol"
            element.binding_kind = status
            if status not in {"declared_symbol", "declared_member"}:
                issues.append(("sfc_" + status, element))
        for child in element.children:
            visit(child, element.kind)

    for program in controller.programs.values():
        for routine in program.routines.values():
            for chart in routine.sequential_charts:
                for element in chart.elements + chart.transition_definitions:
                    visit(element)
    return issues
