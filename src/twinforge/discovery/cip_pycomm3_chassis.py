"""Permission-gated routed chassis Identity evidence for pycomm3."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol

from .chassis import (
    CipChassisObservation,
    CipChassisSlotObservation,
    CipChassisSlotPlan,
    CipChassisSlotRouteMap,
    CipSlotState,
)
from .cip_pycomm3 import CipIdentityReply, decode_cip_identity
from .cip_pycomm3_routed import (
    RoutedExecutionPermit,
    validate_routed_execution,
)
from .cip_routes import CipRouteDeclaration
from .contracts import (
    CipIdentityObservation,
    DiscoveryProviderError,
)
from .controller import JsonEvidence


class RoutedSlotOutcome(str, Enum):
    """Transport-level result requiring no inference by the provider."""

    POPULATED = "populated"
    EMPTY = "empty"
    NO_RESPONSE = "no_response"
    UNSUPPORTED_ROUTE = "unsupported_route"
    DEVICE_FAULT = "device_fault"


@dataclass(frozen=True)
class RoutedSlotResult:
    """Typed routed result with status and raw response evidence."""

    outcome: RoutedSlotOutcome
    reply: CipIdentityReply | None = None
    raw_response: bytes | None = None
    general_status: int | None = None
    additional_status: tuple[int, ...] = ()
    message: str | None = None
    raw_attributes: dict[str, JsonEvidence] | None = None

    def __post_init__(self) -> None:
        if self.outcome is RoutedSlotOutcome.POPULATED and self.reply is None:
            raise ValueError("populated routed slot result requires a reply")
        if self.outcome is not RoutedSlotOutcome.POPULATED and self.reply is not None:
            raise ValueError("only a populated routed slot result may have a reply")


class Pycomm3RoutedSlotTransport(Protocol):
    """Injectable boundary returning an explicit outcome for one slot route."""

    def read_slot_identity(
        self,
        route: CipRouteDeclaration,
        timeout: float,
    ) -> RoutedSlotResult:
        """Read one exact slot route and retain its transport outcome."""
        ...


class PermittedPycomm3ChassisProvider:
    """Enumerate only explicitly mapped slots under an operator permit."""

    def __init__(
        self,
        route_map: CipChassisSlotRouteMap,
        *,
        authorization_reference: str,
        permit: RoutedExecutionPermit | None = None,
        timeout: float = 2.0,
        transport: Pycomm3RoutedSlotTransport,
    ) -> None:
        if not authorization_reference.strip():
            raise ValueError("authorization_reference must not be empty")
        if timeout <= 0 or timeout > 10:
            raise ValueError("timeout must be greater than 0 and at most 10 seconds")
        self._route_map = route_map
        self._authorization_reference = authorization_reference
        self._permit = permit
        self._timeout = timeout
        self._transport = transport
        self._captured = False

    def read_chassis(
        self,
        plan: CipChassisSlotPlan,
        *,
        captured_at: datetime,
    ) -> CipChassisObservation:
        """Read every mapped slot once after validating the complete permit."""
        if plan != self._route_map.plan:
            raise DiscoveryProviderError(
                "cip_chassis_plan_not_allowed",
                "chassis plan does not match the configured slot route map",
            )
        route_keys = tuple(route.key for _, route in self._route_map.routes)
        validate_routed_execution(
            self._permit,
            self._authorization_reference,
            route_keys,
        )
        if self._captured:
            raise DiscoveryProviderError(
                "cip_chassis_request_budget_exceeded",
                "the chassis plan request budget is exhausted",
            )
        self._captured = True
        observations = tuple(
            self._read_slot(slot, route, captured_at)
            for slot, route in self._route_map.routes
        )
        return CipChassisObservation(
            plan=plan,
            captured_at=captured_at,
            slots=observations,
        )

    def _read_slot(
        self,
        slot: int,
        route: CipRouteDeclaration,
        captured_at: datetime,
    ) -> CipChassisSlotObservation:
        result = self._transport.read_slot_identity(route, self._timeout)
        raw_attributes = dict(result.raw_attributes or {})
        raw_attributes["route_key"] = route.key
        if result.outcome is RoutedSlotOutcome.POPULATED:
            assert result.reply is not None
            decoded, trailing = decode_cip_identity(result.reply.payload)
            trailing_payload_hex = (
                trailing.hex() if trailing else None
            )
            raw_attributes["trailing_payload_hex"] = trailing_payload_hex
            identity = CipIdentityObservation(
                target=route.gateway,
                captured_at=captured_at,
                raw_payload_hex=result.reply.payload.hex(),
                raw_attributes={
                    "route_key": route.key,
                    "trailing_payload_hex": trailing_payload_hex,
                },
                **decoded,
            )
        else:
            identity = None
        return CipChassisSlotObservation(
            slot=slot,
            state=CipSlotState(result.outcome.value),
            identity=identity,
            general_status=result.general_status,
            additional_status=result.additional_status,
            message=result.message,
            raw_response_hex=(
                result.raw_response.hex()
                if result.raw_response is not None
                else result.reply.raw_reply.hex()
                if result.reply is not None and result.reply.raw_reply is not None
                else None
            ),
            raw_attributes=raw_attributes,
        )
