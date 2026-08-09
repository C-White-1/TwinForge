from datetime import datetime, timezone

import pytest

from twinforge.discovery.cip_pycomm3 import CipIdentityReply
from twinforge.discovery.cip_pycomm3_routed import (
    LivePycomm3RoutedTransport,
    PermittedPycomm3RoutedControllerProvider,
    RoutedExecutionPermit,
)
from twinforge.discovery.cip_routes import CipRouteDeclaration, CipRouteSegment
from twinforge.discovery.contracts import DiscoveryProviderError, DiscoveryTarget


PAYLOAD = bytes.fromhex(
    "01000e00a60023116000785634120a436f6e74726f6c6c657203"
)
TIMESTAMP = datetime(2026, 8, 9, tzinfo=timezone.utc)


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, bytes, float]] = []

    def read_identity(
        self,
        address: str,
        route_path: bytes,
        timeout: float,
    ) -> CipIdentityReply:
        self.calls.append((address, route_path, timeout))
        return CipIdentityReply(PAYLOAD, b"raw-routed-reply")


class _FakePacket:
    value = PAYLOAD
    raw = b"raw-live-routed"


class _FakeTag:
    value = _FakePacket()
    error = None

    def __bool__(self) -> bool:
        return True


class _FakeDriver:
    last_call: dict[str, object] = {}

    def __init__(self, address: str) -> None:
        self.address = address
        self.socket_timeout = 0.0

    def open(self) -> bool:
        return True

    def generic_message(self, **kwargs: object) -> _FakeTag:
        self.__class__.last_call = kwargs
        return _FakeTag()

    def close(self) -> None:
        pass


def test_live_routed_transport_uses_ucmm_and_extracts_packet_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "twinforge.discovery.cip_pycomm3_routed.CIPDriver",
        _FakeDriver,
    )
    path = b"\x01\x00\x01\x00"

    reply = LivePycomm3RoutedTransport().read_identity(
        "192.168.1.10",
        path,
        2.0,
    )

    assert reply.payload == PAYLOAD
    assert reply.raw_reply == b"raw-live-routed"
    assert _FakeDriver.last_call["connected"] is False
    assert _FakeDriver.last_call["unconnected_send"] is True
    assert _FakeDriver.last_call["route_path"] == path


def _target_and_route() -> tuple[DiscoveryTarget, CipRouteDeclaration]:
    target = DiscoveryTarget(address="192.168.1.10")
    route = CipRouteDeclaration(
        gateway=target,
        segments=(CipRouteSegment(port=1, link=0),),
        maximum_depth=1,
    )
    return target, route


def _permit(route: CipRouteDeclaration) -> RoutedExecutionPermit:
    return RoutedExecutionPermit(
        authorization_reference="LAB-001",
        confirmed_by="operator@example.test",
        confirmed_at=TIMESTAMP,
        allowed_route_keys=(route.key,),
    )


def test_default_provider_refuses_before_transport_is_called() -> None:
    target, route = _target_and_route()
    transport = FakeTransport()
    provider = PermittedPycomm3RoutedControllerProvider(
        (route,),
        authorization_reference="LAB-001",
        transport=transport,
    )

    with pytest.raises(DiscoveryProviderError, match="operator permit"):
        provider.read_controller(target, route=route, captured_at=TIMESTAMP)

    assert transport.calls == []


def test_permitted_provider_uses_exact_unconnected_route_bytes_once() -> None:
    target, route = _target_and_route()
    transport = FakeTransport()
    provider = PermittedPycomm3RoutedControllerProvider(
        (route,),
        authorization_reference="LAB-001",
        permit=_permit(route),
        timeout=3.0,
        transport=transport,
    )

    observation = provider.read_controller(
        target,
        route=route,
        captured_at=TIMESTAMP,
    )

    assert transport.calls == [("192.168.1.10", b"\x01\x00\x01\x00", 3.0)]
    assert observation.identity.product_name == "Controller"
    assert observation.identity.raw_attributes["route_key"] == route.key
    assert observation.identity.raw_attributes["encoded_route_path_hex"] == (
        "01000100"
    )
    assert observation.identity.raw_attributes["raw_reply_hex"] == (
        b"raw-routed-reply".hex()
    )

    with pytest.raises(DiscoveryProviderError, match="budget"):
        provider.read_controller(target, route=route, captured_at=TIMESTAMP)

    assert len(transport.calls) == 1


def test_allowlisted_route_must_also_be_present_in_permit() -> None:
    target, route = _target_and_route()
    other = CipRouteDeclaration(
        gateway=target,
        segments=(CipRouteSegment(port=1, link=1),),
        maximum_depth=1,
    )
    transport = FakeTransport()
    provider = PermittedPycomm3RoutedControllerProvider(
        (route,),
        authorization_reference="LAB-001",
        permit=_permit(other),
        transport=transport,
    )

    with pytest.raises(DiscoveryProviderError, match="absent.*permit"):
        provider.read_controller(target, route=route, captured_at=TIMESTAMP)

    assert transport.calls == []


def test_route_outside_provider_allowlist_is_rejected() -> None:
    target, route = _target_and_route()
    other = CipRouteDeclaration(
        gateway=target,
        segments=(CipRouteSegment(port=1, link=1),),
        maximum_depth=1,
    )
    transport = FakeTransport()
    provider = PermittedPycomm3RoutedControllerProvider(
        (route,),
        authorization_reference="LAB-001",
        permit=_permit(route),
        transport=transport,
    )

    with pytest.raises(DiscoveryProviderError, match="outside.*allowlist"):
        provider.read_controller(target, route=other, captured_at=TIMESTAMP)

    assert transport.calls == []


def test_permit_must_match_provider_authorization_reference() -> None:
    target, route = _target_and_route()
    transport = FakeTransport()
    provider = PermittedPycomm3RoutedControllerProvider(
        (route,),
        authorization_reference="LAB-002",
        permit=_permit(route),
        transport=transport,
    )

    with pytest.raises(DiscoveryProviderError, match="authorization"):
        provider.read_controller(target, route=route, captured_at=TIMESTAMP)

    assert transport.calls == []
