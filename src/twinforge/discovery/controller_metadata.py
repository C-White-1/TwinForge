"""Explicit request planning for read-only CIP controller metadata."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .cip_routes import CipRouteDeclaration, cip_route_data
from .contracts import DiscoveryTarget


class CipMetadataReadService(int, Enum):
    """Read-only CIP services permitted in a metadata plan."""

    GET_ATTRIBUTES_ALL = 0x01
    GET_ATTRIBUTE_SINGLE = 0x0E


class CipMetadataNamespace(str, Enum):
    """Specification ownership of a planned metadata request."""

    STANDARD_CIP = "standard_cip"
    VENDOR_SPECIFIC = "vendor_specific"


class ControllerMetadataField(str, Enum):
    """Vendor-neutral metadata fields a response may populate."""

    LOGICAL_NAME = "logical_name"
    PROJECT_NAME = "project_name"
    PROJECT_REVISION = "project_revision"
    FIRMWARE_REVISION = "firmware_revision"
    OPERATING_MODE = "operating_mode"


@dataclass(frozen=True)
class CipControllerMetadataRequest:
    """One specification-attributed, read-only CIP object request."""

    name: str
    service: CipMetadataReadService
    class_code: int
    instance: int
    specification_reference: str
    namespace: CipMetadataNamespace
    attribute: int | None = None
    semantic_field: ControllerMetadataField | None = None
    vendor_id: int | None = None
    decoder: str | None = None
    request_budget: int = 1

    def __post_init__(self) -> None:
        if not self.name or self.name != self.name.strip():
            raise ValueError("metadata request name must be non-empty and trimmed")
        if (
            not self.specification_reference
            or self.specification_reference != self.specification_reference.strip()
        ):
            raise ValueError(
                "specification_reference must be non-empty and trimmed"
            )
        numeric = (self.class_code, self.instance)
        if any(isinstance(value, bool) or value < 0 for value in numeric):
            raise ValueError("CIP class and instance must be non-negative integers")
        if self.attribute is not None and (
            isinstance(self.attribute, bool) or self.attribute < 0
        ):
            raise ValueError("CIP attribute must be a non-negative integer")
        if (
            self.service is CipMetadataReadService.GET_ATTRIBUTE_SINGLE
            and self.attribute is None
        ):
            raise ValueError("Get_Attribute_Single requires an attribute")
        if (
            self.service is CipMetadataReadService.GET_ATTRIBUTES_ALL
            and self.attribute is not None
        ):
            raise ValueError("Get_Attributes_All must not specify an attribute")
        if self.namespace is CipMetadataNamespace.VENDOR_SPECIFIC:
            if self.vendor_id is None or self.vendor_id < 0:
                raise ValueError("vendor-specific metadata requires a vendor ID")
        elif self.vendor_id is not None:
            raise ValueError("standard CIP metadata must not specify a vendor ID")
        if self.request_budget != 1:
            raise ValueError("each metadata request budget must equal one")
        if self.decoder is not None and self.decoder != self.decoder.strip():
            raise ValueError("decoder name must not contain surrounding whitespace")

    @property
    def key(self) -> str:
        """Return a deterministic request identity."""
        attribute = "all" if self.attribute is None else str(self.attribute)
        return (
            f"service:{self.service.value}|class:{self.class_code}|"
            f"instance:{self.instance}|attribute:{attribute}"
        )


@dataclass(frozen=True)
class CipControllerMetadataPlan:
    """Exact metadata request allowlist for one direct or routed controller."""

    target: DiscoveryTarget
    authorization_reference: str
    requests: tuple[CipControllerMetadataRequest, ...]
    route: CipRouteDeclaration | None = None

    def __post_init__(self) -> None:
        if (
            not self.authorization_reference
            or self.authorization_reference != self.authorization_reference.strip()
        ):
            raise ValueError(
                "authorization_reference must be non-empty and trimmed"
            )
        if not self.requests:
            raise ValueError("controller metadata plan requires at least one request")
        if self.route is not None and self.route.gateway.key != self.target.key:
            raise ValueError("metadata route gateway does not match target")
        keys = [request.key for request in self.requests]
        if len(keys) != len(set(keys)):
            raise ValueError("controller metadata requests must be unique")
        fields = [
            request.semantic_field
            for request in self.requests
            if request.semantic_field is not None
        ]
        if len(fields) != len(set(fields)):
            raise ValueError("controller metadata semantic fields must be unique")

    @property
    def total_request_budget(self) -> int:
        """Return the maximum requests permitted by this plan."""
        return sum(request.request_budget for request in self.requests)


def cip_controller_metadata_plan_data(
    plan: CipControllerMetadataPlan,
) -> dict[str, Any]:
    """Return a deterministic, JSON-compatible dry-run plan."""
    return {
        "schema_version": "1.0",
        "dry_run": True,
        "operation": "cip_controller_metadata",
        "authorization_reference": plan.authorization_reference,
        "target": plan.target.model_dump(mode="json"),
        "route": cip_route_data(plan.route) if plan.route is not None else None,
        "total_request_budget": plan.total_request_budget,
        "runtime_values_permitted": False,
        "requests": [
            {
                "name": request.name,
                "key": request.key,
                "service": request.service.name.lower(),
                "service_code": request.service.value,
                "class_code": request.class_code,
                "instance": request.instance,
                "attribute": request.attribute,
                "namespace": request.namespace.value,
                "vendor_id": request.vendor_id,
                "semantic_field": (
                    request.semantic_field.value
                    if request.semantic_field is not None
                    else None
                ),
                "specification_reference": request.specification_reference,
                "decoder": request.decoder,
                "request_budget": request.request_budget,
            }
            for request in sorted(
                plan.requests,
                key=lambda item: (
                    item.service.value,
                    item.class_code,
                    item.instance,
                    item.attribute if item.attribute is not None else -1,
                ),
            )
        ],
    }


def cip_controller_metadata_plan_json(plan: CipControllerMetadataPlan) -> str:
    """Serialize a metadata dry-run plan with a final newline."""
    return json.dumps(
        cip_controller_metadata_plan_data(plan),
        indent=2,
        ensure_ascii=False,
    ) + "\n"
