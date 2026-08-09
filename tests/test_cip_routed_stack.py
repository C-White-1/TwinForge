from typing import ClassVar
from datetime import datetime, timezone
import json

import pytest

from twinforge.discovery.chassis import (
    CipChassisSlotRouteMap,
    CipSlotState,
    plan_cip_chassis_slots,
)
from twinforge.discovery.cip_pycomm3_chassis import (
    PermittedPycomm3ChassisProvider,
    RoutedSlotOutcome,
)
from twinforge.discovery.cip_pycomm3_routed import RoutedExecutionPermit
from twinforge.discovery.cip_pycomm3_slots import (
    CipSlotStatusProfile,
    CipSlotStatusSignature,
    LivePycomm3RoutedSlotTransport,
)
from twinforge.discovery.cip_routes import CipRouteDeclaration, CipRouteSegment
from twinforge.discovery.contracts import DiscoveryTarget
from twinforge.discovery.routed_capture import (
    CipRoutedCapturePlan,
    RoutedCipProviderFacade,
    capture_routed_cip,
    cip_routed_snapshot_json,
)


TIMESTAMP = datetime(2026, 8, 9, tzinfo=timezone.utc)
IDENTITY_PAYLOAD = bytes.fromhex(
    "010007000b0003010000d204000009313735362d4942313603"
)


def _packet(
    status: int,
    payload: bytes = b"",
    additional_status: tuple[int, ...] = (),
) -> bytes:
    raw = bytearray(44)
    raw[42] = status
    raw[43] = len(additional_status)
    for value in additional_status:
        raw.extend(value.to_bytes(2, "little"))
    raw.extend(payload)
    return bytes(raw)


class _Packet:
    def __init__(self, raw: bytes) -> None:
        self.raw = raw


class _Tag:
    def __init__(self, raw: bytes, error: str | None = None) -> None:
        self.value = _Packet(raw)
        self.error = error


class _RoutingDriver:
    calls: ClassVar[list[bytes]] = []
    responses: ClassVar[dict[bytes, _Tag]] = {}

    def __init__(self, address: str) -> None:
        self.address = address
        self.socket_timeout = 0.0

    def open(self) -> bool:
        return True

    def generic_message(self, **kwargs: object) -> _Tag:
        path = kwargs["route_path"]
        assert isinstance(path, bytes)
        self.__class__.calls.append(path)
        return self.__class__.responses[path]

    def close(self) -> None:
        pass


def _route(target: DiscoveryTarget, slot: int) -> CipRouteDeclaration:
    return CipRouteDeclaration(
        gateway=target,
        segments=(CipRouteSegment(port=1, link=slot),),
        maximum_depth=1,
    )


def test_packet_fixture_flows_through_complete_routed_chassis_stack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = DiscoveryTarget(address="192.168.1.10", label="lab gateway")
    chassis_route = _route(target, 0)
    chassis_plan = plan_cip_chassis_slots(chassis_route, (0, 1))
    slot_routes = (_route(target, 0), _route(target, 1))
    route_map = CipChassisSlotRouteMap(
        plan=chassis_plan,
        routes=((0, slot_routes[0]), (1, slot_routes[1])),
    )
    permit = RoutedExecutionPermit(
        authorization_reference="LAB-001",
        confirmed_by="operator@example.test",
        confirmed_at=TIMESTAMP,
        allowed_route_keys=tuple(route.key for route in slot_routes),
    )
    profile = CipSlotStatusProfile(
        name="authorized-fixture-v1",
        signatures=(
            CipSlotStatusSignature(
                general_status=5,
                additional_status=(0x0204,),
                outcome=RoutedSlotOutcome.EMPTY,
                source_reference="TEST-FIXTURE-EMPTY-SLOT",
            ),
        ),
    )
    _RoutingDriver.calls = []
    _RoutingDriver.responses = {
        b"\x01\x00\x01\x00": _Tag(_packet(0, IDENTITY_PAYLOAD)),
        b"\x01\x00\x01\x01": _Tag(
            _packet(5, additional_status=(0x0204,)),
            "fixture empty slot",
        ),
    }
    monkeypatch.setattr(
        "twinforge.discovery.cip_pycomm3_slots.CIPDriver",
        _RoutingDriver,
    )
    chassis_provider = PermittedPycomm3ChassisProvider(
        route_map,
        authorization_reference="LAB-001",
        permit=permit,
        transport=LivePycomm3RoutedSlotTransport(profile),
    )
    facade = RoutedCipProviderFacade(
        authorization_reference="LAB-001",
        chassis_provider=chassis_provider,
    )
    capture_plan = CipRoutedCapturePlan(
        engagement="controlled lab fixture",
        authorization_reference="LAB-001",
        chassis=(chassis_plan,),
    )

    snapshot = capture_routed_cip(
        capture_plan,
        facade,
        captured_at=TIMESTAMP,
    )
    document = json.loads(cip_routed_snapshot_json(snapshot))

    assert _RoutingDriver.calls == [
        b"\x01\x00\x01\x00",
        b"\x01\x00\x01\x01",
    ]
    assert snapshot.diagnostics == ()
    assert [item.state for item in snapshot.chassis[0].slots] == [
        CipSlotState.POPULATED,
        CipSlotState.EMPTY,
    ]
    assert snapshot.chassis[0].slots[0].identity is not None
    assert snapshot.chassis[0].slots[0].identity.product_name == "1756-IB16"
    assert document["plan"]["total_request_budget"] == 2
    assert document["chassis"][0]["slots"][1]["raw_attributes"] == {
        "classification_matched": True,
        "classification_source": "TEST-FIXTURE-EMPTY-SLOT",
        "profile": "authorized-fixture-v1",
        "route_key": slot_routes[1].key,
    }
