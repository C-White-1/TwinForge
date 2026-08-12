"""Application of explicit mapping-report evidence to neutral gateways."""

from __future__ import annotations

from dataclasses import dataclass

from twinforge.converters import ConversionDiagnostic, DiagnosticSeverity
from twinforge.model import GatewayDevice, GatewayProtocolMapping
from twinforge.parsers.gateway_mapping_csv import GatewayMappingCSVDocument


@dataclass(frozen=True)
class GatewayMappingApplicationResult:
    """Mappings applied to a gateway and rows that remain unresolved."""

    applied: tuple[GatewayProtocolMapping, ...]
    unresolved_rows: tuple[int, ...]
    diagnostics: tuple[ConversionDiagnostic, ...]


def apply_gateway_mapping_document(
    gateway: GatewayDevice,
    document: GatewayMappingCSVDocument,
) -> GatewayMappingApplicationResult:
    """Apply only valid, explicitly evidenced rows to an existing gateway."""

    applied: list[GatewayProtocolMapping] = []
    unresolved: list[int] = []
    diagnostics = list(document.diagnostics)
    interface_names = {
        interface.name for interface in gateway.communication_interfaces
    }
    for record in document.records:
        if not record.promotable:
            unresolved.append(record.row_number)
            continue
        assert record.source_interface is not None
        assert record.target_interface is not None
        assert record.evidence is not None
        missing = tuple(
            name
            for name in (record.source_interface, record.target_interface)
            if name not in interface_names
        )
        if missing:
            unresolved.append(record.row_number)
            diagnostics.append(
                ConversionDiagnostic(
                    severity=DiagnosticSeverity.WARNING,
                    code="gateway_mapping_interface_unresolved",
                    message=(
                        f"gateway mapping CSV row {record.row_number} references "
                        f"unknown interfaces: {', '.join(missing)}"
                    ),
                    object_name=record.mapping_id,
                    raw_value=",".join(missing),
                )
            )
            continue
        mapping = GatewayProtocolMapping(
            source_interface=record.source_interface,
            target_interface=record.target_interface,
            source_reference=record.source_reference,
            target_reference=record.target_reference,
            evidence=record.evidence,
            metadata={
                "mapping_id": record.mapping_id,
                "source_document": str(document.source_path),
                "source_row": record.row_number,
                **record.metadata,
            },
        )
        gateway.add_protocol_mapping(mapping)
        applied.append(mapping)
    if applied:
        gateway.metadata["protocol_mapping_status"] = "partially_evidenced"
    return GatewayMappingApplicationResult(
        applied=tuple(applied),
        unresolved_rows=tuple(unresolved),
        diagnostics=tuple(diagnostics),
    )
