from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from twinforge.converters.diagnostics import (
    ConversionDiagnostic,
    DiagnosticSeverity,
)
from twinforge.model import (
    Connection,
    ElectronicKey,
    EngineeringRangeEvidence,
    EngineeringUnitConfidence,
    EngineeringUnitEvidence,
    EngineeringUnitSource,
    Identity,
    IODirection,
    IOSignalType,
    KeyingMode,
    ModuleCapability,
    Revision,
    VendorIdentity,
)
from twinforge.model.module import Module
from twinforge.parsers.l5x.capture import CapturedSection
from twinforge.schema.l5x.modules import EKEY_ATTRIBUTES, MODULE_ATTRIBUTES
from twinforge.schema.l5x.spec import AttributeSpec

from .source_extension import captured_to_source_extension


_KEYING_MODES = {
    "CompatibleModule": KeyingMode.COMPATIBLE_MODULE,
    "ExactMatch": KeyingMode.EXACT_MATCH,
    "Disabled": KeyingMode.DISABLED,
    "Custom": KeyingMode.CUSTOM,
}


def convert_module(
    section: CapturedSection,
    *,
    slot: int | None = None,
    diagnostics: list[ConversionDiagnostic] | None = None,
) -> Module:
    """Convert one captured L5X ``Module`` section into a model module."""

    if section.tag != "Module":
        raise ValueError(f"expected a Module section, got {section.tag!r}")

    address = _module_address(section)
    resolved_slot = _numeric_slot(address) if slot is None else slot
    identity = _identity(section, MODULE_ATTRIBUTES, diagnostics)
    identity.source_extensions.append(captured_to_source_extension(section))
    engineering_units = _engineering_units(
        section, resolved_slot, diagnostics
    )
    engineering_ranges = _engineering_ranges(section, resolved_slot)

    module = Module(
        name=section.attributes.get("Name", ""),
        slot=resolved_slot,
        address=address,
        catalog=section.attributes.get("CatalogNumber", ""),
        identity=identity,
        electronic_key=_electronic_key(section, diagnostics),
        inhibited=_optional_bool(
            section.attributes.get("Inhibited"), "Inhibited", section, diagnostics
        ),
        major_fault_on_connection_loss=_optional_bool(
            section.attributes.get("MajorFault"),
            "MajorFault",
            section,
            diagnostics,
        ),
        engineering_units=engineering_units,
        engineering_ranges=engineering_ranges,
        capability=_module_capability(
            section,
            identity,
            engineering_ranges,
        ),
        source_extensions=[captured_to_source_extension(section)],
    )
    for connection in _connections(section):
        module.add_connection(connection)
    return module


