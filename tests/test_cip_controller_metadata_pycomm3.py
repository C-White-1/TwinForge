from typing import ClassVar

import pytest

from twinforge.discovery.cip_routes import CipRouteDeclaration, CipRouteSegment
from twinforge.discovery.contracts import DiscoveryProviderError, DiscoveryTarget
from twinforge.discovery.controller_metadata import (
    CipControllerMetadataRequest,
    CipMetadataNamespace,
    CipMetadataReadService,
)
from twinforge.discovery.controller_metadata_pycomm3 import (
    LivePycomm3MetadataTransport,
    standard_metadata_decoders,
)


IDENTITY_PAYLOAD = bytes.fromhex(
    "01000e00a60023116000785634120a436f6e74726f6c6c657203"
)


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


def _fixture() -> tuple[
    DiscoveryTarget,
    CipRouteDeclaration,
    CipControllerMetadataRequest,
]:
    target = DiscoveryTarget(address="192.168.1.10")
    route = CipRouteDeclaration(
        gateway=target,
        segments=(CipRouteSegment(port=1, link=0),),
        maximum_depth=1,
    )
    request = CipControllerMetadataRequest(
        name="Identity attributes",
        service=CipMetadataReadService.GET_ATTRIBUTES_ALL,
        class_code=1,
        instance=1,
        namespace=CipMetadataNamespace.STANDARD_CIP,
        specification_reference="CIP Identity Object",
        decoder="cip_identity_firmware_revision",
    )
    return target, route, request


def test_live_transport_emits_exact_planned_generic_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target, route, request = _fixture()
    _FakeDriver.response = _FakeTag(_packet(0, IDENTITY_PAYLOAD))
    monkeypatch.setattr(
        "twinforge.discovery.controller_metadata_pycomm3.CIPDriver",
        _FakeDriver,
    )

    result = LivePycomm3MetadataTransport().read_metadata(
        target,
        route,
        request,
        3.0,
    )

    assert result.general_status == 0
    assert result.response_payload == IDENTITY_PAYLOAD
    assert result.raw_reply == _FakeDriver.response.value.raw
    assert _FakeDriver.last_call == {
        "service": 1,
        "class_code": 1,
        "instance": 1,
        "attribute": b"",
        "connected": False,
        "unconnected_send": True,
        "route_path": b"\x01\x00\x01\x00",
        "name": "Identity attributes",
        "return_response_packet": True,
    }


def test_live_transport_preserves_failed_status_and_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target, route, request = _fixture()
    raw = _packet(5, b"\x99\x88", (0x0204, 0x0315))
    _FakeDriver.response = _FakeTag(raw, "path destination unknown")
    monkeypatch.setattr(
        "twinforge.discovery.controller_metadata_pycomm3.CIPDriver",
        _FakeDriver,
    )

    result = LivePycomm3MetadataTransport().read_metadata(
        target,
        route,
        request,
        2.0,
    )

    assert result.general_status == 5
    assert result.additional_status == (0x0204, 0x0315)
    assert result.response_payload == b"\x99\x88"
    assert result.raw_reply == raw
    assert result.message == "path destination unknown"


def test_live_transport_rejects_truncated_status_packet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target, route, request = _fixture()
    _FakeDriver.response = _FakeTag(b"short")
    monkeypatch.setattr(
        "twinforge.discovery.controller_metadata_pycomm3.CIPDriver",
        _FakeDriver,
    )

    with pytest.raises(DiscoveryProviderError, match="shorter"):
        LivePycomm3MetadataTransport().read_metadata(
            target,
            route,
            request,
            2.0,
        )


def test_standard_identity_firmware_decoder_is_specification_backed() -> None:
    decoder = standard_metadata_decoders()[
        "cip_identity_firmware_revision"
    ]

    assert decoder(IDENTITY_PAYLOAD) == "35.17"
