import json
from datetime import datetime, timezone

import pytest

from twinforge.discovery.cip_pycomm3_routed import RoutedExecutionPermit
from twinforge.discovery.cip_routes import CipRouteDeclaration, CipRouteSegment
from twinforge.discovery.contracts import DiscoveryProviderError, DiscoveryTarget
from twinforge.discovery.software_inventory_capture import (
    CipSoftwareInventoryItem,
    CipSoftwareInventoryPage,
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
        pages: dict[str | None, CipSoftwareInventoryPage],
    ) -> None:
        self._capabilities = capabilities
        self.pages = pages
        self.calls: list[str | None] = []

    @property
    def capabilities(self) -> tuple[CipSoftwareInventoryCapability, ...]:
        return self._capabilities

    def read_inventory_page(
        self,
        plan: CipSoftwareInventoryPlan,
        cursor: str | None,
        timeout: float,
    ) -> CipSoftwareInventoryPage:
        self.calls.append(cursor)
        return self.pages[cursor]


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


def test_executor_controls_each_paginated_structural_request() -> None:
    programs = CipSoftwareInventoryCapability.PROGRAMS
    tags = CipSoftwareInventoryCapability.TAG_DEFINITIONS
    capabilities = (programs, tags)
    plan, permit = _fixture(capabilities, maximum_requests=3)
    transport = _Transport(
        capabilities,
        {
            None: CipSoftwareInventoryPage(
                items=(
                    CipSoftwareInventoryItem(programs, "MainProgram"),
                    CipSoftwareInventoryItem(
                        tags,
                        "MotorRun",
                        parent="MainProgram",
                        data_type="BOOL",
                    ),
                ),
                next_cursor="page-2",
            ),
            "page-2": CipSoftwareInventoryPage(items=()),
        },
    )

    observation = PermittedSoftwareInventoryExecutor(
        plan,
        permit=permit,
        transport=transport,
    ).capture(captured_at=TIMESTAMP)
    document = json.loads(cip_software_inventory_observation_json(observation))

    assert transport.calls == [None, "page-2"]
    assert observation.requests_used == 2
    assert document["runtime_values_included"] is False
    assert all("value" not in item for item in document["items"])


def test_unsupported_capability_fails_before_transport() -> None:
    requested = (CipSoftwareInventoryCapability.ROUTINES,)
    plan, permit = _fixture(requested)
    transport = _Transport(
        (CipSoftwareInventoryCapability.PROGRAMS,),
        {},
    )

    with pytest.raises(DiscoveryProviderError, match="does not support"):
        PermittedSoftwareInventoryExecutor(
            plan,
            permit=permit,
            transport=transport,
        ).capture(captured_at=TIMESTAMP)

    assert transport.calls == []


def test_executor_stops_before_request_that_would_exceed_budget() -> None:
    programs = CipSoftwareInventoryCapability.PROGRAMS
    plan, permit = _fixture((programs,), maximum_requests=1)
    transport = _Transport(
        (programs,),
        {
            None: CipSoftwareInventoryPage(
                items=(),
                next_cursor="forbidden-page",
            ),
        },
    )

    with pytest.raises(DiscoveryProviderError, match="budget is exhausted"):
        PermittedSoftwareInventoryExecutor(
            plan,
            permit=permit,
            transport=transport,
        ).capture(captured_at=TIMESTAMP)

    assert transport.calls == [None]


def test_executor_rejects_repeated_cursor_and_wrong_page_capability() -> None:
    programs = CipSoftwareInventoryCapability.PROGRAMS
    tasks = CipSoftwareInventoryCapability.TASKS
    plan, permit = _fixture((programs,))
    repeated = _Transport(
        (programs,),
        {
            None: CipSoftwareInventoryPage(
                items=(), next_cursor="again"
            ),
            "again": CipSoftwareInventoryPage(
                items=(), next_cursor="again"
            ),
        },
    )
    with pytest.raises(DiscoveryProviderError, match="repeated"):
        PermittedSoftwareInventoryExecutor(
            plan,
            permit=permit,
            transport=repeated,
        ).capture(captured_at=TIMESTAMP)

    plan, permit = _fixture((programs,))
    wrong_kind = _Transport(
        (programs,),
        {
            None: CipSoftwareInventoryPage(
                items=(CipSoftwareInventoryItem(tasks, "MainTask"),)
            ),
        },
    )
    with pytest.raises(DiscoveryProviderError, match="requested plan"):
        PermittedSoftwareInventoryExecutor(
            plan,
            permit=permit,
            transport=wrong_kind,
        ).capture(captured_at=TIMESTAMP)
