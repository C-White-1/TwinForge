from __future__ import annotations

from typing import ClassVar

import pytest

from twinforge.discovery.cip_infrastructure_plan import (
    CipInfrastructureObject,
    CipInfrastructureReadRequest,
)
from twinforge.discovery.cip_infrastructure_pycomm3 import (
    LivePycomm3InfrastructureTransport,
)
from twinforge.discovery.cip_routes import CipRouteDeclaration, CipRouteSegment
from twinforge.discovery.contracts import DiscoveryProviderError, DiscoveryTarget
from twinforge.discovery.controller_metadata import CipMetadataReadService


def _packet(
    status: int,
    payload: bytes,
    additional_status: tuple[int, ...] = (),
) -> bytes:
    raw = bytearray(44)
    raw[42] = status
    raw[43] = len(additional_status)
    for value in additional_status:
        raw.extend(value.to_bytes(2, "little"))
    raw.extend(payload)
    return bytes(raw)


class _FakePacket:
    def __init__(self, raw: bytes) -> None:
        self.raw = raw


class _FakeTag:
    def __init__(self, raw: bytes, error: str | None = None) -> None:
        self.value = _FakePacket(raw)
        self.error = error


class _FakeDriver:
    response: ClassVar[_FakeTag]
    last_call: ClassVar[dict[str, object]] = {}

    def __init__(self, address: str) -> None:
        self.address = address
        self.socket_timeout = 0.0

    def open(self) -> bool:
        return True

    def generic_message(self, **kwargs: object) -> _FakeTag:
        self.__class__.last_call = kwargs
        return self.__class__.response

    def close(self) -> None:
        pass


def _fixture(
    object_type: CipInfrastructureObject = CipInfrastructureObject.ASSEMBLY,
) -> tuple[
    DiscoveryTarget,
    CipRouteDeclaration,
    CipInfrastructureReadRequest,
]:
    target = DiscoveryTarget(address="192.168.1.20")
    route = CipRouteDeclaration(
        gateway=target,
        segments=(CipRouteSegment(port=1, link=3),),
        maximum_depth=1,
    )
    request = CipInfrastructureReadRequest(
        object_type=object_type,
        instance=101 if object_type is CipInfrastructureObject.ASSEMBLY else 1,
        attribute=3,
        service=CipMetadataReadService.GET_ATTRIBUTE_SINGLE,
        specification_reference="authorized packet fixture",
    )
    return target, route, request


def test_emits_exact_planned_assembly_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target, route, request = _fixture()
    raw = _packet(0, b"\x34\x12\x99")
    _FakeDriver.response = _FakeTag(raw)
    monkeypatch.setattr(
        "twinforge.discovery.cip_infrastructure_pycomm3.CIPDriver",
        _FakeDriver,
    )

    result = LivePycomm3InfrastructureTransport().read_infrastructure(
        target, route, request, 3.0
    )

    assert result.general_status == 0
    assert result.response_payload == b"\x34\x12\x99"
    assert result.raw_reply == raw
    assert _FakeDriver.last_call == {
        "service": 14,
        "class_code": 4,
        "instance": 101,
        "attribute": 3,
        "connected": False,
        "unconnected_send": True,
        "route_path": b"\x01\x00\x01\x03",
        "name": "assembly instance 101 get_attribute_single",
        "return_response_packet": True,
    }


def test_preserves_connection_manager_failure_packet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target, route, request = _fixture(
        CipInfrastructureObject.CONNECTION_MANAGER
    )
    raw = _packet(5, b"\xaa\xbb", (0x0204,))
    _FakeDriver.response = _FakeTag(raw, "path destination unknown")
    monkeypatch.setattr(
        "twinforge.discovery.cip_infrastructure_pycomm3.CIPDriver",
        _FakeDriver,
    )

    result = LivePycomm3InfrastructureTransport().read_infrastructure(
        target, route, request, 2.0
    )

    assert result.general_status == 5
    assert result.additional_status == (0x0204,)
    assert result.response_payload == b"\xaa\xbb"
    assert result.message == "path destination unknown"
    assert _FakeDriver.last_call["class_code"] == 6


def test_rejects_route_mismatch_before_opening_driver() -> None:
    target, _, request = _fixture()
    other = DiscoveryTarget(address="192.168.1.21")
    wrong_route = CipRouteDeclaration(
        gateway=other,
        segments=(CipRouteSegment(port=1, link=3),),
        maximum_depth=1,
    )

    with pytest.raises(DiscoveryProviderError, match="does not match"):
        LivePycomm3InfrastructureTransport().read_infrastructure(
            target, wrong_route, request, 2.0
        )


def test_rejects_truncated_packet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target, route, request = _fixture()
    _FakeDriver.response = _FakeTag(b"short")
    monkeypatch.setattr(
        "twinforge.discovery.cip_infrastructure_pycomm3.CIPDriver",
        _FakeDriver,
    )

    with pytest.raises(DiscoveryProviderError, match="shorter"):
        LivePycomm3InfrastructureTransport().read_infrastructure(
            target, route, request, 2.0
        )
