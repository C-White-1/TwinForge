import json
from datetime import datetime, timezone
from typing import ClassVar

import pytest

from twinforge.discovery.cip_pycomm3_routed import (
    LivePycomm3RoutedTransport,
    PermittedPycomm3RoutedControllerProvider,
    RoutedExecutionPermit,
)
from twinforge.discovery.cip_routes import CipRouteDeclaration, CipRouteSegment
from twinforge.discovery.contracts import DiscoveryTarget
from twinforge.discovery.controller_enrichment import (
    MetadataEnrichedControllerProvider,
)
from twinforge.discovery.controller_metadata import (
    CipControllerMetadataPlan,
    CipControllerMetadataRequest,
    CipMetadataNamespace,
    CipMetadataReadService,
    ControllerMetadataField,
)
from twinforge.discovery.controller_metadata_capture import (
    PermittedControllerMetadataExecutor,
)
from twinforge.discovery.controller_metadata_pycomm3 import (
    LivePycomm3MetadataTransport,
    standard_metadata_decoders,
)
from twinforge.discovery.routed_capture import (
    CipControllerReadPlan,
    CipRoutedCapturePlan,
    RoutedCipProviderFacade,
    capture_routed_cip,
    cip_routed_snapshot_json,
)


TIMESTAMP = datetime(2026, 8, 9, tzinfo=timezone.utc)
IDENTITY_PAYLOAD = bytes.fromhex(
    "01000e00a60023116000785634120a436f6e74726f6c6c657203"
)


def _packet(payload: bytes) -> bytes:
    raw = bytearray(44)
    raw.extend(payload)
    return bytes(raw)


class _Packet:
    def __init__(self, raw: bytes, payload: bytes) -> None:
        self.raw = raw
        self.value = payload


class _Tag:
    def __init__(self, raw: bytes, payload: bytes) -> None:
        self.value = _Packet(raw, payload)
        self.error = None

    def __bool__(self) -> bool:
        return True


class _ControllerDriver:
    calls: ClassVar[list[dict[str, object]]] = []

    def __init__(self, address: str) -> None:
        self.address = address
        self.socket_timeout = 0.0

    def open(self) -> bool:
        return True

    def generic_message(self, **kwargs: object) -> _Tag:
        self.__class__.calls.append(kwargs)
        return _Tag(_packet(IDENTITY_PAYLOAD), IDENTITY_PAYLOAD)

    def close(self) -> None:
        pass


def test_packet_fixture_flows_through_enriched_controller_stack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = DiscoveryTarget(address="192.168.1.10", label="lab gateway")
    route = CipRouteDeclaration(
        gateway=target,
        segments=(CipRouteSegment(port=1, link=0),),
        maximum_depth=1,
    )
    permit = RoutedExecutionPermit(
        authorization_reference="LAB-001",
        confirmed_by="operator@example.test",
        confirmed_at=TIMESTAMP,
        allowed_route_keys=(route.key,),
    )
    metadata_plan = CipControllerMetadataPlan(
        target=target,
        route=route,
        authorization_reference="LAB-001",
        requests=(
            CipControllerMetadataRequest(
                name="Identity object firmware revision",
                service=CipMetadataReadService.GET_ATTRIBUTES_ALL,
                class_code=1,
                instance=1,
                namespace=CipMetadataNamespace.STANDARD_CIP,
                specification_reference="ODVA CIP Identity Object",
                semantic_field=ControllerMetadataField.FIRMWARE_REVISION,
                decoder="cip_identity_firmware_revision",
            ),
        ),
    )
    identity_provider = PermittedPycomm3RoutedControllerProvider(
        (route,),
        authorization_reference="LAB-001",
        permit=permit,
        transport=LivePycomm3RoutedTransport(),
    )
    metadata_executor = PermittedControllerMetadataExecutor(
        metadata_plan,
        permit=permit,
        transport=LivePycomm3MetadataTransport(),
        decoders=standard_metadata_decoders(),
    )
    provider = MetadataEnrichedControllerProvider(
        identity_provider,
        metadata_executor,
    )
    facade = RoutedCipProviderFacade(
        authorization_reference="LAB-001",
        controller_provider=provider,
    )
    capture_plan = CipRoutedCapturePlan(
        engagement="controlled lab fixture",
        authorization_reference="LAB-001",
        controllers=(
            CipControllerReadPlan(
                target=target,
                route=route,
                metadata=metadata_plan,
            ),
        ),
    )
    _ControllerDriver.calls = []
    monkeypatch.setattr(
        "twinforge.discovery.cip_pycomm3_routed.CIPDriver",
        _ControllerDriver,
    )
    monkeypatch.setattr(
        "twinforge.discovery.controller_metadata_pycomm3.CIPDriver",
        _ControllerDriver,
    )

    snapshot = capture_routed_cip(
        capture_plan,
        facade,
        captured_at=TIMESTAMP,
    )
    document = json.loads(cip_routed_snapshot_json(snapshot))

    assert len(_ControllerDriver.calls) == 2
    assert all(
        call["route_path"] == b"\x01\x00\x01\x00"
        for call in _ControllerDriver.calls
    )
    assert snapshot.diagnostics == ()
    assert snapshot.controllers[0].identity.product_name == "Controller"
    assert snapshot.controllers[0].firmware_revision == "35.17"
    assert len(snapshot.controllers[0].object_evidence) == 1
    assert document["plan"]["total_request_budget"] == 2
    controller_plan = document["plan"]["controllers"][0]
    assert controller_plan["request_budget"] == 1
    assert controller_plan["total_request_budget"] == 2
    assert controller_plan["metadata"]["total_request_budget"] == 1
