"""Bounded read plans for CIP Assembly and Connection Manager evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

from twinforge.transport.cip import objects

from .cip_routes import CipRouteDeclaration, cip_route_data
from .contracts import DiscoveryTarget
from .controller_metadata import CipMetadataReadService


class CipInfrastructureObject(str, Enum):
    """CIP infrastructure objects admitted by this discovery boundary."""

    ASSEMBLY = "assembly"
    CONNECTION_MANAGER = "connection_manager"

    @property
    def class_code(self) -> int:
        """Return the standard CIP class code for this object."""
        return {
            CipInfrastructureObject.ASSEMBLY: objects.ASSEMBLY,
            CipInfrastructureObject.CONNECTION_MANAGER: (
                objects.CONNECTION_MANAGER
            ),
        }[self]


@dataclass(frozen=True)
class CipInfrastructureReadRequest:
    """One exact, specification-attributed read of a known object instance."""

    object_type: CipInfrastructureObject
    instance: int
    service: CipMetadataReadService
    specification_reference: str
    attribute: int | None = None
    purpose: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.instance, bool) or self.instance <= 0:
            raise ValueError("CIP infrastructure instance must be positive")
        if (
            not self.specification_reference
            or self.specification_reference
            != self.specification_reference.strip()
        ):
            raise ValueError(
                "specification_reference must be non-empty and trimmed"
            )
        if self.purpose is not None and (
            not self.purpose or self.purpose != self.purpose.strip()
        ):
            raise ValueError("purpose must be non-empty and trimmed when set")
        if self.service is CipMetadataReadService.GET_ATTRIBUTE_SINGLE:
            if isinstance(self.attribute, bool) or self.attribute is None:
                raise ValueError("Get_Attribute_Single requires an attribute")
            if self.attribute <= 0:
                raise ValueError("CIP infrastructure attribute must be positive")
        elif self.attribute is not None:
            raise ValueError("Get_Attributes_All must not specify an attribute")

    @property
    def key(self) -> str:
        """Return a deterministic identity for budget and duplicate checks."""
        attribute = "all" if self.attribute is None else str(self.attribute)
        return (
            f"class:{self.object_type.class_code}|instance:{self.instance}|"
            f"attribute:{attribute}|service:{self.service.value}"
        )


@dataclass(frozen=True)
class CipInfrastructureDiscoveryPlan:
    """Immutable allowlist for Assembly and Connection Manager reads."""

    target: DiscoveryTarget
    engagement: str
    authorization_reference: str
    requests: tuple[CipInfrastructureReadRequest, ...]
    maximum_requests: int
    route: CipRouteDeclaration | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("engagement", self.engagement),
            ("authorization_reference", self.authorization_reference),
        ):
            if not value or value != value.strip():
                raise ValueError(f"{name} must be non-empty and trimmed")
        if self.route is not None and self.route.gateway.key != self.target.key:
            raise ValueError("infrastructure route gateway does not match target")
        if not self.requests:
            raise ValueError("infrastructure discovery requires a request")
        keys = tuple(request.key for request in self.requests)
        if len(keys) != len(set(keys)):
            raise ValueError("infrastructure requests must be unique")
        if isinstance(self.maximum_requests, bool) or self.maximum_requests <= 0:
            raise ValueError("maximum_requests must be a positive integer")
        if self.maximum_requests < len(self.requests):
            raise ValueError("maximum_requests must cover every request")


def cip_infrastructure_plan_data(
    plan: CipInfrastructureDiscoveryPlan,
) -> dict[str, Any]:
    """Return the stable, socket-free dry-run representation."""
    return {
        "schema_version": "1.0",
        "dry_run": True,
        "operation": "cip_infrastructure_discovery",
        "engagement": plan.engagement,
        "authorization_reference": plan.authorization_reference,
        "target": plan.target.model_dump(mode="json"),
        "route": cip_route_data(plan.route) if plan.route is not None else None,
        "maximum_requests": plan.maximum_requests,
        "runtime_values_permitted": False,
        "requests": [
            {
                "key": request.key,
                "object_type": request.object_type.value,
                "class_code": request.object_type.class_code,
                "instance": request.instance,
                "service": request.service.name.lower(),
                "service_code": request.service.value,
                "attribute": request.attribute,
                "specification_reference": request.specification_reference,
                "purpose": request.purpose,
            }
            for request in sorted(plan.requests, key=lambda item: item.key)
        ],
    }


def cip_infrastructure_plan_json(
    plan: CipInfrastructureDiscoveryPlan,
) -> str:
    """Serialize an infrastructure plan deterministically."""
    return json.dumps(
        cip_infrastructure_plan_data(plan),
        indent=2,
        ensure_ascii=False,
    ) + "\n"
