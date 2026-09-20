"""Conservative chart variable binding, independent of vendor XML and execution."""
import re

from twinforge.model import Controller
from twinforge.model.library_interface import LibraryInterface
from twinforge.model.sequential import SequentialElement


def resolve_sequential_bindings(
    controller: Controller, *, identifier_pattern: str,
    interfaces: list[LibraryInterface] | None = None,
    ambiguous_names: frozenset[str] = frozenset(),
) -> list[tuple[str, SequentialElement]]:
    """Rebuild simple symbol bindings; do not interpret member expressions or effects."""
    symbols: dict[str, str] = {}
    ambiguous = {name.casefold() for name in ambiguous_names}
    for tag in controller.tags.values():
        key = tag.name.casefold()
        if key in symbols:
            ambiguous.add(key)
        symbols[key] = tag.name
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
                    tag = next(t for t in controller.tags.values() if t.name == symbols[base_key])
                    definitions = [i for i in interfaces or [] if i.kind == "function_block"
                                   and i.name and i.name.casefold() == (tag.data_type or "").casefold()]
                    if len(definitions) == 1:
                        parameters = [p for p in definitions[0].parameters
                                      if p.name and p.name.casefold() == member.casefold()]
                        if len(parameters) == 1:
                            parameter = parameters[0]
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
                element.target_symbol_name = symbols[key]
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
