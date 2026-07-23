from __future__ import annotations

import re

from twinforge.converters.diagnostics import (
    ConversionDiagnostic,
    DiagnosticSeverity,
)
from twinforge.model import (
    Controller,
    EngineeringUnitConfidence,
    EngineeringUnitEvidence,
    EngineeringUnitSource,
    Module,
    Program,
    Tag,
)


_LOCAL_ALIAS = re.compile(
    r"^Local:(?P<slot>\d+):(?P<direction>[IOC])(?:[.:])(?P<member>.+)$",
    re.IGNORECASE,
)
_NAMED_MODULE_ALIAS = re.compile(
    r"^(?P<module>[^:]+):(?P<direction>[IOC])(?:[.:])(?P<member>.+)$",
    re.IGNORECASE,
)
_DESCRIPTION_UNIT = re.compile(
    r"\((?P<unit>[A-Za-z°%][A-Za-z0-9°%/·*^._-]{0,15})\)\s*$"
)
_COMPARISON = re.compile(
    r"(?:EQU|NEQ|GRT|GEQ|LES|LEQ)\s*"
    r"\(\s*(?P<left>[^,()]+)\s*,\s*(?P<right>[^,()]+)\s*\)",
    re.IGNORECASE,
)
_CONFIDENCE_RANK = {
    EngineeringUnitConfidence.INFERRED: 1,
    EngineeringUnitConfidence.DERIVED: 2,
    EngineeringUnitConfidence.EXPLICIT: 3,
}


def resolve_engineering_units(
    controller: Controller,
    *,
    diagnostics: list[ConversionDiagnostic] | None = None,
) -> None:
    """Resolve explicit and inferred engineering-unit evidence onto tags."""

    modules = _controller_modules(controller)
    modules_by_name = {module.name.casefold(): module for module in modules}
    modules_by_slot = {
        module.slot: module for module in modules if module.slot is not None
    }
    for tag in _all_tags(controller):
        if tag.alias_for:
            evidence = _alias_unit(
                tag.alias_for, modules_by_slot, modules_by_name
            )
            if evidence is not None:
                _add_evidence(tag, evidence, diagnostics)
        description_evidence = _description_evidence(tag)
        if description_evidence is not None:
            _add_evidence(tag, description_evidence, diagnostics)

    for program in controller.iter_programs():
        tags = dict(controller.tags)
        tags.update(program.tags)
        for routine in program.iter_routines():
            for rung in routine.ladder_rungs:
                _resolve_comparisons(
                    rung.text or "",
                    tags,
                    diagnostics,
                    program,
                    routine.name,
                    rung.number,
                )


def _controller_modules(controller: Controller) -> list[Module]:
    modules: list[Module] = list(controller.unplaced_modules)
    for chassis in controller.iter_chassis():
        for module in chassis.iter_modules():
            modules.append(module)
            modules.extend(_descendants(module))
    return modules


def _descendants(module: Module) -> list[Module]:
    descendants: list[Module] = []
    for child in module.child_modules:
        descendants.append(child)
        descendants.extend(_descendants(child))
    return descendants


def _all_tags(controller: Controller) -> list[Tag]:
    tags = list(controller.tags.values())
    for program in controller.iter_programs():
        tags.extend(program.tags.values())
    return tags


def _alias_unit(
    operand: str,
    modules_by_slot: dict[int, Module],
    modules_by_name: dict[str, Module],
) -> EngineeringUnitEvidence | None:
    local = _LOCAL_ALIAS.fullmatch(operand)
    if local is not None:
        module = modules_by_slot.get(int(local.group("slot")))
        if module is None:
            return None
        return module.engineering_units.get(
            _unit_key(local.group("direction"), local.group("member"))
        )
    named = _NAMED_MODULE_ALIAS.fullmatch(operand)
    if named is None:
        return None
    module = modules_by_name.get(named.group("module").casefold())
    if module is None:
        return None
    return module.engineering_units.get(
        _unit_key(named.group("direction"), named.group("member"))
    )


