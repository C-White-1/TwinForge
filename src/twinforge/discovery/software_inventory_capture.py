"""Capability-gated capture of structural CIP software evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from .cip_pycomm3_routed import (
    RoutedExecutionPermit,
    validate_routed_execution,
)
from .contracts import DiscoveryProviderError, DiscoveryTarget
from .controller import CipObjectEvidence, JsonEvidence
from .software_inventory_plan import (
    CipSoftwareInventoryCapability,
    CipSoftwareInventoryPlan,
)


@dataclass(frozen=True)
class CipSoftwareInventoryItem:
    """One structural item; runtime values have no representation here."""

    capability: CipSoftwareInventoryCapability
    name: str
    parent: str | None = None
    instance_id: int | None = None
    data_type: str | None = None
    language: str | None = None
    raw_attributes: dict[str, JsonEvidence] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name or self.name != self.name.strip():
            raise ValueError("software inventory item name must be trimmed")
        if self.instance_id is not None and self.instance_id < 0:
            raise ValueError("software inventory instance ID must not be negative")


@dataclass(frozen=True)
class CipSoftwareInventoryTransportResult:
    """Bounded provider result before capture attribution is added."""

    requests_used: int
    items: tuple[CipSoftwareInventoryItem, ...]
    object_evidence: tuple[CipObjectEvidence, ...] = ()

    def __post_init__(self) -> None:
        if isinstance(self.requests_used, bool) or self.requests_used < 0:
            raise ValueError("requests_used must be a non-negative integer")


class CipSoftwareInventoryTransport(Protocol):
    """Injectable structural inventory provider boundary."""

    @property
    def capabilities(self) -> tuple[CipSoftwareInventoryCapability, ...]:
        """Return capabilities supported without performing transport I/O."""
        ...

    def capture_inventory(
        self,
        plan: CipSoftwareInventoryPlan,
        timeout: float,
    ) -> CipSoftwareInventoryTransportResult:
        """Capture only the structural capabilities named by ``plan``."""
        ...


@dataclass(frozen=True)
class CipSoftwareInventoryObservation:
    """Attributable structural software inventory evidence."""

    target: DiscoveryTarget
    captured_at: datetime
    capabilities: tuple[CipSoftwareInventoryCapability, ...]
    requests_used: int
    items: tuple[CipSoftwareInventoryItem, ...]
    object_evidence: tuple[CipObjectEvidence, ...] = ()


class PermittedSoftwareInventoryExecutor:
    """Execute one routed metadata-only plan after fail-closed preflight."""

    def __init__(
        self,
        plan: CipSoftwareInventoryPlan,
        *,
        permit: RoutedExecutionPermit | None,
        transport: CipSoftwareInventoryTransport,
        timeout: float = 2.0,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self._plan = plan
        self._permit = permit
        self._transport = transport
        self._timeout = timeout
        self._executed = False

    def preflight(self) -> None:
        """Validate route, permit, capabilities, and one-shot state without I/O."""
        if self._plan.route is None:
            raise DiscoveryProviderError(
                "cip_software_route_required",
                "software inventory execution currently requires a routed plan",
            )
        validate_routed_execution(
            self._permit,
            self._plan.authorization_reference,
            (self._plan.route.key,),
        )
        supported = set(self._transport.capabilities)
        missing = sorted(
            set(self._plan.capabilities) - supported,
            key=lambda item: item.value,
        )
        if missing:
            names = ", ".join(item.value for item in missing)
            raise DiscoveryProviderError(
                "cip_software_capability_unsupported",
                f"software inventory provider does not support: {names}",
            )
        if self._executed:
            raise DiscoveryProviderError(
                "cip_software_plan_already_executed",
                "software inventory plans may execute only once",
            )

    def capture(self, *, captured_at: datetime) -> CipSoftwareInventoryObservation:
        """Capture structural evidence once and enforce the request budget."""
        if captured_at.tzinfo is None:
            raise ValueError("captured_at must include a timezone")
        self.preflight()
        self._executed = True
        result = self._transport.capture_inventory(self._plan, self._timeout)
        if result.requests_used > self._plan.maximum_requests:
            raise DiscoveryProviderError(
                "cip_software_request_budget_exceeded",
                "software inventory provider exceeded its request budget",
            )
        requested = set(self._plan.capabilities)
        if any(item.capability not in requested for item in result.items):
            raise DiscoveryProviderError(
                "cip_software_unrequested_evidence",
                "provider returned a software capability outside the plan",
            )
        return CipSoftwareInventoryObservation(
            target=self._plan.target,
            captured_at=captured_at,
            capabilities=self._plan.capabilities,
            requests_used=result.requests_used,
            items=tuple(
                sorted(
                    result.items,
                    key=lambda item: (
                        item.capability.value,
                        item.parent or "",
                        item.name,
                    ),
                )
            ),
            object_evidence=result.object_evidence,
        )


def cip_software_inventory_observation_data(
    observation: CipSoftwareInventoryObservation,
) -> dict[str, Any]:
    """Return deterministic structural evidence without runtime values."""
    return {
        "target": observation.target.model_dump(mode="json"),
        "captured_at": observation.captured_at.isoformat(),
        "capabilities": [item.value for item in observation.capabilities],
        "requests_used": observation.requests_used,
        "runtime_values_included": False,
        "items": [
            {
                "capability": item.capability.value,
                "name": item.name,
                "parent": item.parent,
                "instance_id": item.instance_id,
                "data_type": item.data_type,
                "language": item.language,
                "raw_attributes": item.raw_attributes,
            }
            for item in observation.items
        ],
        "object_evidence": [
            {
                "class_code": item.class_code,
                "instance": item.instance,
                "service": item.service,
                "general_status": item.general_status,
                "response_payload_hex": item.response_payload_hex,
                "raw_reply_hex": item.raw_reply_hex,
            }
            for item in observation.object_evidence
        ],
    }


def cip_software_inventory_observation_json(
    observation: CipSoftwareInventoryObservation,
) -> str:
    """Serialize structural inventory evidence deterministically."""
    return json.dumps(
        cip_software_inventory_observation_data(observation),
        indent=2,
        ensure_ascii=False,
    ) + "\n"
