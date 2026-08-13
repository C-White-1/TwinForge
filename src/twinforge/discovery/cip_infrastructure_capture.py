"""Permission-gated raw capture of planned CIP infrastructure evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from .cip_infrastructure_plan import (
    CipInfrastructureDiscoveryPlan,
    CipInfrastructureReadRequest,
    cip_infrastructure_plan_data,
)
from .cip_pycomm3_routed import (
    RoutedExecutionPermit,
    validate_routed_execution,
)
from .cip_routes import CipRouteDeclaration
from .contracts import DiscoveryProviderError, DiscoveryTarget
from .controller import CipObjectEvidence


@dataclass(frozen=True)
class CipInfrastructureTransportResult:
    """Uninterpreted response to one allowlisted infrastructure read."""

    general_status: int
    response_payload: bytes
    additional_status: tuple[int, ...] = ()
    raw_reply: bytes | None = None
    message: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.general_status, bool) or self.general_status < 0:
            raise ValueError("CIP general status must be non-negative")
        if any(isinstance(value, bool) or value < 0 for value in self.additional_status):
            raise ValueError("CIP additional status must be non-negative")


class CipInfrastructureTransport(Protocol):
    """Injectable boundary for one exact infrastructure-object request."""

    def read_infrastructure(
        self,
        target: DiscoveryTarget,
        route: CipRouteDeclaration,
        request: CipInfrastructureReadRequest,
        timeout: float,
    ) -> CipInfrastructureTransportResult:
        """Return raw status and payload evidence without decoding it."""
        ...


@dataclass(frozen=True)
class CipInfrastructureCapture:
    """Complete raw evidence obtained from one immutable plan."""

    plan: CipInfrastructureDiscoveryPlan
    captured_at: datetime
    object_evidence: tuple[CipObjectEvidence, ...]

    def __post_init__(self) -> None:
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must include a timezone")


class PermittedCipInfrastructureExecutor:
    """Execute one routed infrastructure plan after complete preflight."""

    def __init__(
        self,
        plan: CipInfrastructureDiscoveryPlan,
        *,
        permit: RoutedExecutionPermit | None,
        transport: CipInfrastructureTransport,
        timeout: float = 2.0,
    ) -> None:
        if plan.route is None:
            raise ValueError("infrastructure executor requires a routed plan")
        if timeout <= 0 or timeout > 10:
            raise ValueError("timeout must be greater than 0 and at most 10 seconds")
        self._plan = plan
        self._permit = permit
        self._transport = transport
        self._timeout = timeout
        self._executed = False

    def preflight(self) -> None:
        """Validate authorization and one-shot budget without transport I/O."""
        assert self._plan.route is not None
        validate_routed_execution(
            self._permit,
            self._plan.authorization_reference,
            (self._plan.route.key,),
        )
        if self._executed:
            raise DiscoveryProviderError(
                "cip_infrastructure_request_budget_exceeded",
                "the CIP infrastructure plan request budget is exhausted",
            )

    def capture(self, *, captured_at: datetime) -> CipInfrastructureCapture:
        """Execute each allowlisted read once and preserve every response."""
        if captured_at.tzinfo is None:
            raise ValueError("captured_at must include a timezone")
        self.preflight()
        assert self._plan.route is not None
        self._executed = True
        evidence: list[CipObjectEvidence] = []
        for request in sorted(self._plan.requests, key=lambda item: item.key):
            result = self._transport.read_infrastructure(
                self._plan.target,
                self._plan.route,
                request,
                self._timeout,
            )
            evidence.append(
                CipObjectEvidence(
                    class_code=request.object_type.class_code,
                    instance=request.instance,
                    attribute=request.attribute,
                    service=request.service.value,
                    general_status=result.general_status,
                    additional_status=result.additional_status,
                    response_payload_hex=result.response_payload.hex(),
                    raw_reply_hex=(
                        result.raw_reply.hex()
                        if result.raw_reply is not None
                        else None
                    ),
                    message=result.message,
                )
            )
        return CipInfrastructureCapture(
            plan=self._plan,
            captured_at=captured_at,
            object_evidence=tuple(evidence),
        )


def cip_infrastructure_capture_data(
    capture: CipInfrastructureCapture,
) -> dict[str, Any]:
    """Return deterministic raw evidence and its complete request plan."""
    return {
        "schema_version": "1.0",
        "captured_at": capture.captured_at.isoformat(),
        "plan": cip_infrastructure_plan_data(capture.plan),
        "object_evidence": [
            {
                "class_code": item.class_code,
                "instance": item.instance,
                "attribute": item.attribute,
                "service": item.service,
                "general_status": item.general_status,
                "additional_status": list(item.additional_status),
                "response_payload_hex": item.response_payload_hex,
                "raw_reply_hex": item.raw_reply_hex,
                "message": item.message,
                "decoded": dict(sorted(item.decoded.items())),
            }
            for item in capture.object_evidence
        ],
    }


def cip_infrastructure_capture_json(capture: CipInfrastructureCapture) -> str:
    """Serialize raw infrastructure evidence with a final newline."""
    return json.dumps(
        cip_infrastructure_capture_data(capture),
        indent=2,
        ensure_ascii=False,
    ) + "\n"
