"""Profile-driven decoding of retained CIP infrastructure payloads."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Literal

from .cip_infrastructure_capture import CipInfrastructureCapture
from .cip_infrastructure_plan import (
    CipInfrastructureObject,
    CipInfrastructureReadRequest,
)
from .controller import CipObjectEvidence, JsonEvidence
from .controller_metadata import CipMetadataReadService


class CipBinaryFieldType(str, Enum):
    """Explicit primitive representations accepted in a decode profile."""

    UNSIGNED_INTEGER = "unsigned_integer"
    SIGNED_INTEGER = "signed_integer"
    BYTES = "bytes"


@dataclass(frozen=True)
class CipBinaryField:
    """One cited field occupying an exact byte interval."""

    name: str
    offset: int
    width: int
    field_type: CipBinaryFieldType
    specification_reference: str
    byte_order: Literal["little", "big"] = "little"

    def __post_init__(self) -> None:
        if not self.name or self.name != self.name.strip():
            raise ValueError("binary field name must be non-empty and trimmed")
        if isinstance(self.offset, bool) or self.offset < 0:
            raise ValueError("binary field offset must be non-negative")
        if isinstance(self.width, bool) or self.width <= 0:
            raise ValueError("binary field width must be positive")
        if (
            not self.specification_reference
            or self.specification_reference != self.specification_reference.strip()
        ):
            raise ValueError(
                "binary field specification_reference must be non-empty and trimmed"
            )
        if self.byte_order not in {"little", "big"}:
            raise ValueError("binary field byte_order must be little or big")


@dataclass(frozen=True)
class CipInfrastructureDecodeProfile:
    """Exact request identity and cited payload layout for one response."""

    name: str
    object_type: CipInfrastructureObject
    instance: int
    service: CipMetadataReadService
    specification_reference: str
    fields: tuple[CipBinaryField, ...]
    attribute: int | None = None
    expected_payload_size: int | None = None

    def __post_init__(self) -> None:
        if not self.name or self.name != self.name.strip():
            raise ValueError("decode profile name must be non-empty and trimmed")
        if (
            not self.specification_reference
            or self.specification_reference != self.specification_reference.strip()
        ):
            raise ValueError(
                "profile specification_reference must be non-empty and trimmed"
            )
        if not self.fields:
            raise ValueError("decode profile requires at least one field")
        request = self.request
        del request
        names = tuple(field.name for field in self.fields)
        if len(names) != len(set(names)):
            raise ValueError("decode profile field names must be unique")
        occupied: set[int] = set()
        for field in self.fields:
            positions = set(range(field.offset, field.offset + field.width))
            if occupied.intersection(positions):
                raise ValueError("decode profile fields must not overlap")
            occupied.update(positions)
        if self.expected_payload_size is not None:
            if (
                isinstance(self.expected_payload_size, bool)
                or self.expected_payload_size <= 0
            ):
                raise ValueError("expected_payload_size must be positive")
            if occupied and max(occupied) >= self.expected_payload_size:
                raise ValueError("decode profile field exceeds expected payload size")

    @property
    def request(self) -> CipInfrastructureReadRequest:
        """Materialize the exact request identity represented by this profile."""
        return CipInfrastructureReadRequest(
            object_type=self.object_type,
            instance=self.instance,
            attribute=self.attribute,
            service=self.service,
            specification_reference=self.specification_reference,
        )


def decode_cip_infrastructure_capture(
    capture: CipInfrastructureCapture,
    profiles: tuple[CipInfrastructureDecodeProfile, ...],
) -> CipInfrastructureCapture:
    """Decode exact successful matches while retaining all original bytes."""
    by_key = {profile.request.key: profile for profile in profiles}
    if len(by_key) != len(profiles):
        raise ValueError("decode profiles must target unique request identities")
    planned_keys = {request.key for request in capture.plan.requests}
    unknown = sorted(set(by_key).difference(planned_keys))
    if unknown:
        raise ValueError("decode profile does not match a planned request: " + unknown[0])

    evidence = tuple(
        _decode_evidence(item, by_key.get(_evidence_key(item)))
        for item in capture.object_evidence
    )
    return replace(capture, object_evidence=evidence)


def _decode_evidence(
    evidence: CipObjectEvidence,
    profile: CipInfrastructureDecodeProfile | None,
) -> CipObjectEvidence:
    if profile is None or evidence.general_status != 0:
        return evidence
    payload = bytes.fromhex(evidence.response_payload_hex or "")
    if (
        profile.expected_payload_size is not None
        and len(payload) != profile.expected_payload_size
    ):
        raise ValueError(
            f"payload size {len(payload)} does not match profile "
            f"{profile.name!r} size {profile.expected_payload_size}"
        )
    decoded_fields: dict[str, JsonEvidence] = {}
    claimed: set[int] = set()
    for field in profile.fields:
        end = field.offset + field.width
        if end > len(payload):
            raise ValueError(
                f"field {field.name!r} exceeds payload size {len(payload)}"
            )
        raw = payload[field.offset:end]
        claimed.update(range(field.offset, end))
        if field.field_type is CipBinaryFieldType.BYTES:
            value: JsonEvidence = raw.hex()
        else:
            value = int.from_bytes(
                raw,
                byteorder=field.byte_order,
                signed=(field.field_type is CipBinaryFieldType.SIGNED_INTEGER),
            )
        decoded_fields[field.name] = {
            "value": value,
            "offset": field.offset,
            "width": field.width,
            "field_type": field.field_type.value,
            "byte_order": field.byte_order,
            "specification_reference": field.specification_reference,
        }
    unclaimed = bytes(
        value for index, value in enumerate(payload) if index not in claimed
    )
    decoded: dict[str, JsonEvidence] = {
        "profile_name": profile.name,
        "specification_reference": profile.specification_reference,
        "fields": decoded_fields,
        "unclaimed_payload_hex": unclaimed.hex(),
    }
    return replace(evidence, decoded=decoded)


def _evidence_key(evidence: CipObjectEvidence) -> str:
    attribute = "all" if evidence.attribute is None else str(evidence.attribute)
    return (
        f"class:{evidence.class_code}|instance:{evidence.instance}|"
        f"attribute:{attribute}|service:{evidence.service}"
    )
