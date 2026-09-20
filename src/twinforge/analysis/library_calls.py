"""Match source calls to signature evidence without claiming type compatibility."""
import re

from twinforge.model import Controller
from twinforge.model.graphical import GraphicalObject, GraphicalPin
from twinforge.model.library_interface import LibraryInterface

# Schneider EF/EFB sources mark a repeatable parameter template with a literal
# "(Extensible)" comment suffix (observed on ADD's IN1). This is vendor
# evidence of the convention, not a naming heuristic applied on our own guess.
_EXTENSIBLE_MARKER = "(Extensible)"
_TRAILING_DIGITS = re.compile(r"^(.*?)(\d+)$")


def _extensible_templates(interface: LibraryInterface) -> dict[tuple[str, str], list[int]]:
    templates: dict[tuple[str, str], list[int]] = {}
    for index, parameter in enumerate(interface.parameters):
        if not parameter.name or not parameter.comment or _EXTENSIBLE_MARKER not in parameter.comment:
            continue
        match = _TRAILING_DIGITS.match(parameter.name)
        if not match:
            continue
        templates.setdefault((match.group(1).casefold(), parameter.direction), []).append(index)
    return templates


def match_library_calls(
    controller: Controller, interfaces: list[LibraryInterface], *,
    direction_aliases: tuple[tuple[str, str], ...] = (),
) -> list[tuple[str, GraphicalObject | GraphicalPin]]:
    issues: list[tuple[str, GraphicalObject | GraphicalPin]] = []
    for program in controller.programs.values():
        for routine in program.routines.values():
            for diagram in routine.graphical_diagrams:
                for obj in diagram.objects:
                    obj.interface_status = None
                    obj.interface_index = None
                    for pin in obj.pins:
                        pin.interface_status = None
                        pin.parameter_index = None
                    if obj.kind != "block" or not obj.type_name:
                        continue
                    candidates = [index for index, interface in enumerate(interfaces)
                                  if interface.name and interface.name.casefold() == obj.type_name.casefold()]
                    if len(candidates) != 1:
                        obj.interface_status = "ambiguous" if candidates else "missing"
                        issues.append(("unresolved_library_interface", obj))
                        continue
                    obj.interface_index = candidates[0]
                    obj.interface_status = "matched"
                    interface = interfaces[candidates[0]]
                    templates = _extensible_templates(interface)
                    for pin in obj.pins:
                        matches = [index for index, parameter in enumerate(interface.parameters)
                                   if parameter.name and pin.name
                                   and parameter.name.casefold() == pin.name.casefold()
                                   and (parameter.direction == pin.direction
                                        or (parameter.direction, pin.direction) in direction_aliases)]
                        extensible_match = _TRAILING_DIGITS.match(pin.name) if pin.name else None
                        extensible_candidates = (
                            templates.get((extensible_match.group(1).casefold(), pin.direction), [])
                            if extensible_match else []
                        )
                        if len(matches) == 1:
                            pin.interface_status = ("matched" if interface.parameters[matches[0]].direction == pin.direction
                                                    else "matched_direction_alias")
                            pin.parameter_index = matches[0]
                        elif len(matches) > 1:
                            pin.interface_status = "ambiguous"
                            issues.append(("unresolved_library_pin", pin))
                        elif len(extensible_candidates) == 1:
                            pin.interface_status = "matched_extensible"
                            pin.parameter_index = extensible_candidates[0]
                        elif len(extensible_candidates) > 1:
                            pin.interface_status = "ambiguous"
                            issues.append(("unresolved_library_pin", pin))
                        elif pin.role in {"execution_enable", "execution_status"}:
                            pin.interface_status = "implicit_execution_pin"
                        else:
                            pin.interface_status = "unresolved_convention"
                            issues.append(("unresolved_library_pin", pin))
    return issues
