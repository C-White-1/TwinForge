"""Derive conservative CIP infrastructure candidates from EDS paths."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from twinforge.discovery import (
    CipInfrastructureObject,
    CipInfrastructureReadRequest,
    CipMetadataReadService,
)
from twinforge.parsers.eds import EdsDocument


class EdsLogicalSegmentType(str, Enum):
    """Logical EPATH segment types used by EDS connection declarations."""

    CLASS = "class"
    INSTANCE = "instance"
    CONNECTION_POINT = "connection_point"


@dataclass(frozen=True)
class EdsLogicalPathSegment:
    """One decoded logical segment with its original encoded bytes."""

    segment_type: EdsLogicalSegmentType
    value: int
    offset: int
    encoded_hex: str


@dataclass(frozen=True)
class EdsCipInfrastructureCandidate:
    """One exact Assembly read candidate supported by an EDS connection path."""

    request: CipInfrastructureReadRequest
    connection_reference: str
    path_position: int
    segment_type: EdsLogicalSegmentType
    endpoint_reference: str | None = None
    declared_size: int | None = None


@dataclass(frozen=True)
class EdsCipInfrastructureDiagnostic:
    """Evidence that could not safely become an infrastructure request."""

    connection_reference: str
    code: str
    message: str
    path_hex: str | None = None


@dataclass(frozen=True)
class EdsCipInfrastructureAssessment:
    """Decoded EDS paths, request candidates, and retained ambiguity."""

    source_path: str
    segments: tuple[tuple[str, tuple[EdsLogicalPathSegment, ...]], ...]
    candidates: tuple[EdsCipInfrastructureCandidate, ...]
    diagnostics: tuple[EdsCipInfrastructureDiagnostic, ...]


def assess_eds_cip_infrastructure(
    document: EdsDocument,
) -> EdsCipInfrastructureAssessment:
    """Extract exact Assembly instances without inferring payload layouts."""
    all_segments: list[tuple[str, tuple[EdsLogicalPathSegment, ...]]] = []
    candidates: list[EdsCipInfrastructureCandidate] = []
    diagnostics: list[EdsCipInfrastructureDiagnostic] = []
    for connection in document.connections:
        if connection.path is None:
            diagnostics.append(
                EdsCipInfrastructureDiagnostic(
                    connection_reference=connection.reference,
                    code="eds_connection_path_unavailable",
                    message="connection has no decodable hexadecimal path",
                    path_hex=connection.path_text,
                )
            )
            continue
        try:
            segments = decode_eds_logical_path(bytes(connection.path))
        except ValueError as error:
            diagnostics.append(
                EdsCipInfrastructureDiagnostic(
                    connection_reference=connection.reference,
                    code="eds_connection_path_unsupported",
                    message=str(error),
                    path_hex=bytes(connection.path).hex(),
                )
            )
            continue
        all_segments.append((connection.reference, segments))
        classes = [
            item
            for item in segments
            if item.segment_type is EdsLogicalSegmentType.CLASS
        ]
        if len(classes) != 1 or classes[0].value != 4:
            diagnostics.append(
                EdsCipInfrastructureDiagnostic(
                    connection_reference=connection.reference,
                    code="eds_connection_path_not_assembly",
                    message="path does not contain exactly one Assembly class segment",
                    path_hex=bytes(connection.path).hex(),
                )
            )
            continue
        instance_segments = tuple(
            item
            for item in segments
            if item.segment_type
            in {
                EdsLogicalSegmentType.INSTANCE,
                EdsLogicalSegmentType.CONNECTION_POINT,
            }
        )
        endpoints = (
            (
                connection.target_config_reference,
                connection.target_config_size,
            ),
            (
                connection.originator_to_target.assembly_reference,
                connection.originator_to_target.declared_size,
            ),
            (
                connection.target_to_originator.assembly_reference,
                connection.target_to_originator.declared_size,
            ),
        )
        for position, segment in enumerate(instance_segments):
            endpoint_reference, declared_size = (
                endpoints[position] if position < len(endpoints) else (None, None)
            )
            candidates.append(
                EdsCipInfrastructureCandidate(
                    request=CipInfrastructureReadRequest(
                        object_type=CipInfrastructureObject.ASSEMBLY,
                        instance=segment.value,
                        attribute=3,
                        service=CipMetadataReadService.GET_ATTRIBUTE_SINGLE,
                        specification_reference=(
                            f"EDS {document.source_path}; "
                            f"{connection.reference} path segment {position + 1}"
                        ),
                        purpose="read EDS-declared Assembly instance data",
                    ),
                    connection_reference=connection.reference,
                    path_position=position,
                    segment_type=segment.segment_type,
                    endpoint_reference=endpoint_reference,
                    declared_size=declared_size,
                )
            )
    return EdsCipInfrastructureAssessment(
        source_path=str(document.source_path),
        segments=tuple(all_segments),
        candidates=tuple(candidates),
        diagnostics=tuple(diagnostics),
    )


def decode_eds_logical_path(path: bytes) -> tuple[EdsLogicalPathSegment, ...]:
    """Decode supported 8- and 16-bit logical EPATH segments losslessly."""
    segments: list[EdsLogicalPathSegment] = []
    offset = 0
    types = {
        0x20: (EdsLogicalSegmentType.CLASS, 1, 0),
        0x21: (EdsLogicalSegmentType.CLASS, 2, 1),
        0x24: (EdsLogicalSegmentType.INSTANCE, 1, 0),
        0x25: (EdsLogicalSegmentType.INSTANCE, 2, 1),
        0x2C: (EdsLogicalSegmentType.CONNECTION_POINT, 1, 0),
        0x2D: (EdsLogicalSegmentType.CONNECTION_POINT, 2, 1),
    }
    while offset < len(path):
        start = offset
        code = path[offset]
        definition = types.get(code)
        if definition is None:
            raise ValueError(
                f"unsupported logical path segment 0x{code:02X} at byte {offset}"
            )
        segment_type, width, pad = definition
        value_start = offset + 1 + pad
        end = value_start + width
        if end > len(path):
            raise ValueError(
                f"truncated logical path segment 0x{code:02X} at byte {offset}"
            )
        encoded = path[start:end]
        segments.append(
            EdsLogicalPathSegment(
                segment_type=segment_type,
                value=int.from_bytes(path[value_start:end], "little"),
                offset=start,
                encoded_hex=encoded.hex(),
            )
        )
        offset = end
    return tuple(segments)
