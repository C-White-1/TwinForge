"""Correlation of EDS and GSD descriptions into a neutral gateway asset."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from twinforge.converters import ConversionDiagnostic, DiagnosticSeverity
from twinforge.model import (
    CommunicationInterface,
    CommunicationRole,
    Connection,
    GatewayDevice,
)
from twinforge.parsers.eds import EdsDocument
from twinforge.parsers.gsd import GsdDocument


@dataclass(frozen=True)
class GatewayDescriptionAssemblyResult:
    """One assembled gateway plus cross-description diagnostics."""

    gateway: GatewayDevice
    diagnostics: tuple[ConversionDiagnostic, ...] = ()


def assemble_gateway_descriptions(
    eds: EdsDocument,
    gsd: GsdDocument,
    *,
    name: str | None = None,
) -> GatewayDescriptionAssemblyResult:
    """Assemble EDS and GSD evidence without inventing protocol mappings."""

    diagnostics: list[ConversionDiagnostic] = []
    cip_name = eds.identity.product_name
    profibus_name = gsd.identity.model_name
    if (
        cip_name
        and profibus_name
        and cip_name.casefold() != profibus_name.casefold()
    ):
        diagnostics.append(
            ConversionDiagnostic(
                severity=DiagnosticSeverity.WARNING,
                code="gateway_description_model_mismatch",
                message=(
                    f"EDS product {cip_name!r} and GSD model "
                    f"{profibus_name!r} do not match"
                ),
                object_name=name or cip_name,
            )
        )

    gateway = GatewayDevice(
        name=name or cip_name or profibus_name or "Protocol gateway",
        manufacturer=(
            eds.identity.vendor.name
            if eds.identity.vendor is not None
            else gsd.identity.vendor_name
        ),
        model=cip_name or profibus_name,
        identity=deepcopy(eds.identity),
        metadata={
            "description_sources": {
                "EDS": str(eds.source_path),
                "GSD": str(gsd.source_path),
            },
            "protocol_mapping_status": "not_evidenced",
        },
    )

    ethernet_ip = CommunicationInterface(
        name="EtherNet/IP",
        protocol="EtherNet/IP",
        role=CommunicationRole.ADAPTER,
        metadata={
            "source_format": "EDS",
            "assembly_declarations": tuple(
                {
                    "reference": item.reference,
                    "name": item.name,
                    "declared_count": item.declared_count,
                    "parameter_reference": item.parameter_reference,
                }
                for item in eds.assemblies
            ),
        },
    )
    for item in eds.connections:
        ethernet_ip.add_connection(
            Connection(
                name=item.name or item.reference,
                protocol="EtherNet/IP",
                connection_type="Class 1 declaration",
                metadata={
                    "source_reference": item.reference,
                    "originator_to_target": {
                        "assembly_reference": (
                            item.originator_to_target.assembly_reference
                        ),
                        "declared_size": item.originator_to_target.declared_size,
                        "parameter_reference": (
                            item.originator_to_target.parameter_reference
                        ),
                    },
                    "target_to_originator": {
                        "assembly_reference": (
                            item.target_to_originator.assembly_reference
                        ),
                        "declared_size": item.target_to_originator.declared_size,
                        "parameter_reference": (
                            item.target_to_originator.parameter_reference
                        ),
                    },
                    "path_text": item.path_text,
                    "configured_size_status": "not_evidenced",
                },
            )
        )
    gateway.add_communication_interface(ethernet_ip)

    profibus = CommunicationInterface(
        name="PROFIBUS DP",
        protocol="PROFIBUS DP",
        role=(
            CommunicationRole.SLAVE
            if gsd.identity.station_type == 0
            else CommunicationRole.UNKNOWN
        ),
        metadata={
            "source_format": "GSD",
            "ident_number": gsd.identity.ident_number,
            "station_type": gsd.identity.station_type,
            "limits": {
                "max_modules": gsd.limits.max_modules,
                "max_input_length": gsd.limits.max_input_length,
                "max_output_length": gsd.limits.max_output_length,
                "max_data_length": gsd.limits.max_data_length,
            },
            "selectable_modules": tuple(
                {
                    "name": module.name,
                    "identifiers": tuple(
                        item.identifier for item in module.configuration
                    ),
                }
                for module in gsd.modules
            ),
        },
    )
    gateway.add_communication_interface(profibus)

    return GatewayDescriptionAssemblyResult(
        gateway=gateway,
        diagnostics=tuple(diagnostics),
    )