def _description_evidence(tag: Tag) -> EngineeringUnitEvidence | None:
    if not tag.description:
        return None
    match = _DESCRIPTION_UNIT.search(tag.description)
    if match is None:
        return None
    return EngineeringUnitEvidence(
        symbol=match.group("unit"),
        source=EngineeringUnitSource.TAG_DESCRIPTION,
        confidence=EngineeringUnitConfidence.INFERRED,
        inherited_from=tag.name,
    )


def _resolve_comparisons(
    text: str,
    tags: dict[str, Tag],
    diagnostics: list[ConversionDiagnostic] | None,
    program: Program,
    routine_name: str,
    rung_number: int | None,
) -> None:
    for comparison in _COMPARISON.finditer(text):
        left = tags.get(comparison.group("left").strip())
        right = tags.get(comparison.group("right").strip())
        if left is None or right is None:
            continue
        if left.engineering_unit and right.engineering_unit:
            if not _same_symbol(
                left.engineering_unit.symbol,
                right.engineering_unit.symbol,
            ):
                _unit_conflict(
                    diagnostics,
                    right.name,
                    left.engineering_unit.symbol,
                    right.engineering_unit.symbol,
                    (
                        f"{program.name}/{routine_name} rung "
                        f"{rung_number}"
                    ),
                )
            else:
                _inherit_comparison_unit(
                    right, left, diagnostics
                )
                _inherit_comparison_unit(
                    left, right, diagnostics
                )
        elif left.engineering_unit:
            _inherit_comparison_unit(right, left, diagnostics)
        elif right.engineering_unit:
            _inherit_comparison_unit(left, right, diagnostics)


def _inherit_comparison_unit(
    target: Tag,
    source: Tag,
    diagnostics: list[ConversionDiagnostic] | None,
) -> None:
    unit = source.engineering_unit
    if unit is None:
        return
    confidence = (
        EngineeringUnitConfidence.INFERRED
        if unit.confidence is EngineeringUnitConfidence.INFERRED
        else EngineeringUnitConfidence.DERIVED
    )
    _add_evidence(
        target,
        EngineeringUnitEvidence(
            symbol=unit.symbol,
            source=EngineeringUnitSource.COMPARISON,
            confidence=confidence,
            source_operand=source.name,
            inherited_from=source.name,
        ),
        diagnostics,
    )


def _add_evidence(
    tag: Tag,
    evidence: EngineeringUnitEvidence,
    diagnostics: list[ConversionDiagnostic] | None,
) -> None:
    if evidence not in tag.engineering_unit_evidence:
        tag.engineering_unit_evidence.append(evidence)
    current = tag.engineering_unit
    if current is None:
        tag.engineering_unit = evidence
        return
    if not _same_symbol(current.symbol, evidence.symbol):
        _unit_conflict(
            diagnostics,
            tag.name,
            current.symbol,
            evidence.symbol,
            evidence.source.value,
        )
        if _CONFIDENCE_RANK[evidence.confidence] > _CONFIDENCE_RANK[
            current.confidence
        ]:
            tag.engineering_unit = evidence
        return
    if _CONFIDENCE_RANK[evidence.confidence] > _CONFIDENCE_RANK[
        current.confidence
    ]:
        tag.engineering_unit = evidence


def _unit_conflict(
    diagnostics: list[ConversionDiagnostic] | None,
    tag_name: str,
    first: str,
    second: str,
    source: str,
) -> None:
    if diagnostics is None:
        return
    diagnostics.append(
        ConversionDiagnostic(
            severity=DiagnosticSeverity.WARNING,
            code="engineering_unit_conflict",
            message=(
                f"tag {tag_name!r} has conflicting engineering units "
                f"{first!r} and {second!r}"
            ),
            object_name=tag_name,
            field="EngineeringUnit",
            raw_value=source,
        )
    )


def _unit_key(direction: str, member: str) -> str:
    return f"{direction}.{member.lstrip('.')}".casefold()


def _same_symbol(left: str, right: str) -> bool:
    return left.strip().casefold() == right.strip().casefold()
