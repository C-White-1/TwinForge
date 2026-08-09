import json
from datetime import datetime, timezone

import pytest

from twinforge.discovery.cip_pycomm3_routed import RoutedExecutionPermit
from twinforge.discovery.cip_routes import CipRouteDeclaration, CipRouteSegment
from twinforge.discovery.contracts import (
    CipIdentityObservation,
    DiscoveryProviderError,
    DiscoveryTarget,
)
from twinforge.discovery.controller import CipControllerObservation
from twinforge.discovery.controller_metadata import (
    CipControllerMetadataPlan,
    CipControllerMetadataRequest,
    CipMetadataNamespace,
    CipMetadataReadService,
    ControllerMetadataField,
)
from twinforge.discovery.controller_metadata_capture import (
    CipMetadataTransportResult,
    PermittedControllerMetadataExecutor,
    apply_controller_metadata,
    cip_controller_metadata_capture_json,
)


TIMESTAMP = datetime(2026, 8, 9, tzinfo=timezone.utc)


class FakeMetadataTransport:
    def __init__(self, results: dict[str, CipMetadataTransportResult]) -> None:
        self.results = results
        self.calls: list[tuple[str, str, float]] = []

    def read_metadata(
        self,
        target: DiscoveryTarget,
        route: CipRouteDeclaration,
        request: CipControllerMetadataRequest,
        timeout: float,
    ) -> CipMetadataTransportResult:
        self.calls.append((target.key, request.key, timeout))
        assert route.gateway == target
        return self.results[request.key]


def _fixture():
    target = DiscoveryTarget(address="192.168.1.10")
    route = CipRouteDeclaration(
        gateway=target,
        segments=(CipRouteSegment(port=1, link=0),),
        maximum_depth=1,
    )
    name_request = CipControllerMetadataRequest(
        name="controller name",
        service=CipMetadataReadService.GET_ATTRIBUTE_SINGLE,
        class_code=0x64,
        instance=1,
        attribute=1,
        namespace=CipMetadataNamespace.VENDOR_SPECIFIC,
        vendor_id=1,
        specification_reference="authorized fixture",
        semantic_field=ControllerMetadataField.LOGICAL_NAME,
        decoder="utf8_text",
    )
    failed_request = CipControllerMetadataRequest(
        name="project revision",
        service=CipMetadataReadService.GET_ATTRIBUTE_SINGLE,
        class_code=0x64,
        instance=1,
        attribute=2,
        namespace=CipMetadataNamespace.VENDOR_SPECIFIC,
        vendor_id=1,
        specification_reference="authorized fixture",
        semantic_field=ControllerMetadataField.PROJECT_REVISION,
    )
    plan = CipControllerMetadataPlan(
        target=target,
        route=route,
        authorization_reference="LAB-001",
        requests=(name_request, failed_request),
    )
    permit = RoutedExecutionPermit(
        authorization_reference="LAB-001",
        confirmed_by="operator@example.test",
        confirmed_at=TIMESTAMP,
        allowed_route_keys=(route.key,),
    )
    return target, route, name_request, failed_request, plan, permit


def _controller(
    target: DiscoveryTarget,
    route: CipRouteDeclaration,
) -> CipControllerObservation:
    identity = CipIdentityObservation(
        target=target,
        captured_at=TIMESTAMP,
        vendor_id=1,
        device_type=14,
        product_code=166,
        major_revision=35,
        minor_revision=17,
        status=0,
        serial_number=1234,
        product_name="Controller",
    )
    return CipControllerObservation(
        target=target,
        route=route,
        captured_at=TIMESTAMP,
        identity=identity,
    )


def test_executor_decodes_registered_field_and_preserves_failed_read() -> None:
    target, route, name_request, failed_request, plan, permit = _fixture()
    transport = FakeMetadataTransport(
        {
            name_request.key: CipMetadataTransportResult(
                general_status=0,
                response_payload=b"LabController",
                raw_reply=b"raw-name",
            ),
            failed_request.key: CipMetadataTransportResult(
                general_status=5,
                additional_status=(516,),
                response_payload=b"\x99\x88",
                raw_reply=b"raw-failure",
                message="path destination unknown",
            ),
        }
    )
    executor = PermittedControllerMetadataExecutor(
        plan,
        permit=permit,
        transport=transport,
        decoders={"utf8_text": lambda payload: payload.decode("utf-8")},
        timeout=3.0,
    )

    capture = executor.capture(captured_at=TIMESTAMP)
    merged = apply_controller_metadata(_controller(target, route), capture)
    document = json.loads(cip_controller_metadata_capture_json(capture))

    assert capture.values == {
        ControllerMetadataField.LOGICAL_NAME: "LabController"
    }
    assert merged.logical_name == "LabController"
    assert merged.project_revision is None
    assert len(merged.object_evidence) == 2
    assert document["object_evidence"][1]["general_status"] == 5
    assert document["object_evidence"][1]["additional_status"] == [516]
    assert document["object_evidence"][1]["response_payload_hex"] == "9988"
    assert document["object_evidence"][1]["raw_reply_hex"] == (
        b"raw-failure".hex()
    )
    assert document["object_evidence"][1]["message"] == (
        "path destination unknown"
    )
    assert len(transport.calls) == plan.total_request_budget


def test_executor_preflights_permit_and_decoders_before_transport() -> None:
    _, _, _, _, plan, _ = _fixture()
    transport = FakeMetadataTransport({})
    without_permit = PermittedControllerMetadataExecutor(
        plan,
        permit=None,
        transport=transport,
        decoders={"utf8_text": lambda payload: payload.decode()},
    )

    with pytest.raises(DiscoveryProviderError, match="operator permit"):
        without_permit.capture(captured_at=TIMESTAMP)
    assert transport.calls == []

    _, _, _, _, plan, permit = _fixture()
    missing_decoder = PermittedControllerMetadataExecutor(
        plan,
        permit=permit,
        transport=transport,
    )
    with pytest.raises(DiscoveryProviderError, match="unregistered decoders"):
        missing_decoder.capture(captured_at=TIMESTAMP)
    assert transport.calls == []


def test_executor_enforces_whole_plan_budget() -> None:
    _, _, name_request, failed_request, plan, permit = _fixture()
    transport = FakeMetadataTransport(
        {
            name_request.key: CipMetadataTransportResult(0, b"name"),
            failed_request.key: CipMetadataTransportResult(1, b""),
        }
    )
    executor = PermittedControllerMetadataExecutor(
        plan,
        permit=permit,
        transport=transport,
        decoders={"utf8_text": lambda payload: payload.decode()},
    )

    executor.capture(captured_at=TIMESTAMP)
    with pytest.raises(DiscoveryProviderError, match="budget"):
        executor.capture(captured_at=TIMESTAMP)

    assert len(transport.calls) == plan.total_request_budget


def test_plan_rejects_two_requests_for_same_semantic_field() -> None:
    target, route, name_request, _, _, _ = _fixture()
    duplicate_field = CipControllerMetadataRequest(
        name="other name source",
        service=CipMetadataReadService.GET_ATTRIBUTE_SINGLE,
        class_code=0x65,
        instance=1,
        attribute=1,
        namespace=CipMetadataNamespace.VENDOR_SPECIFIC,
        vendor_id=1,
        specification_reference="authorized fixture",
        semantic_field=ControllerMetadataField.LOGICAL_NAME,
    )

    with pytest.raises(ValueError, match="semantic fields"):
        CipControllerMetadataPlan(
            target=target,
            route=route,
            authorization_reference="LAB-001",
            requests=(name_request, duplicate_field),
        )
