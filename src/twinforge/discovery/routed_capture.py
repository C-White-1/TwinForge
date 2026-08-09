"""Socket-independent orchestration for routed CIP evidence capture."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from .chassis import (
    CipChassisDiscoveryProvider,
    CipChassisObservation,
    CipChassisSlotPlan,
    cip_chassis_data,
)
from .cip_routes import CipRouteDeclaration, cip_route_data
from .contracts import (
    DiscoveryDiagnostic,
    DiscoveryDiagnosticSeverity,
    DiscoveryProviderError,
    DiscoveryTarget,
)
from .controller import (
    CipControllerDiscoveryProvider,
    CipControllerObservation,
    cip_controller_data,
)


@dataclass(frozen=True)
class CipControllerReadPlan:
    """One explicitly authorized direct or routed controller read."""

    target: DiscoveryTarget
    route: CipRouteDeclaration | None = None
    request_budget: int = 1

    def __post_init__(self) -> None:
        if self.route is not None and self.route.gateway.key != self.target.key:
            raise ValueError("controller route gateway does not match target")
        if self.request_budget != 1:
            raise ValueError("controller metadata request budget must equal one")

    @property
    def key(self) -> str:
        """Return a stable direct-or-routed request identity."""
        route_key = self.route.key if self.route is not None else "direct"
        return f"{self.target.key}|{route_key}"


@dataclass(frozen=True)
class CipRoutedCapturePlan:
    """Complete offline statement of routed reads and their request bounds."""

    engagement: str
    authorization_reference: str
    controllers: tuple[CipControllerReadPlan, ...] = ()
    chassis: tuple[CipChassisSlotPlan, ...] = ()

    def __post_init__(self) -> None:
        if not self.engagement or self.engagement != self.engagement.strip():
            raise ValueError("engagement must be non-empty and trimmed")
        if (
            not self.authorization_reference
            or self.authorization_reference != self.authorization_reference.strip()
        ):
            raise ValueError(
                "authorization_reference must be non-empty and trimmed"
            )
        if not self.controllers and not self.chassis:
            raise ValueError("routed capture plan must contain at least one read")
        controller_keys = [item.key for item in self.controllers]
        if len(controller_keys) != len(set(controller_keys)):
            raise ValueError("controller read plans must be unique")
        chassis_keys = [item.route.key for item in self.chassis]
        if len(chassis_keys) != len(set(chassis_keys)):
            raise ValueError("chassis read plans must use unique routes")

    @property
    def total_request_budget(self) -> int:
        """Return the maximum request count across all planned reads."""
        return sum(item.request_budget for item in self.controllers) + sum(
            item.total_request_budget for item in self.chassis
        )


@dataclass(frozen=True)
class CipRoutedDiscoverySnapshot:
    """Controller and chassis evidence plus target-specific diagnostics."""

    schema_version: str
    engagement: str
    authorization_reference: str
    captured_at: datetime
    plan: CipRoutedCapturePlan
    controllers: tuple[CipControllerObservation, ...] = ()
    chassis: tuple[CipChassisObservation, ...] = ()
    diagnostics: tuple[DiscoveryDiagnostic, ...] = ()


class CipRoutedDiscoveryProvider(
    CipControllerDiscoveryProvider,
    CipChassisDiscoveryProvider,
    Protocol,
):
    """Combined provider boundary consumed by routed capture orchestration."""


def capture_routed_cip(
    plan: CipRoutedCapturePlan,
    provider: CipRoutedDiscoveryProvider,
    *,
    captured_at: datetime | None = None,
) -> CipRoutedDiscoverySnapshot:
    """Execute each explicit plan item once and retain expected failures."""
    timestamp = captured_at or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        raise ValueError("captured_at must include a timezone")
    controllers: list[CipControllerObservation] = []
    chassis: list[CipChassisObservation] = []
    diagnostics: list[DiscoveryDiagnostic] = []

    for request in sorted(plan.controllers, key=lambda item: item.key):
        try:
            observed = provider.read_controller(
                request.target,
                route=request.route,
                captured_at=timestamp,
            )
            if observed.target.key != request.target.key or observed.route != request.route:
                raise DiscoveryProviderError(
                    "controller_evidence_mismatch",
                    "provider returned controller evidence outside its plan item",
                )
            controllers.append(observed)
        except DiscoveryProviderError as error:
            diagnostics.append(_diagnostic(request.target, error))

    for slot_plan in sorted(plan.chassis, key=lambda item: item.route.key):
        try:
            observed = provider.read_chassis(slot_plan, captured_at=timestamp)
            if observed.plan != slot_plan:
                raise DiscoveryProviderError(
                    "chassis_evidence_mismatch",
                    "provider returned chassis evidence outside its plan item",
                )
            chassis.append(observed)
        except DiscoveryProviderError as error:
            diagnostics.append(_diagnostic(slot_plan.route.gateway, error))

    return CipRoutedDiscoverySnapshot(
        schema_version="1.0",
        engagement=plan.engagement,
        authorization_reference=plan.authorization_reference,
        captured_at=timestamp,
        plan=plan,
        controllers=tuple(controllers),
        chassis=tuple(chassis),
        diagnostics=tuple(
            sorted(
                diagnostics,
                key=lambda item: (item.target.key, item.code, item.message),
            )
        ),
    )


def cip_routed_snapshot_data(
    snapshot: CipRoutedDiscoverySnapshot,
) -> dict[str, Any]:
    """Return a stable JSON-compatible routed snapshot."""
    return {
        "schema_version": snapshot.schema_version,
        "engagement": snapshot.engagement,
        "authorization_reference": snapshot.authorization_reference,
        "captured_at": snapshot.captured_at.isoformat(),
        "plan": {
            "total_request_budget": snapshot.plan.total_request_budget,
            "controllers": [
                {
                    "target": item.target.model_dump(mode="json"),
                    "route": (
                        cip_route_data(item.route)
                        if item.route is not None
                        else None
                    ),
                    "request_budget": item.request_budget,
                }
                for item in sorted(
                    snapshot.plan.controllers,
                    key=lambda item: item.key,
                )
            ],
            "chassis": [
                {
                    "route": cip_route_data(item.route),
                    "slots": list(item.slots),
                    "request_budget_per_slot": item.request_budget_per_slot,
                }
                for item in sorted(
                    snapshot.plan.chassis,
                    key=lambda item: item.route.key,
                )
            ],
        },
        "controllers": [
            cip_controller_data(item)
            for item in sorted(
                snapshot.controllers,
                key=lambda item: (
                    item.target.key,
                    item.route.key if item.route is not None else "direct",
                ),
            )
        ],
        "chassis": [
            cip_chassis_data(item)
            for item in sorted(
                snapshot.chassis,
                key=lambda item: item.plan.route.key,
            )
        ],
        "diagnostics": [
            {
                "target": item.target.model_dump(mode="json"),
                "severity": item.severity.value,
                "code": item.code,
                "message": item.message,
            }
            for item in snapshot.diagnostics
        ],
    }


def cip_routed_snapshot_json(snapshot: CipRoutedDiscoverySnapshot) -> str:
    """Serialize a routed snapshot deterministically with a final newline."""
    return json.dumps(
        cip_routed_snapshot_data(snapshot),
        indent=2,
        ensure_ascii=False,
    ) + "\n"


def _diagnostic(
    target: DiscoveryTarget,
    error: DiscoveryProviderError,
) -> DiscoveryDiagnostic:
    return DiscoveryDiagnostic(
        target=target,
        severity=DiscoveryDiagnosticSeverity.ERROR,
        code=error.code,
        message=str(error),
    )
