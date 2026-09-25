"""Read-only inspection summaries for SCADAPack `.RCZ`/`.STA` exports.

Scope matches docs/roadmaps/scadapack-rcz-capture-roadmap.md: plain-XML
`STSource` routines and `.prj` DTM/protocol configuration only. FBD
content, the binary-framed older-version `STSource` shape, and the DTM
parent/child tree remain unresolved -- reported as diagnostics, not
guessed at.
"""
from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, TextIO

from twinforge.model import ConfiguredProtocolAddress, DeviceTypeManager, ProtocolVariant, Routine
from twinforge.parsers.scadapack import capture_file, parse_station


class ScadaPackCommandError(RuntimeError):
    """Inspection failed or could not fully read its input."""


def _routine_summary(routine: Routine) -> dict[str, Any]:
    return {
        "name": routine.name, "language": routine.language,
        "structured_text_line_count": len(routine.structured_text_lines),
        "structured_text": routine.structured_text,
    }


def _protocol_variant_summary(variant: ProtocolVariant) -> dict[str, Any]:
    return {"protocol_id": variant.protocol_id, "protocol_name": variant.protocol_name}


def _configured_protocol_summary(address: ConfiguredProtocolAddress) -> dict[str, Any]:
    return {
        "protocol_id": address.protocol_id, "protocol_name": address.protocol_name,
        "active": address.active, "addressing_mode": address.addressing_mode,
        "target_address": address.target_address, "ip_address": address.ip_address,
        "port": address.port, "device_serial_number": address.device_serial_number,
        "local_connection": address.local_connection,
    }


def _device_type_manager_summary(manager: DeviceTypeManager) -> dict[str, Any]:
    return {
        "id": manager.id, "name": manager.name,
        "product_name": manager.product_name, "product_manufacturer": manager.product_manufacturer,
        "supported_protocols": [_protocol_variant_summary(v) for v in manager.supported_protocols],
        "configured_protocols": [_configured_protocol_summary(c) for c in manager.configured_protocols],
    }


def inspect_scadapack(path: Path, *, output_format: str, stdout: TextIO) -> None:
    """Print deterministic inspection evidence; partial reads have a failure exit."""
    try:
        captured = capture_file(path)
    except OSError as error:
        raise ScadaPackCommandError(f"could not inspect SCADAPack input '{path}': {error}") from error
    result = parse_station(captured)
    has_content = bool(result.station_properties or result.routines or result.device_type_managers)
    status = "inspected" if has_content else "no_supported_content"
    report: dict[str, Any] = {
        "report_version": "1.0", "report_type": "scadapack_inspection",
        "input": {"name": path.name, "sha256": captured.sha256},
        "status": status,
        "native_validation": "not_performed",
        "station_properties": result.station_properties,
        "routines": [_routine_summary(r) for r in result.routines],
        "device_type_managers": [_device_type_manager_summary(m) for m in result.device_type_managers],
        "diagnostics": [asdict(d) for d in result.diagnostics],
    }
    if output_format == "json":
        stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    else:
        stdout.write(f"SCADAPack inspection: {path.name}\n"
                     f"SHA-256: {captured.sha256}\n"
                     f"Status: {status}\n"
                     "Native validation: not performed\n")
        if result.station_properties:
            stdout.write(f"\nRTU model: {result.station_properties.get('PROCESSOR', '(unknown)')}\n"
                         f"  Application LIBSET: {result.station_properties.get('APPLICATION LIBSET', '(unknown)')}\n"
                         f"  STU compatibility level: {result.station_properties.get('STU COMPATIBILITY LEVEL', '(unknown)')}\n"
                         f"  PLC address: {result.station_properties.get('PLC ADDRESS', '(unknown)')} "
                         f"({result.station_properties.get('PLC MEDIA', '(unknown)')})\n")
        stdout.write(f"\nRoutines: {len(result.routines)} (plain-XML STSource only; "
                     "older binary-framed sources are diagnosed, not parsed)\n")
        for routine in report["routines"]:
            stdout.write(f"  {routine['name']}: {routine['structured_text_line_count']} lines\n")
        stdout.write(f"\nDevice Type Managers: {len(result.device_type_managers)}\n")
        for manager in report["device_type_managers"]:
            stdout.write(f"  {manager['name']} ({manager['product_name'] or '(unknown product)'})\n")
            if manager["supported_protocols"]:
                names = ", ".join(v["protocol_name"] for v in manager["supported_protocols"])
                stdout.write(f"    Catalog: {names}\n")
            for protocol in manager["configured_protocols"]:
                marker = "active" if protocol["active"] else "configured"
                address = protocol["ip_address"] or protocol["target_address"] or "(no address)"
                stdout.write(f"    {protocol['protocol_name'] or protocol['protocol_id']} [{marker}]: "
                             f"{protocol['addressing_mode']} -> {address}"
                             + (f":{protocol['port']}" if protocol["port"] else "") + "\n")
        if result.diagnostics:
            stdout.write(f"\nDiagnostics: {len(result.diagnostics)}\n")
            for diagnostic in result.diagnostics:
                stdout.write(f"  {diagnostic.code}: {diagnostic.message}\n")
    if not has_content:
        raise ScadaPackCommandError(
            f"no supported SCADAPack content found in '{path}' "
            "(no STATION.CTX, no plain-XML STSource, no .prj DTM data)"
        )