def _engineering_units(
    module: CapturedSection,
    slot: int | None,
    diagnostics: list[ConversionDiagnostic] | None,
) -> dict[str, EngineeringUnitEvidence]:
    units: dict[str, EngineeringUnitEvidence] = {}
    for communications in module.elements.get("Communications", []):
        for connections in communications.elements.get("Connections", []):
            for connection in connections.elements.get("Connection", []):
                for element_name, direction in (
                    ("InputTag", "I"),
                    ("OutputTag", "O"),
                ):
                    for tag_data in connection.elements.get(
                        element_name, []
                    ):
                        for child in tag_data.ordered_children:
                            if (
                                not isinstance(child, ET.Element)
                                or child.tag != "EngineeringUnits"
                            ):
                                continue
                            for unit in child:
                                if unit.tag != "EngineeringUnit":
                                    continue
                                operand = unit.attrib.get("Operand")
                                symbol = (unit.text or "").strip()
                                if not operand or not symbol:
                                    continue
                                key = _unit_key(direction, operand)
                                source_operand = (
                                    f"Local:{slot}:{direction}"
                                    f"{operand}"
                                    if slot is not None
                                    else operand
                                )
                                evidence = EngineeringUnitEvidence(
                                    symbol=symbol,
                                    source=(
                                        EngineeringUnitSource.MODULE_CHANNEL
                                    ),
                                    confidence=(
                                        EngineeringUnitConfidence.EXPLICIT
                                    ),
                                    source_operand=source_operand,
                                )
                                previous = units.get(key)
                                if (
                                    previous is not None
                                    and previous.symbol.casefold()
                                    != symbol.casefold()
                                ):
                                    _emit(
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
    return units


def _unit_key(direction: str, operand: str) -> str:
    return f"{direction}.{operand.lstrip('.')}".casefold()


def _engineering_ranges(
    module: CapturedSection,
    slot: int | None,
) -> dict[str, EngineeringRangeEvidence]:
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
                structure = data.find("Structure")
                if structure is None:
                    continue
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
                    for direction in ("I", "O"):
                        ranges[
                            _unit_key(direction, f"Ch{number}Data")
                        ] = evidence
    return ranges


def _module_capability(
    module: CapturedSection,
    identity: Identity,
    engineering_ranges: dict[str, EngineeringRangeEvidence],
) -> ModuleCapability | None:
    vendor = identity.vendor
    if vendor is None or vendor.id != 1:
        return None
    catalog = module.attributes.get("CatalogNumber", "")
    match = re.fullmatch(
        r"1756-(?P<direction>[IO])(?P<signal>[BF])"
        r"(?P<count>\d+)[A-Z0-9]*",
        catalog,
        re.IGNORECASE,
    )
    if match is None:
        return None
    direction = (
        IODirection.INPUT
        if match.group("direction").upper() == "I"
        else IODirection.OUTPUT
    )
    signal_type = (
        IOSignalType.DIGITAL
        if match.group("signal").upper() == "B"
        else IOSignalType.ANALOG
    )
    nominal_count = int(match.group("count"))
    if signal_type is IOSignalType.DIGITAL:
        configured_count = nominal_count
    else:
        prefix = "i." if direction is IODirection.INPUT else "o."
        configured_count = len(
            {
                key
                for key in engineering_ranges
                if key.startswith(prefix)
            }
        )
        if configured_count == 0:
            configured_count = None
    return ModuleCapability(
        signal_type=signal_type,
        direction=direction,
        nominal_channel_count=nominal_count,
        configured_channel_count=configured_count,
        source="rockwell_1756_catalog_convention+l5x_configuration",
    )


def _electronic_key(
    module: CapturedSection,
    diagnostics: list[ConversionDiagnostic] | None,
) -> ElectronicKey | None:
    sections = module.elements.get("EKey", [])
    if not sections:
        return None

    section = sections[0]
    state = section.attributes.get("State")
    mode = _KEYING_MODES.get(state) if state is not None else None
    unknown_mode = state if state is not None and mode is None else None
    if unknown_mode is not None:
        _emit(
            diagnostics,
            DiagnosticSeverity.WARNING,
            "unknown_keying_mode",
            f"module {module.attributes.get('Name', '')!r} uses unknown EKey state {state!r}",
            module,
            "State",
            state,
        )
    identity = None
    if any(
        name in section.attributes
        for name in ("Vendor", "ProductType", "ProductCode", "Major", "Minor")
    ):
        identity = _identity(section, EKEY_ATTRIBUTES, diagnostics, module)
        identity.source_extensions.append(captured_to_source_extension(section))
    if mode is KeyingMode.CUSTOM:
        missing = [
            name
            for name in ("Vendor", "ProductType", "ProductCode", "Major", "Minor")
            if name not in section.attributes
        ]
        if missing:
            _emit(
                diagnostics,
                DiagnosticSeverity.WARNING,
                "incomplete_custom_ekey",
                f"custom EKey is missing: {', '.join(missing)}",
                module,
            )

    return ElectronicKey(
        mode=mode,
        identity=identity,
        unknown_mode=unknown_mode,
        source_extensions=[captured_to_source_extension(section)],
    )


def _connections(module: CapturedSection) -> list[Connection]:
    return [
        Connection(
            name=connection.attributes.get("Name", ""),
            protocol="EtherNet/IP",
            connection_type=connection.attributes.get("Type"),
            source_extensions=[captured_to_source_extension(connection)],
        )
        for communications in module.elements.get("Communications", [])
        for connections in communications.elements.get("Connections", [])
        for connection in connections.elements.get("Connection", [])
    ]


def _identity(
    section: CapturedSection,
    specs: dict[str, AttributeSpec],
    diagnostics: list[ConversionDiagnostic] | None,
    owner: CapturedSection | None = None,
) -> Identity:
    diagnostic_owner = owner or section
    vendor_id = _optional_int(
        section.attributes.get("Vendor"), "Vendor", diagnostic_owner, diagnostics
    )
    major = _optional_int(
        section.attributes.get("Major"), "Major", diagnostic_owner, diagnostics
    )
    minor = _optional_int(
        section.attributes.get("Minor"), "Minor", diagnostic_owner, diagnostics
    )
    revision = Revision(major, minor) if major is not None and minor is not None else None
    vendor_name = (
        _value_label(specs.get("Vendor"), vendor_id)
        if vendor_id is not None
        else None
    )
    if vendor_id is not None and vendor_name is None:
        _emit(
            diagnostics,
            DiagnosticSeverity.INFO,
            "unknown_vendor",
            f"vendor ID {vendor_id} has no resolved name",
            diagnostic_owner,
            "Vendor",
            str(vendor_id),
        )
    if (major is None) != (minor is None):
        _emit(
            diagnostics,
            DiagnosticSeverity.WARNING,
            "incomplete_revision",
            "identity revision requires both Major and Minor values",
            diagnostic_owner,
        )

    return Identity(
        vendor=(
            VendorIdentity(vendor_id, vendor_name)
            if vendor_id is not None
            else None
        ),
        product_type=_optional_int(
            section.attributes.get("ProductType"),
            "ProductType",
            diagnostic_owner,
            diagnostics,
        ),
        product_code=_optional_int(
            section.attributes.get("ProductCode"),
            "ProductCode",
            diagnostic_owner,
            diagnostics,
        ),
        revision=revision,
    )


def _module_address(module: CapturedSection) -> str | None:
    addressed_ports = [
        port
        for ports in module.elements.get("Ports", [])
        for port in ports.elements.get("Port", [])
        if "Address" in port.attributes
    ]
    upstream = next(
        (
            port
            for port in addressed_ports
            if port.attributes.get("Upstream") == "true"
        ),
        None,
    )
    port = upstream or (addressed_ports[0] if addressed_ports else None)
    return port.attributes["Address"] if port is not None else None


def _numeric_slot(address: str | None) -> int | None:
    if address is None:
        return None
    try:
        return int(address)
    except ValueError:
        return None


def _optional_int(
    value: str | None,
    field: str,
    section: CapturedSection,
    diagnostics: list[ConversionDiagnostic] | None,
) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        _emit(
            diagnostics,
            DiagnosticSeverity.WARNING,
            "invalid_integer",
            f"{field} must be an integer, got {value!r}",
            section,
            field,
            value,
        )
        return None


def _optional_bool(
    value: str | None,
    field: str,
    section: CapturedSection,
    diagnostics: list[ConversionDiagnostic] | None,
) -> bool | None:
    if value == "true":
        return True
    if value == "false":
        return False
    if value is not None:
        _emit(
            diagnostics,
            DiagnosticSeverity.WARNING,
            "invalid_boolean",
            f"{field} must be 'true' or 'false', got {value!r}",
            section,
            field,
            value,
        )
    return None


def _value_label(spec: AttributeSpec | None, value: int) -> str | None:
    if spec is None:
        return None
    for known_value, label in spec.value_labels:
        if known_value == value:
            return label
    return None


def _emit(
    diagnostics: list[ConversionDiagnostic] | None,
    severity: DiagnosticSeverity,
    code: str,
    message: str,
    section: CapturedSection,
    field: str | None = None,
    raw_value: str | None = None,
) -> None:
    if diagnostics is None:
        return
    diagnostics.append(
        ConversionDiagnostic(
            severity=severity,
            code=code,
            message=message,
            object_name=section.attributes.get("Name"),
            field=field,
            raw_value=raw_value,
        )
    )
