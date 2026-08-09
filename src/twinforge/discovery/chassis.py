"""Bounded plans and evidence contracts for CIP chassis inventory."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol

from .cip_routes import CipRouteDeclaration, cip_route_data
from .contracts import CipIdentityObservation
from .controller import JsonEvidence


class CipSlotState(str, Enum):
    """Observed result of one explicitly planned chassis-slot request."""

    POPULATED = "populated"
    EMPTY = "empty"
    NO_RESPONSE = "no_response"
    UNSUPPORTED_ROUTE = "unsupported_route"
    DEVICE_FAULT = "device_fault"


@dataclass(frozen=True)
class CipChassisSlotPlan:
    """Exact slots authorized beneath one declared CIP route."""

    route: CipRouteDeclaration
    slots: tuple[int, ...]
    request_budget_per_slot: int = 1

    def __post_init__(self) -> None:
        if not self.slots:
            raise ValueError("chassis slot plan must contain at least one slot")
        if any(isinstance(slot, bool) or slot < 0 for slot in self.slots):
            raise ValueError("chassis slot numbers must be non-negative integers")
        if tuple(sorted(set(self.slots))) != self.slots:
            raise ValueError("chassis slots must be unique and sorted")
        if self.request_budget_per_slot <= 0:
            raise ValueError("request_budget_per_slot must be positive")

    @property
    def total_request_budget(self) -> int:
        """Return the plan-wide upper request bound."""
        return len(self.slots) * self.request_budget_per_slot


@dataclass(frozen=True)
class CipChassisSlotObservation:
    """Evidence and explicit outcome for one requested chassis slot."""

    slot: int
    state: CipSlotState
    identity: CipIdentityObservation | None = None
    general_status: int | None = None
    additional_status: tuple[int, ...] = ()
    message: str | None = None
    raw_response_hex: str | None = None
    raw_attributes: dict[str, JsonEvidence] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.slot, bool) or self.slot < 0:
            raise ValueError("chassis slot number must be a non-negative integer")
        if self.state is CipSlotState.POPULATED and self.identity is None:
            raise ValueError("a populated slot requires identity evidence")
        if self.state is not CipSlotState.POPULATED and self.identity is not None:
            raise ValueError("only a populated slot may contain identity evidence")
        status_values = (
            (() if self.general_status is None else (self.general_status,))
            + self.additional_status
        )
        if any(value < 0 for value in status_values):
            raise ValueError("CIP status values must not be negative")


@dataclass(frozen=True)
class CipChassisObservation:
    """Complete outcome set for one bounded chassis-slot plan."""

    plan: CipChassisSlotPlan
    captured_at: datetime
    slots: tuple[CipChassisSlotObservation, ...]

    def __post_init__(self) -> None:
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must include a timezone")
        observed = tuple(sorted(item.slot for item in self.slots))
        if len(observed) != len(set(observed)):
            raise ValueError("chassis observation contains duplicate slots")
        if observed != self.plan.slots:
            raise ValueError("chassis observation must cover every planned slot")
        gateway_key = self.plan.route.gateway.key
        for item in self.slots:
            if item.identity is not None and item.identity.target.key != gateway_key:
                raise ValueError("slot identity target does not match route gateway")


class CipChassisDiscoveryProvider(Protocol):
    """Future provider boundary for bounded routed chassis reads."""

    def read_chassis(
        self,
        plan: CipChassisSlotPlan,
        *,
        captured_at: datetime,
    ) -> CipChassisObservation:
        """Return one explicit outcome for every authorized slot."""
        ...


def plan_cip_chassis_slots(
    route: CipRouteDeclaration,
    slots: tuple[int, ...],
    *,
    request_budget_per_slot: int = 1,
) -> CipChassisSlotPlan:
    """Canonicalize an explicit slot allowlist without opening a socket."""
    return CipChassisSlotPlan(
        route=route,
        slots=tuple(sorted(slots)),
        request_budget_per_slot=request_budget_per_slot,
    )


def cip_chassis_data(observation: CipChassisObservation) -> dict[str, Any]:
    """Return deterministic, JSON-compatible chassis evidence."""
    return {
        "captured_at": observation.captured_at.isoformat(),
        "plan": {
            "route": cip_route_data(observation.plan.route),
            "slots": list(observation.plan.slots),
            "request_budget_per_slot": observation.plan.request_budget_per_slot,
            "total_request_budget": observation.plan.total_request_budget,
        },
        "slots": [
            _slot_data(item)
            for item in sorted(observation.slots, key=lambda item: item.slot)
        ],
    }


def cip_chassis_json(observation: CipChassisObservation) -> str:
    """Serialize chassis evidence deterministically with a final newline."""
    return json.dumps(
        cip_chassis_data(observation),
        indent=2,
        ensure_ascii=False,
    ) + "\n"


def _slot_data(item: CipChassisSlotObservation) -> dict[str, Any]:
    identity = item.identity
    return {
        "slot": item.slot,
        "state": item.state.value,
        "identity": (
            {
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
            }
            if identity is not None
            else None
        ),
        "general_status": item.general_status,
        "additional_status": list(item.additional_status),
        "message": item.message,
        "raw_response_hex": item.raw_response_hex,
        "raw_attributes": dict(sorted(item.raw_attributes.items())),
    }
