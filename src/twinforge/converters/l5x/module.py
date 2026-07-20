from __future__ import annotations

from twinforge.converters.diagnostics import (
    ConversionDiagnostic,
    DiagnosticSeverity,
)
from twinforge.model import (
    Connection,
    ElectronicKey,
    Identity,
    KeyingMode,
    Module,
    Revision,
    VendorIdentity,
)
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
        source_extensions=[captured_to_source_extension(section)],
    )
    for connection in _connections(section):
        module.add_connection(connection)
    return module


def _electronic_key(
    module: CapturedSection,
    diagnostics: list[ConversionDiagnostic] | None,
) -> ElectronicKey | None:
    sections = module.elements.get("EKey", [])
    if not sections:
        return None

    section = sections[0]
    state = section.attributes.get("State")
    mode = _KEYING_MODES.get(state)
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
