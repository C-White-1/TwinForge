"""Correlate native PLX50 configuration with generated Logix mapping logic."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from twinforge.analysis import extract_program_calls
from twinforge.converters import ConversionDiagnostic, DiagnosticSeverity
from twinforge.model import (
    Controller,
    Datatype,
    GatewayDevice,
    GatewayProtocolMapping,
    GatewayTagBinding,
    GatewayTagBindingRole,
    SourceExtension,
    Tag,
)
from twinforge.parsers.plx50 import Plx50DeviceConfiguration


_ASSEMBLY_OPERAND = re.compile(
    r"(?P<module>[A-Za-z_][A-Za-z0-9_]*):"
    r"(?P<direction>[IO])(?P<connection>\d+)\.Data"
    r"(?:\[(?P<offset>\d+)\])?"
)


@dataclass(frozen=True)
class Plx50LogixTransfer:
    """One generated CPS transfer between a module assembly and a tag."""

    module_name: str
    direction: str
    connection_number: int
    assembly_offset: int
    copy_length: int
    controller_tag: str
    source_text: str

    @property
    def assembly_reference(self) -> str:
        """Return the exact Logix module-side operand."""

        return (
            f"{self.module_name}:{self.direction}{self.connection_number}"
            f".Data[{self.assembly_offset}]"
        )


@dataclass(frozen=True)
class Plx50LogixPointCorrelation:
    """One PROFIBUS point tied to generated Logix tag and assembly evidence."""

    station_address: int
    slot_id: int
    point_type: str
    point_name: str
    data_type: str | None
    byte_length: int | None
    profibus_reference: str
    controller_tag_path: str
    assembly_reference: str
    copy_length: int
    evidence: tuple[str, ...]
    source_extensions: tuple[SourceExtension, ...] = ()


@dataclass(frozen=True)
class Plx50LogixMappingResult:
    """Applied mappings plus unresolved source evidence and diagnostics."""

    transfers: tuple[Plx50LogixTransfer, ...]
    correlations: tuple[Plx50LogixPointCorrelation, ...]
    unresolved_points: tuple[str, ...]
    diagnostics: tuple[ConversionDiagnostic, ...]


def plx50_logix_mapping_data(
    result: Plx50LogixMappingResult,
) -> dict[str, Any]:
    """Return a deterministic, JSON-compatible correlation contract."""

    return {
        "schema_version": "1.0",
        "transfers": [
            {
                "module_name": item.module_name,
                "direction": item.direction,
                "connection_number": item.connection_number,
                "assembly_offset": item.assembly_offset,
                "assembly_reference": item.assembly_reference,
                "copy_length": item.copy_length,
                "controller_tag": item.controller_tag,
                "source_text": item.source_text,
            }
            for item in result.transfers
        ],
        "correlations": [
            {
                "station_address": item.station_address,
                "slot_id": item.slot_id,
                "point_type": item.point_type,
                "point_name": item.point_name,
                "data_type": item.data_type,
                "byte_length": item.byte_length,
                "profibus_reference": item.profibus_reference,
                "controller_tag_path": item.controller_tag_path,
                "assembly_reference": item.assembly_reference,
                "copy_length": item.copy_length,
                "evidence": list(item.evidence),
            }
            for item in result.correlations
        ],
        "unresolved_points": list(result.unresolved_points),
        "diagnostics": [
            {
                "severity": item.severity.value,
                "code": item.code,
                "message": item.message,
                "object_name": item.object_name,
                "field": item.field,
                "raw_value": item.raw_value,
            }
            for item in result.diagnostics
        ],
    }


def plx50_logix_mapping_json(result: Plx50LogixMappingResult) -> str:
    """Serialize the stable correlation contract with a final newline."""

    return json.dumps(
        plx50_logix_mapping_data(result),
        indent=2,
        ensure_ascii=False,
    ) + "\n"


def apply_plx50_logix_mapping(
    gateway: GatewayDevice,
    configuration: Plx50DeviceConfiguration,
    controller: Controller,
) -> Plx50LogixMappingResult:
    """Apply only PSJ points corroborated by generated MOV and CPS evidence."""

    diagnostics: list[ConversionDiagnostic] = []
    transfers, station_tags = _generated_evidence(
        controller,
        configuration.instance_name,
        diagnostics,
    )
    correlations: list[Plx50LogixPointCorrelation] = []
    unresolved: list[str] = []
    for device in configuration.profibus_devices:
        station = device.station_address
        for slot in device.slots:
            for point in slot.data_points:
                point_name = point.description
                point_type = point.data_point_type
                reference = _profibus_reference(
                    station,
                    slot.slot_id,
                    point_type,
                    point.local_offset,
                )
                if station is None or slot.slot_id is None:
                    unresolved.append(reference)
                    diagnostics.append(
                        _warning(
                            "plx50_logix_profibus_location_unresolved",
                            f"{reference} has no complete station/slot location",
                            point.description,
                        )
                    )
                    continue
                if not point_name or point_type not in ("Input", "Output"):
                    unresolved.append(reference)
                    continue
                candidates = _point_candidates(
                    controller,
                    station_tags.get(station, ()),
                    transfers,
                    point_type,
                    point_name,
                )
                if len(candidates) != 1:
                    unresolved.append(reference)
                    diagnostics.append(
                        _warning(
                            "plx50_logix_point_mapping_unresolved",
                            (
                                f"{reference} resolved to {len(candidates)} "
                                "generated Logix mapping candidates"
                            ),
                            point_name,
                        )
                    )
                    continue
                tag, transfer = candidates[0]
                tag_path = f"{transfer.controller_tag}.{point_name}"
                evidence = (
                    f"generated station assignment for station {station}",
                    transfer.source_text,
                )
                correlation = Plx50LogixPointCorrelation(
                    station_address=station,
                    slot_id=slot.slot_id,
                    point_type=point_type,
                    point_name=point_name,
                    data_type=point.data_format,
                    byte_length=point.byte_length,
                    profibus_reference=reference,
                    controller_tag_path=tag_path,
                    assembly_reference=transfer.assembly_reference,
                    copy_length=transfer.copy_length,
                    evidence=evidence,
                    source_extensions=(
                        point.source_extension,
                        *tag.source_extensions,
                    ),
                )
                correlations.append(correlation)
                gateway.add_protocol_mapping(_gateway_mapping(correlation))
                gateway.add_tag_binding(
                    _gateway_tag_binding(correlation, tag)
                )

    if correlations:
        gateway.metadata["protocol_mapping_status"] = "partially_evidenced"
    return Plx50LogixMappingResult(
        transfers=transfers,
        correlations=tuple(correlations),
        unresolved_points=tuple(unresolved),
        diagnostics=tuple(diagnostics),
    )


def _generated_evidence(
    controller: Controller,
    module_name: str | None,
    diagnostics: list[ConversionDiagnostic],
) -> tuple[tuple[Plx50LogixTransfer, ...], dict[int, tuple[str, ...]]]:
    transfers: list[Plx50LogixTransfer] = []
    station_tags: dict[int, list[str]] = {}
    for program in controller.iter_programs():
        for call in extract_program_calls(program):
            operands = tuple(item.source.strip() for item in call.arguments)
            mnemonic = call.callee.upper()
            if mnemonic == "MOV" and len(operands) == 2:
                station = _integer(operands[0])
                suffix = ".Output.Control.StationNumber"
                if station is not None and operands[1].endswith(suffix):
                    station_tags.setdefault(station, []).append(
                        operands[1][: -len(suffix)]
                    )
            elif mnemonic == "CPS" and len(operands) == 3:
                transfer = _cps_transfer(operands, call.source_text)
                if transfer is not None and (
                    module_name is None or transfer.module_name == module_name
                ):
                    transfers.append(transfer)
    if module_name and not transfers:
        diagnostics.append(
            _warning(
                "plx50_logix_module_transfer_unresolved",
                f"no generated CPS transfers reference module {module_name!r}",
                module_name,
            )
        )
    return (
        tuple(transfers),
        {
            station: tuple(dict.fromkeys(tags))
            for station, tags in station_tags.items()
        },
    )


def _cps_transfer(
    operands: tuple[str, ...],
    source_text: str,
) -> Plx50LogixTransfer | None:
    first = _assembly_match(operands[0])
    second = _assembly_match(operands[1])
    length = _integer(operands[2])
    if length is None or length < 1:
        return None
    if first is not None and first.group("direction") == "I":
        match = first
        tag = operands[1]
    elif second is not None and second.group("direction") == "O":
        match = second
        tag = operands[0]
    else:
        return None
    return Plx50LogixTransfer(
        module_name=match.group("module"),
        direction=match.group("direction"),
        connection_number=int(match.group("connection")),
        assembly_offset=int(match.group("offset") or "0"),
        copy_length=length,
        controller_tag=tag,
        source_text=source_text,
    )


def _assembly_match(value: str) -> re.Match[str] | None:
    return _ASSEMBLY_OPERAND.fullmatch(value)


def _point_candidates(
    controller: Controller,
    base_tags: tuple[str, ...],
    transfers: tuple[Plx50LogixTransfer, ...],
    point_type: str,
    point_name: str,
) -> list[tuple[Tag, Plx50LogixTransfer]]:
    candidates: list[tuple[Tag, Plx50LogixTransfer]] = []
    for base in base_tags:
        tag = controller.get_tag(base)
        if tag is None or not _has_member(tag.data_type_definition, point_type, point_name):
            continue
        expected = f"{base}.{point_type}"
        candidates.extend(
            (tag, transfer)
            for transfer in transfers
            if transfer.controller_tag == expected
        )
    return candidates


def _has_member(
    data_type: Datatype | None,
    container_name: str,
    member_name: str,
) -> bool:
    if data_type is None:
        return False
    container = next(
        (item for item in data_type.members if item.name == container_name),
        None,
    )
    return bool(
        container is not None
        and container.data_type is not None
        and any(item.name == member_name for item in container.data_type.members)
    )


def _gateway_mapping(
    item: Plx50LogixPointCorrelation,
) -> GatewayProtocolMapping:
    logix_reference = (
        f"{item.assembly_reference} via {item.controller_tag_path}"
    )
    if item.point_type == "Input":
        source_interface, source_reference = "PROFIBUS DP", item.profibus_reference
        target_interface, target_reference = "EtherNet/IP", logix_reference
    else:
        source_interface, source_reference = "EtherNet/IP", logix_reference
        target_interface, target_reference = "PROFIBUS DP", item.profibus_reference
    return GatewayProtocolMapping(
        source_interface=source_interface,
        source_reference=source_reference,
        target_interface=target_interface,
        target_reference=target_reference,
        evidence="PLX50 PSJ point plus generated Logix MOV/CPS mapping",
        metadata={
            "profibus_station": item.station_address,
            "profibus_slot": item.slot_id,
            "data_point": item.point_name,
            "controller_tag_path": item.controller_tag_path,
            "assembly_reference": item.assembly_reference,
            "copy_length": item.copy_length,
        },
        source_extensions=item.source_extensions,
    )


def _gateway_tag_binding(
    item: Plx50LogixPointCorrelation,
    tag: Tag,
) -> GatewayTagBinding:
    """Create the neutral tag link corroborated by MOV/CPS evidence."""

    role = (
        GatewayTagBindingRole.TARGET
        if item.point_type == "Input"
        else GatewayTagBindingRole.SOURCE
    )
    return GatewayTagBinding(
        interface_name="EtherNet/IP",
        endpoint_reference=item.assembly_reference,
        tag=tag,
        tag_path=item.controller_tag_path,
        role=role,
        evidence="PLX50 generated Logix MOV/CPS mapping",
        source_extensions=item.source_extensions,
    )


def _profibus_reference(
    station: int | None,
    slot: int | None,
    point_type: str | None,
    local_offset: int | None,
) -> str:
    return (
        f"station {station}/slot {slot}/{point_type or 'data'} "
        f"offset {local_offset}"
    )


def _integer(value: str) -> int | None:
    try:
        return int(value, 0)
    except ValueError:
        return None


def _warning(
    code: str,
    message: str,
    raw_value: str | None,
) -> ConversionDiagnostic:
    return ConversionDiagnostic(
        severity=DiagnosticSeverity.WARNING,
        code=code,
        message=message,
        object_name="PLX50 Logix mapping",
        raw_value=raw_value,
    )
