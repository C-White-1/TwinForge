from datetime import datetime, timezone

import pytest

from twinforge.discovery.chassis import (
    CipChassisSlotRouteMap,
    CipSlotState,
    plan_cip_chassis_slots,
)
from twinforge.discovery.cip_pycomm3 import CipIdentityReply
from twinforge.discovery.cip_pycomm3_chassis import (
    PermittedPycomm3ChassisProvider,
    RoutedSlotOutcome,
    RoutedSlotResult,
)
from twinforge.discovery.cip_pycomm3_routed import RoutedExecutionPermit
from twinforge.discovery.cip_routes import CipRouteDeclaration, CipRouteSegment
from twinforge.discovery.contracts import DiscoveryProviderError, DiscoveryTarget


PAYLOAD = bytes.fromhex(
    "010007000b0003010000d204000009313735362d4942313603"
)
TIMESTAMP = datetime(2026, 8, 9, tzinfo=timezone.utc)


class FakeSlotTransport:
    def __init__(self, results: dict[str, RoutedSlotResult]) -> None:
        self.results = results
        self.calls: list[tuple[str, float]] = []

    def read_slot_identity(
        self,
        route: CipRouteDeclaration,
        timeout: float,
    ) -> RoutedSlotResult:
        self.calls.append((route.key, timeout))
        return self.results[route.key]


def _route(target: DiscoveryTarget, slot: int) -> CipRouteDeclaration:
    return CipRouteDeclaration(
        gateway=target,
        segments=(CipRouteSegment(port=1, link=slot),),
        maximum_depth=1,
    )


def _fixture():
    target = DiscoveryTarget(address="192.168.1.10")
    chassis_route = _route(target, 0)
    plan = plan_cip_chassis_slots(chassis_route, (0, 1, 2, 3, 4))
    routes = tuple((slot, _route(target, slot)) for slot in plan.slots)
    route_map = CipChassisSlotRouteMap(plan=plan, routes=routes)
    permit = RoutedExecutionPermit(
        authorization_reference="LAB-001",
        confirmed_by="operator@example.test",
        confirmed_at=TIMESTAMP,
        allowed_route_keys=tuple(route.key for _, route in routes),
    )
    return plan, route_map, permit


def test_provider_preserves_all_typed_slot_outcomes() -> None:
    plan, route_map, permit = _fixture()
    results = {
        route.key: result
        for (_, route), result in zip(
            route_map.routes,
            (
                RoutedSlotResult(
                    RoutedSlotOutcome.POPULATED,
                    reply=CipIdentityReply(PAYLOAD, b"raw"),
                ),
                RoutedSlotResult(RoutedSlotOutcome.EMPTY, general_status=5),
                RoutedSlotResult(RoutedSlotOutcome.NO_RESPONSE),
                RoutedSlotResult(
                    RoutedSlotOutcome.UNSUPPORTED_ROUTE,
                    general_status=4,
                ),
                RoutedSlotResult(
                    RoutedSlotOutcome.DEVICE_FAULT,
                    general_status=1,
                    additional_status=(513,),
                    raw_attributes={"vendor_status": 513},
                ),
            ),
            strict=True,
        )
    }
    transport = FakeSlotTransport(results)
    provider = PermittedPycomm3ChassisProvider(
        route_map,
        authorization_reference="LAB-001",
        permit=permit,
        timeout=3.0,
        transport=transport,
    )

    observation = provider.read_chassis(plan, captured_at=TIMESTAMP)

    assert [item.state for item in observation.slots] == list(CipSlotState)
    assert observation.slots[0].identity is not None
    assert observation.slots[0].identity.product_name == "1756-IB16"
    assert observation.slots[4].additional_status == (513,)
    assert observation.slots[4].raw_attributes["vendor_status"] == 513
    assert transport.calls == [
        (route.key, 3.0) for _, route in route_map.routes
    ]


def test_provider_refuses_without_permit_before_first_slot() -> None:
    plan, route_map, _ = _fixture()
    transport = FakeSlotTransport({})
    provider = PermittedPycomm3ChassisProvider(
        route_map,
        authorization_reference="LAB-001",
        transport=transport,
    )

    with pytest.raises(DiscoveryProviderError, match="operator permit"):
        provider.read_chassis(plan, captured_at=TIMESTAMP)

    assert transport.calls == []


def test_provider_preflights_every_slot_route_in_permit() -> None:
    plan, route_map, permit = _fixture()
    incomplete = RoutedExecutionPermit(
        authorization_reference=permit.authorization_reference,
        confirmed_by=permit.confirmed_by,
        confirmed_at=permit.confirmed_at,
        allowed_route_keys=permit.allowed_route_keys[:-1],
    )
    transport = FakeSlotTransport({})
    provider = PermittedPycomm3ChassisProvider(
        route_map,
        authorization_reference="LAB-001",
        permit=incomplete,
        transport=transport,
    )

    with pytest.raises(DiscoveryProviderError, match="absent.*permit"):
        provider.read_chassis(plan, captured_at=TIMESTAMP)

    assert transport.calls == []


def test_provider_enforces_whole_plan_budget() -> None:
    plan, route_map, permit = _fixture()
    results = {
        route.key: RoutedSlotResult(RoutedSlotOutcome.EMPTY)
        for _, route in route_map.routes
    }
    transport = FakeSlotTransport(results)
    provider = PermittedPycomm3ChassisProvider(
        route_map,
        authorization_reference="LAB-001",
        permit=permit,
        transport=transport,
    )

    provider.read_chassis(plan, captured_at=TIMESTAMP)
    with pytest.raises(DiscoveryProviderError, match="budget"):
        provider.read_chassis(plan, captured_at=TIMESTAMP)

    assert len(transport.calls) == len(plan.slots)
