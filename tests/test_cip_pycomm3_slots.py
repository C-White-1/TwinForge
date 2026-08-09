from typing import ClassVar

import pytest

from twinforge.discovery.cip_pycomm3_chassis import RoutedSlotOutcome
from twinforge.discovery.cip_pycomm3_slots import (
    CipSlotStatusProfile,
    CipSlotStatusSignature,
    LivePycomm3RoutedSlotTransport,
)
from twinforge.discovery.cip_routes import CipRouteDeclaration, CipRouteSegment
from twinforge.discovery.contracts import DiscoveryTarget


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


class _FakePacket:
    def __init__(self, raw: bytes | None) -> None:
        self.raw = raw


class _FakeTag:
    def __init__(self, raw: bytes | None, error: str | None = None) -> None:
        self.value = _FakePacket(raw)
        self.error = error


class _FakeDriver:
    response: ClassVar[_FakeTag]
    open_result: ClassVar[bool] = True
    last_call: ClassVar[dict[str, object]] = {}

    def __init__(self, address: str) -> None:
        self.address = address
        self.socket_timeout = 0.0

    def open(self) -> bool:
        return self.__class__.open_result

    def generic_message(self, **kwargs: object) -> _FakeTag:
        self.__class__.last_call = kwargs
        return self.__class__.response

    def close(self) -> None:
        pass


def _route() -> CipRouteDeclaration:
    return CipRouteDeclaration(
        gateway=DiscoveryTarget(address="192.168.1.10"),
        segments=(CipRouteSegment(port=1, link=3),),
        maximum_depth=1,
    )


def _patch_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "twinforge.discovery.cip_pycomm3_slots.CIPDriver",
        _FakeDriver,
    )


def test_successful_identity_is_populated_with_exact_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _FakeDriver.open_result = True
    raw = _packet(0, IDENTITY_PAYLOAD)
    _FakeDriver.response = _FakeTag(raw)
    _patch_driver(monkeypatch)

    result = LivePycomm3RoutedSlotTransport().read_slot_identity(
        _route(),
        3.0,
    )

    assert result.outcome is RoutedSlotOutcome.POPULATED
    assert result.reply is not None
    assert result.reply.payload == IDENTITY_PAYLOAD
    assert result.raw_response == raw
    assert _FakeDriver.last_call["route_path"] == b"\x01\x00\x01\x03"
    assert _FakeDriver.last_call["connected"] is False
    assert _FakeDriver.last_call["unconnected_send"] is True


def test_absent_packet_is_no_response(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeDriver.open_result = True
    _FakeDriver.response = _FakeTag(None, "no response")
    _patch_driver(monkeypatch)

    result = LivePycomm3RoutedSlotTransport().read_slot_identity(
        _route(),
        2.0,
    )

    assert result.outcome is RoutedSlotOutcome.NO_RESPONSE
    assert result.message == "no response"


def test_unknown_failure_remains_device_fault(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _FakeDriver.open_result = True
    raw = _packet(5, b"\x99", (0x0204,))
    _FakeDriver.response = _FakeTag(raw, "path destination unknown")
    _patch_driver(monkeypatch)

    result = LivePycomm3RoutedSlotTransport().read_slot_identity(
        _route(),
        2.0,
    )

    assert result.outcome is RoutedSlotOutcome.DEVICE_FAULT
    assert result.general_status == 5
    assert result.additional_status == (0x0204,)
    assert result.raw_response == raw
    assert result.raw_attributes == {
        "profile": "conservative-unclassified",
        "classification_source": None,
        "classification_matched": False,
    }


@pytest.mark.parametrize(
    ("outcome", "status", "additional"),
    [
        (RoutedSlotOutcome.EMPTY, 5, (0x0204,)),
        (RoutedSlotOutcome.UNSUPPORTED_ROUTE, 4, ()),
    ],
)
def test_exact_documented_signature_enables_specific_classification(
    monkeypatch: pytest.MonkeyPatch,
    outcome: RoutedSlotOutcome,
    status: int,
    additional: tuple[int, ...],
) -> None:
    _FakeDriver.open_result = True
    raw = _packet(status, additional_status=additional)
    _FakeDriver.response = _FakeTag(raw, "documented failure")
    _patch_driver(monkeypatch)
    profile = CipSlotStatusProfile(
        name="authorized-lab-fixture-v1",
        signatures=(
            CipSlotStatusSignature(
                general_status=status,
                additional_status=additional,
                outcome=outcome,
                source_reference="LAB-FIXTURE-001",
            ),
        ),
    )

    result = LivePycomm3RoutedSlotTransport(profile).read_slot_identity(
        _route(),
        2.0,
    )

    assert result.outcome is outcome
    assert result.raw_attributes == {
        "profile": "authorized-lab-fixture-v1",
        "classification_source": "LAB-FIXTURE-001",
        "classification_matched": True,
    }


def test_duplicate_status_signatures_are_rejected() -> None:
    signature = CipSlotStatusSignature(
        general_status=5,
        additional_status=(0x0204,),
        outcome=RoutedSlotOutcome.EMPTY,
        source_reference="LAB-FIXTURE-001",
    )

    with pytest.raises(ValueError, match="must be unique"):
        CipSlotStatusProfile(
            name="invalid",
            signatures=(signature, signature),
        )
