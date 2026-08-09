"""Vendor-neutral evidence contracts for routed controller discovery."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, TypeAlias

from .cip_routes import CipRouteDeclaration, cip_route_data
from .contracts import CipIdentityObservation, DiscoveryTarget


JsonEvidence: TypeAlias = (
    str
    | int
    | float
    | bool
    | None
    | list["JsonEvidence"]
    | dict[str, "JsonEvidence"]
)


@dataclass(frozen=True)
class CipObjectEvidence:
    """One attributable CIP object response with its raw bytes retained."""

    class_code: int
    instance: int
    service: int
    general_status: int
    attribute: int | None = None
    additional_status: tuple[int, ...] = ()
    request_payload_hex: str | None = None
    response_payload_hex: str | None = None
    raw_reply_hex: str | None = None
    message: str | None = None
    decoded: dict[str, JsonEvidence] = field(default_factory=dict)

    def __post_init__(self) -> None:
        numeric = (
            self.class_code,
            self.instance,
            self.service,
            self.general_status,
            *self.additional_status,
        )
        if any(value < 0 for value in numeric):
            raise ValueError("CIP object evidence values must not be negative")
        if self.attribute is not None and self.attribute < 0:
            raise ValueError("CIP attribute number must not be negative")


@dataclass(frozen=True)
class CipControllerObservation:
    """Observed controller identity and optional vendor-neutral metadata."""

    target: DiscoveryTarget
    captured_at: datetime
    identity: CipIdentityObservation
    route: CipRouteDeclaration | None = None
    logical_name: str | None = None
    project_name: str | None = None
    project_revision: str | None = None
    firmware_revision: str | None = None
    operating_mode: str | None = None
    raw_attributes: dict[str, JsonEvidence] = field(default_factory=dict)
    object_evidence: tuple[CipObjectEvidence, ...] = ()

    def __post_init__(self) -> None:
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must include a timezone")
        if self.identity.target.key != self.target.key:
            raise ValueError("controller identity target does not match target")
        if self.route is not None and self.route.gateway.key != self.target.key:
            raise ValueError("controller route gateway does not match target")


class CipControllerDiscoveryProvider(Protocol):
    """Future provider boundary for authorized controller metadata reads."""

    def read_controller(
        self,
        target: DiscoveryTarget,
        *,
        route: CipRouteDeclaration | None,
        captured_at: datetime,
    ) -> CipControllerObservation:
        """Read controller evidence for one explicitly authorized endpoint."""
        ...


def cip_controller_data(observation: CipControllerObservation) -> dict[str, Any]:
    """Return a deterministic, JSON-compatible controller observation."""
    identity = observation.identity
    return {
        "target": {
            "address": observation.target.address,
            "route": list(observation.target.route),
            "label": observation.target.label,
        },
        "captured_at": observation.captured_at.isoformat(),
        "route": (
            cip_route_data(observation.route)
            if observation.route is not None
            else None
        ),
        "identity": {
            "vendor_id": identity.vendor_id,
            "device_type": identity.device_type,
            "product_code": identity.product_code,
            "major_revision": identity.major_revision,
            "minor_revision": identity.minor_revision,
            "status": identity.status,
            "serial_number": identity.serial_number,
            "product_name": identity.product_name,
            "state": identity.state,
            "raw_payload_hex": identity.raw_payload_hex,
            "raw_attributes": dict(sorted(identity.raw_attributes.items())),
        },
        "metadata": {
            "logical_name": observation.logical_name,
            "project_name": observation.project_name,
            "project_revision": observation.project_revision,
            "firmware_revision": observation.firmware_revision,
            "operating_mode": observation.operating_mode,
        },
        "raw_attributes": dict(sorted(observation.raw_attributes.items())),
        "object_evidence": [
            _object_evidence_data(item)
            for item in sorted(
                observation.object_evidence,
                key=lambda item: (
                    item.class_code,
                    item.instance,
                    item.attribute if item.attribute is not None else -1,
                    item.service,
                ),
            )
        ],
    }


def cip_controller_json(observation: CipControllerObservation) -> str:
    """Serialize controller evidence deterministically with a final newline."""
    return json.dumps(
        cip_controller_data(observation),
        indent=2,
        ensure_ascii=False,
    ) + "\n"


def _object_evidence_data(evidence: CipObjectEvidence) -> dict[str, Any]:
    return {
        "class_code": evidence.class_code,
        "instance": evidence.instance,
        "attribute": evidence.attribute,
        "service": evidence.service,
        "general_status": evidence.general_status,
        "additional_status": list(evidence.additional_status),
        "request_payload_hex": evidence.request_payload_hex,
        "response_payload_hex": evidence.response_payload_hex,
        "raw_reply_hex": evidence.raw_reply_hex,
        "message": evidence.message,
        "decoded": dict(sorted(evidence.decoded.items())),
    }
