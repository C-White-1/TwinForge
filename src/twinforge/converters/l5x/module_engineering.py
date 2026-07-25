"""Extract engineering metadata embedded in L5X module configuration."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from twinforge.converters.diagnostics import (
    ConversionDiagnostic,
    DiagnosticSeverity,
)
from twinforge.model import (
    EngineeringRangeEvidence,
    EngineeringUnitConfidence,
    EngineeringUnitEvidence,
    EngineeringUnitSource,
)
from twinforge.parsers.l5x.capture import CapturedSection

from .conversion_value import emit_diagnostic


def engineering_unit_key(direction: str, operand: str) -> str:
    """Return the normalized lookup key used for module engineering metadata."""

    return f"{direction}.{operand.lstrip('.')}".casefold()


def extract_engineering_units(
    module: CapturedSection,
    slot: int | None,
    diagnostics: list[ConversionDiagnostic] | None,
) -> dict[str, EngineeringUnitEvidence]:
    """Extract explicit units from captured connection tag XML."""

    units: dict[str, EngineeringUnitEvidence] = {}
    for communications in module.elements.get("Communications", []):
        for connections in communications.elements.get("Connections", []):
            for connection in connections.elements.get("Connection", []):
                for element_name, direction in (
                    ("InputTag", "I"),
                    ("OutputTag", "O"),
                ):
                    for tag_data in connection.elements.get(element_name, []):
                        _collect_tag_units(
                            tag_data,
                            module,
                            direction,
                            slot,
                            units,
                            diagnostics,
                        )
    return units


def _collect_tag_units(
    tag_data: CapturedSection,
    module: CapturedSection,
    direction: str,
    slot: int | None,
    units: dict[str, EngineeringUnitEvidence],
    diagnostics: list[ConversionDiagnostic] | None,
) -> None:
    """Collect unit nodes while preserving capture's mixed child ordering."""

    for child in tag_data.ordered_children:
        if not isinstance(child, ET.Element) or child.tag != "EngineeringUnits":
            continue
        for unit in child:
            if unit.tag != "EngineeringUnit":
                continue
            operand = unit.attrib.get("Operand")
            symbol = (unit.text or "").strip()
            if not operand or not symbol:
                continue
            key = engineering_unit_key(direction, operand)
            source_operand = (
                f"Local:{slot}:{direction}{operand}"
                if slot is not None
                else operand
            )
            evidence = EngineeringUnitEvidence(
                symbol=symbol,
                source=EngineeringUnitSource.MODULE_CHANNEL,
                confidence=EngineeringUnitConfidence.EXPLICIT,
                source_operand=source_operand,
            )
            previous = units.get(key)
            if (
                previous is not None
                and previous.symbol.casefold() != symbol.casefold()
            ):
                emit_diagnostic(
                    diagnostics,
                    DiagnosticSeverity.WARNING,
                    "conflicting_module_engineering_unit",
                    (
                        f"module {module.attributes.get('Name', '')!r} "
                        f"has conflicting units for {operand}"
                    ),
                    module,
                    "EngineeringUnit",
                    f"{previous.symbol}, {symbol}",
                )
                continue
            units[key] = evidence


def extract_engineering_ranges(
    module: CapturedSection,
    slot: int | None,
) -> dict[str, EngineeringRangeEvidence]:
    """Extract explicit configured channel ranges from decorated ConfigTag data."""

    ranges: dict[str, EngineeringRangeEvidence] = {}
    for communications in module.elements.get("Communications", []):
        for config_tag in communications.elements.get("ConfigTag", []):
            for data in config_tag.ordered_children:
                if (
                    not isinstance(data, ET.Element)
                    or data.tag != "Data"
                    or data.attrib.get("Format") != "Decorated"
                ):
                    continue
                _collect_config_ranges(data, slot, ranges)
    return ranges


def _collect_config_ranges(
    data: ET.Element,
    slot: int | None,
    ranges: dict[str, EngineeringRangeEvidence],
) -> None:
    """Promote channel range pairs from one decorated configuration payload."""

    structure = data.find("Structure")
    if structure is None:
        return
    for channel in structure.findall("StructureMember"):
        match = re.fullmatch(
            r"Ch(?P<number>\d+)Config",
            channel.attrib.get("Name", ""),
            re.IGNORECASE,
        )
        if match is None:
            continue
        values: dict[str, str] = {}
        for member in channel.findall("DataValueMember"):
            name = member.attrib.get("Name")
            value = member.attrib.get("Value")
            if name is not None and value is not None:
                values[name] = value
        lower_value = values.get("LowEngineering")
        upper_value = values.get("HighEngineering")
        if lower_value is None or upper_value is None:
            continue
        try:
            lower = float(lower_value)
            upper = float(upper_value)
        except ValueError:
            continue

        number = match.group("number")
        source = (
            f"Local:{slot}:C.Ch{number}Config"
            if slot is not None
            else f"Ch{number}Config"
        )
        evidence = EngineeringRangeEvidence(
            lower=lower,
            upper=upper,
            confidence=EngineeringUnitConfidence.EXPLICIT,
            source_operand=source,
        )
        # L5X configuration members do not encode direction. Retain both
        # candidates; downstream alias resolution selects the matching member.
        for direction in ("I", "O"):
            ranges[
                engineering_unit_key(direction, f"Ch{number}Data")
            ] = evidence
