from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from twinforge.discovery.cip_infrastructure_capture import (
    CipInfrastructureTransportResult,
    PermittedCipInfrastructureExecutor,
    cip_infrastructure_capture_json,
)
from twinforge.discovery.cip_infrastructure_plan import (
    CipInfrastructureDiscoveryPlan,
    CipInfrastructureObject,
    CipInfrastructureReadRequest,
)
from twinforge.discovery.cip_pycomm3_routed import RoutedExecutionPermit
from twinforge.discovery.cip_routes import CipRouteDeclaration, CipRouteSegment
from twinforge.discovery.contracts import DiscoveryProviderError, DiscoveryTarget
from twinforge.discovery.controller_metadata import CipMetadataReadService


NOW = datetime(2026, 8, 13, tzinfo=timezone.utc)


class FakeTransport:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def read_infrastructure(self, target, route, request, timeout):
        self.calls.append((target.key, route.key, request.key, timeout))
        return self.results[request.key]


def _fixture():
    target = DiscoveryTarget(address="192.168.1.20")
    route = CipRouteDeclaration(
        gateway=target,
        segments=(CipRouteSegment(port=1, link=3),),
        maximum_depth=1,
    )
    assembly = CipInfrastructureReadRequest(
        object_type=CipInfrastructureObject.ASSEMBLY,
        instance=101,
        attribute=3,
        service=CipMetadataReadService.GET_ATTRIBUTE_SINGLE,
        specification_reference="EDS Assembly 101",
    )
    manager = CipInfrastructureReadRequest(
        object_type=CipInfrastructureObject.CONNECTION_MANAGER,
        instance=1,
        service=CipMetadataReadService.GET_ATTRIBUTES_ALL,
        specification_reference="CIP Networks Library volume 1",
    )
    plan = CipInfrastructureDiscoveryPlan(
        target=target,
        route=route,
        engagement="authorized-lab",
        authorization_reference="LAB-22",
        requests=(manager, assembly),
        maximum_requests=2,
    )
    permit = RoutedExecutionPermit(
        authorization_reference="LAB-22",
        confirmed_by="engineer@example.test",
        confirmed_at=NOW,
        allowed_route_keys=(route.key,),
    )
    return assembly, manager, plan, permit


def test_capture_preserves_success_and_failure_bytes_and_status() -> None:
    assembly, manager, plan, permit = _fixture()
    transport = FakeTransport(
        {
            assembly.key: CipInfrastructureTransportResult(
                0, b"\x01\x02\x03\x04", raw_reply=b"assembly-raw"
            ),
            manager.key: CipInfrastructureTransportResult(
                5,
                b"\xaa\xbb",
                additional_status=(513,),
                raw_reply=b"manager-raw",
                message="path destination unknown",
            ),
        }
    )
    executor = PermittedCipInfrastructureExecutor(
        plan, permit=permit, transport=transport, timeout=3.0
    )

    document = json.loads(
        cip_infrastructure_capture_json(executor.capture(captured_at=NOW))
    )

    assert len(transport.calls) == 2
    assert document["object_evidence"][0]["class_code"] == 4
    assert document["object_evidence"][0]["response_payload_hex"] == "01020304"
    assert document["object_evidence"][0]["decoded"] == {}
    assert document["object_evidence"][1]["class_code"] == 6
    assert document["object_evidence"][1]["general_status"] == 5
    assert document["object_evidence"][1]["additional_status"] == [513]
    assert document["object_evidence"][1]["response_payload_hex"] == "aabb"
    assert document["object_evidence"][1]["message"] == "path destination unknown"


def test_preflight_refuses_missing_permit_without_transport_calls() -> None:
    _, _, plan, _ = _fixture()
    transport = FakeTransport({})
    executor = PermittedCipInfrastructureExecutor(
        plan, permit=None, transport=transport
    )

    with pytest.raises(DiscoveryProviderError, match="operator permit"):
        executor.capture(captured_at=NOW)

    assert transport.calls == []


def test_executor_enforces_one_shot_plan_budget() -> None:
    assembly, manager, plan, permit = _fixture()
    transport = FakeTransport(
        {
            assembly.key: CipInfrastructureTransportResult(0, b""),
            manager.key: CipInfrastructureTransportResult(0, b""),
        }
    )
    executor = PermittedCipInfrastructureExecutor(
        plan, permit=permit, transport=transport
    )

    executor.capture(captured_at=NOW)
    with pytest.raises(DiscoveryProviderError, match="budget"):
        executor.capture(captured_at=NOW)

    assert len(transport.calls) == 2
