"""Socket-free policy plans for CIP software metadata and runtime values."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .cip_routes import CipRouteDeclaration, cip_route_data
from .contracts import DiscoveryTarget


class CipSoftwareInventoryCapability(str, Enum):
    """Structural controller content that a provider may enumerate."""

    PROGRAMS = "programs"
    ROUTINES = "routines"
    TASKS = "tasks"
    TAG_DEFINITIONS = "tag_definitions"


@dataclass(frozen=True)
class CipSoftwareInventoryPlan:
    """Bounded structural-metadata plan that cannot authorize tag values."""

    target: DiscoveryTarget
    authorization_reference: str
    capabilities: tuple[CipSoftwareInventoryCapability, ...]
    maximum_requests: int
    route: CipRouteDeclaration | None = None

    def __post_init__(self) -> None:
        _validate_common(
            self.target,
            self.route,
            self.authorization_reference,
            self.maximum_requests,
        )
        if not self.capabilities:
            raise ValueError("software inventory requires at least one capability")
        ordered = tuple(sorted(set(self.capabilities), key=lambda item: item.value))
        if ordered != self.capabilities:
            raise ValueError("software inventory capabilities must be unique and sorted")


@dataclass(frozen=True)
class CipRuntimeValueReadPlan:
    """Separate approval record for bounded, named runtime tag-value reads."""

    target: DiscoveryTarget
    authorization_reference: str
    runtime_value_approval_reference: str
    justification: str
    tag_paths: tuple[str, ...]
    maximum_requests: int
    route: CipRouteDeclaration | None = None

    def __post_init__(self) -> None:
        _validate_common(
            self.target,
            self.route,
            self.authorization_reference,
            self.maximum_requests,
        )
        for name, value in (
            ("runtime_value_approval_reference", self.runtime_value_approval_reference),
            ("justification", self.justification),
        ):
            if not value or value != value.strip():
                raise ValueError(f"{name} must be non-empty and trimmed")
        if not self.tag_paths:
            raise ValueError("runtime value plan requires at least one tag path")
        if any(not path or path != path.strip() for path in self.tag_paths):
            raise ValueError("runtime tag paths must be non-empty and trimmed")
        if len(self.tag_paths) != len(set(self.tag_paths)):
            raise ValueError("runtime tag paths must be unique")
        if self.maximum_requests < len(self.tag_paths):
            raise ValueError("maximum_requests must cover every runtime tag path")


def cip_software_inventory_plan_data(
    plan: CipSoftwareInventoryPlan,
) -> dict[str, Any]:
    """Return a deterministic metadata-only dry-run plan."""
    return {
        "schema_version": "1.0",
        "dry_run": True,
        "operation": "cip_software_inventory",
        "authorization_reference": plan.authorization_reference,
        "target": plan.target.model_dump(mode="json"),
        "route": cip_route_data(plan.route) if plan.route is not None else None,
        "capabilities": [item.value for item in plan.capabilities],
        "maximum_requests": plan.maximum_requests,
        "runtime_values_permitted": False,
    }


def cip_runtime_value_plan_data(plan: CipRuntimeValueReadPlan) -> dict[str, Any]:
    """Return a deterministic separately approved runtime-value dry run."""
    return {
        "schema_version": "1.0",
        "dry_run": True,
        "operation": "cip_runtime_values",
        "authorization_reference": plan.authorization_reference,
        "runtime_value_approval_reference": (
            plan.runtime_value_approval_reference
        ),
        "justification": plan.justification,
        "target": plan.target.model_dump(mode="json"),
        "route": cip_route_data(plan.route) if plan.route is not None else None,
        "tag_paths": list(plan.tag_paths),
        "maximum_requests": plan.maximum_requests,
        "runtime_values_permitted": True,
    }


def cip_software_inventory_plan_json(plan: CipSoftwareInventoryPlan) -> str:
    """Serialize a structural software-inventory plan."""
    return json.dumps(cip_software_inventory_plan_data(plan), indent=2) + "\n"


def cip_runtime_value_plan_json(plan: CipRuntimeValueReadPlan) -> str:
    """Serialize a separately approved runtime-value plan."""
    return json.dumps(cip_runtime_value_plan_data(plan), indent=2) + "\n"


def _validate_common(
    target: DiscoveryTarget,
    route: CipRouteDeclaration | None,
    authorization_reference: str,
    maximum_requests: int,
) -> None:
    if not authorization_reference or authorization_reference != authorization_reference.strip():
        raise ValueError("authorization_reference must be non-empty and trimmed")
    if isinstance(maximum_requests, bool) or maximum_requests <= 0:
        raise ValueError("maximum_requests must be a positive integer")
    if route is not None and route.gateway.key != target.key:
        raise ValueError("software inventory route gateway does not match target")
