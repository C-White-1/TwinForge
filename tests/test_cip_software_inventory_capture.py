import json
from datetime import datetime, timezone

import pytest

from twinforge.discovery.cip_pycomm3_routed import RoutedExecutionPermit
from twinforge.discovery.cip_routes import CipRouteDeclaration, CipRouteSegment
from twinforge.discovery.contracts import DiscoveryProviderError, DiscoveryTarget
from twinforge.discovery.software_inventory_capture import (
    CipSoftwareInventoryItem,
    CipSoftwareInventoryTransportResult,
    PermittedSoftwareInventoryExecutor,
    cip_software_inventory_observation_json,
)
from twinforge.discovery.software_inventory_plan import (
    CipSoftwareInventoryCapability,
    CipSoftwareInventoryPlan,
)


TIMESTAMP = datetime(2026, 8, 9, tzinfo=timezone.utc)


class _Transport:
    def __init__(
        self,
        capabilities: tuple[CipSoftwareInventoryCapability, ...],
        result: CipSoftwareInventoryTransportResult,
    ) -> None:
        self._capabilities = capabilities
        self.result = result
        self.calls = 0

    @property
    def capabilities(self) -> tuple[CipSoftwareInventoryCapability, ...]:
        return self._capabilities

    def capture_inventory(
        self,
        plan: CipSoftwareInventoryPlan,
        timeout: float,
    ) -> CipSoftwareInventoryTransportResult:
        self.calls += 1
        return self.result


def _fixture(
    capabilities: tuple[CipSoftwareInventoryCapability, ...],
    maximum_requests: int = 4,
) -> tuple[CipSoftwareInventoryPlan, RoutedExecutionPermit]:
    target = DiscoveryTarget(address="192.168.1.10")
    route = CipRouteDeclaration(
        gateway=target,
        segments=(CipRouteSegment(port=1, link=0),),
        maximum_depth=1,
    )
    return (
        CipSoftwareInventoryPlan(
            target=target,
            route=route,
            authorization_reference="LAB-001",
            capabilities=capabilities,
            maximum_requests=maximum_requests,
        ),
        RoutedExecutionPermit(
            authorization_reference="LAB-001",
            confirmed_by="operator@example.test",
            confirmed_at=TIMESTAMP,
            allowed_route_keys=(route.key,),
        ),
    )


def test_executor_captures_only_requested_structural_items() -> None:
    capabilities = (
        CipSoftwareInventoryCapability.PROGRAMS,
        CipSoftwareInventoryCapability.TAG_DEFINITIONS,
    )
    plan, permit = _fixture(capabilities)
    transport = _Transport(
        capabilities,
        CipSoftwareInventoryTransportResult(
            requests_used=2,
            items=(
                CipSoftwareInventoryItem(
                    capability=CipSoftwareInventoryCapability.TAG_DEFINITIONS,
                    name="MotorRun",
                    parent="MainProgram",
                    data_type="BOOL",
                ),
                CipSoftwareInventoryItem(
                    capability=CipSoftwareInventoryCapability.PROGRAMS,
                    name="MainProgram",
                ),
            ),
        ),
    )
    executor = PermittedSoftwareInventoryExecutor(
        plan,
        permit=permit,
        transport=transport,
    )

    observation = executor.capture(captured_at=TIMESTAMP)
    document = json.loads(cip_software_inventory_observation_json(observation))

    assert transport.calls == 1
    assert document["runtime_values_included"] is False
    assert "value" not in document["items"][1]


def test_unsupported_capability_fails_before_transport() -> None:
    requested = (CipSoftwareInventoryCapability.ROUTINES,)
    plan, permit = _fixture(requested)
    transport = _Transport(
        (CipSoftwareInventoryCapability.PROGRAMS,),
        CipSoftwareInventoryTransportResult(requests_used=0, items=()),
    )
    executor = PermittedSoftwareInventoryExecutor(
        plan,
        permit=permit,
        transport=transport,
    )

    with pytest.raises(DiscoveryProviderError, match="does not support"):
        executor.capture(captured_at=TIMESTAMP)

    assert transport.calls == 0


def test_executor_rejects_budget_overrun_and_unrequested_items() -> None:
    requested = (CipSoftwareInventoryCapability.PROGRAMS,)
    plan, permit = _fixture(requested, maximum_requests=1)
    overrun = _Transport(
        requested,
        CipSoftwareInventoryTransportResult(requests_used=2, items=()),
    )
    with pytest.raises(DiscoveryProviderError, match="exceeded"):
        PermittedSoftwareInventoryExecutor(
            plan,
            permit=permit,
            transport=overrun,
        ).capture(captured_at=TIMESTAMP)

    plan, permit = _fixture(requested)
    outside_plan = _Transport(
        requested,
        CipSoftwareInventoryTransportResult(
            requests_used=1,
            items=(
                CipSoftwareInventoryItem(
                    capability=CipSoftwareInventoryCapability.TASKS,
                    name="MainTask",
                ),
            ),
        ),
    )
    with pytest.raises(DiscoveryProviderError, match="outside the plan"):
        PermittedSoftwareInventoryExecutor(
            plan,
            permit=permit,
            transport=outside_plan,
        ).capture(captured_at=TIMESTAMP)
