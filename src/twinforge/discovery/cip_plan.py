"""Deterministic dry-run planning for bounded CIP Identity capture."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .cip_pycomm3 import (
    validate_cip_identity_target,
    validate_cip_identity_timeout,
)
from .contracts import DiscoveryOperation, DiscoveryScope, DiscoveryTarget


@dataclass(frozen=True)
class CipIdentityPlanTarget:
    """One exact endpoint and its maximum request count."""

    target: DiscoveryTarget
    request_budget: int = 1


@dataclass(frozen=True)
class CipIdentityCapturePlan:
    """Socket-free statement of an intended CIP Identity capture."""

    schema_version: str
    engagement: str
    authorization_reference: str
    operation: DiscoveryOperation
    timeout_seconds: float
    targets: tuple[CipIdentityPlanTarget, ...]

    @property
    def total_request_budget(self) -> int:
        """Return the maximum requests permitted by this plan."""
        return sum(item.request_budget for item in self.targets)


def plan_cip_identity_capture(
    scope: DiscoveryScope,
    *,
    timeout: float = 2.0,
) -> CipIdentityCapturePlan:
    """Build a validated plan without constructing or calling a transport."""
    if DiscoveryOperation.CIP_IDENTITY not in scope.operations:
        raise ValueError("scope does not authorize CIP Identity discovery")
    validate_cip_identity_timeout(timeout)
    targets = tuple(sorted(scope.targets, key=lambda target: target.key))
    for target in targets:
        validate_cip_identity_target(target)
    return CipIdentityCapturePlan(
        schema_version="1.0",
        engagement=scope.engagement,
        authorization_reference=scope.authorization_reference,
        operation=DiscoveryOperation.CIP_IDENTITY,
        timeout_seconds=timeout,
        targets=tuple(CipIdentityPlanTarget(target) for target in targets),
    )


def cip_identity_plan_data(plan: CipIdentityCapturePlan) -> dict[str, Any]:
    """Return a stable JSON-compatible dry-run representation."""
    return {
        "schema_version": plan.schema_version,
        "dry_run": True,
        "engagement": plan.engagement,
        "authorization_reference": plan.authorization_reference,
        "operation": plan.operation.value,
        "transport": "EtherNet/IP TCP 44818, unconnected",
        "timeout_seconds": plan.timeout_seconds,
        "total_request_budget": plan.total_request_budget,
        "targets": [
            {
                "address": item.target.address,
                "route": list(item.target.route),
                "label": item.target.label,
                "request_budget": item.request_budget,
            }
            for item in plan.targets
        ],
    }


def cip_identity_plan_json(plan: CipIdentityCapturePlan) -> str:
    """Serialize a dry-run plan deterministically with a final newline."""
    return json.dumps(
        cip_identity_plan_data(plan),
        indent=2,
        ensure_ascii=False,
    ) + "\n"
