"""Orchestrate conversion of captured L5X modules into domain modules.

Detailed identity, engineering-metadata, and vendor capability rules live in
focused collaborators. This module owns only assembly, addressing, flags, and
connection relationships.
"""

from __future__ import annotations

from collections.abc import Sequence

from twinforge.converters.diagnostics import ConversionDiagnostic
from twinforge.model import Connection
from twinforge.model.module import Module
from twinforge.parsers.l5x.capture import CapturedSection
from twinforge.schema.l5x.modules import MODULE_ATTRIBUTES

from .conversion_value import optional_bool, optional_int
from .module_capability import (
    DEFAULT_CAPABILITY_PROVIDERS,
    ModuleCapabilityProvider,
    infer_module_capability,
)
from .module_engineering import (
    extract_engineering_ranges,
    extract_engineering_units,
)
from .module_identity import convert_electronic_key, convert_identity
from .source_extension import captured_to_source_extension


def convert_module(
    section: CapturedSection,
    *,
    slot: int | None = None,
    diagnostics: list[ConversionDiagnostic] | None = None,
    capability_providers: Sequence[
        ModuleCapabilityProvider
    ] = DEFAULT_CAPABILITY_PROVIDERS,
) -> Module:
    """Convert one captured L5X ``Module`` into a lossless domain module.

    ``capability_providers`` is injectable so vendor- or profile-specific
    knowledge can extend conversion without changing this orchestrator.
    Providers may infer additional facts, but captured source data is always
    retained independently in source extensions.
    """

    if section.tag != "Module":
        raise ValueError(f"expected a Module section, got {section.tag!r}")

    address = _module_address(section)
    resolved_slot = _numeric_slot(address) if slot is None else slot
    identity = convert_identity(section, MODULE_ATTRIBUTES, diagnostics)
    identity.source_extensions.append(captured_to_source_extension(section))
    engineering_units = extract_engineering_units(
        section, resolved_slot, diagnostics
    )
    engineering_ranges = extract_engineering_ranges(section, resolved_slot)

    module = Module(
        name=section.attributes.get("Name", ""),
        slot=resolved_slot,
        address=address,
        catalog=section.attributes.get("CatalogNumber", ""),
        identity=identity,
        electronic_key=convert_electronic_key(section, diagnostics),
        inhibited=optional_bool(
            section.attributes.get("Inhibited"),
            "Inhibited",
            section,
            diagnostics,
        ),
        major_fault_on_connection_loss=optional_bool(
            section.attributes.get("MajorFault"),
            "MajorFault",
            section,
            diagnostics,
        ),
        engineering_units=engineering_units,
        engineering_ranges=engineering_ranges,
        capability=infer_module_capability(
            section,
            identity,
            engineering_ranges,
            capability_providers,
        ),
        source_extensions=[captured_to_source_extension(section)],
    )
    for connection in _convert_connections(section, diagnostics):
        module.add_connection(connection)
    return module


def _convert_connections(
    module: CapturedSection,
    diagnostics: list[ConversionDiagnostic] | None,
) -> list[Connection]:
    """Convert captured connection records and retain their source XML."""

    return [
        Connection(
            name=connection.attributes.get("Name", ""),
            protocol="EtherNet/IP",
            connection_type=connection.attributes.get("Type"),
            requested_packet_interval_microseconds=optional_int(
                connection.attributes.get("RPI"),
                "RPI",
                connection,
                diagnostics,
            ),
            input_connection_point=optional_int(
                connection.attributes.get("InputCxnPoint"),
                "InputCxnPoint",
                connection,
                diagnostics,
            ),
            output_connection_point=optional_int(
                connection.attributes.get("OutputCxnPoint"),
                "OutputCxnPoint",
                connection,
                diagnostics,
            ),
            input_size_bytes=optional_int(
                connection.attributes.get("InputSize"),
                "InputSize",
                connection,
                diagnostics,
            ),
            output_size_bytes=optional_int(
                connection.attributes.get("OutputSize"),
                "OutputSize",
                connection,
                diagnostics,
            ),
            unicast=optional_bool(
                connection.attributes.get("Unicast"),
                "Unicast",
                connection,
                diagnostics,
            ),
            source_extensions=[captured_to_source_extension(connection)],
        )
        for communications in module.elements.get("Communications", [])
        for connections in communications.elements.get("Connections", [])
        for connection in connections.elements.get("Connection", [])
    ]


def _module_address(module: CapturedSection) -> str | None:
    """Prefer the upstream port address while preserving non-slot addresses."""

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
    """Interpret an address as a slot only when it is a decimal integer."""

    if address is None:
        return None
    try:
        return int(address)
    except ValueError:
        return None
