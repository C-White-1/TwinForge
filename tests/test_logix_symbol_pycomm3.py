from datetime import datetime, timezone
from struct import pack
from typing import ClassVar

import pytest

from twinforge.discovery.cip_pycomm3_routed import RoutedExecutionPermit
from twinforge.discovery.cip_routes import CipRouteDeclaration, CipRouteSegment
from twinforge.discovery.contracts import DiscoveryTarget
from twinforge.discovery.logix_symbol_pycomm3 import (
    ExperimentalPycomm3LogixSymbolTransport,
    pycomm3_logix_path,
)
from twinforge.discovery.software_inventory_capture import (
    PermittedSoftwareInventoryExecutor,
)
from twinforge.discovery.software_inventory_plan import (
    CipSoftwareInventoryCapability,
    CipSoftwareInventoryPlan,
)


TIMESTAMP = datetime(2026, 8, 9, tzinfo=timezone.utc)


def _record(instance: int, name: str) -> bytes:
    encoded = name.encode()
    return b"".join(
        (
            pack("<IH", instance, len(encoded)),
            encoded,
            pack("<HIIIIII", 0xC1, 1, 2, 0, 0, 0, 0),
            bytes((2,)),
        )
    )


class _Packet:
    def __init__(self, data: bytes, status: int) -> None:
        self.data = data
        self.service_status = status
        self.raw = b"packet:" + data


class _Tag:
    def __init__(self, packet: _Packet) -> None:
        self.value = packet
        self.error = None


class _Driver:
    responses: ClassVar[list[_Tag]] = []
    paths: ClassVar[list[str]] = []
    calls: ClassVar[list[dict[str, object]]] = []

    def __init__(self, path: str, **kwargs: object) -> None:
        self.__class__.paths.append(path)
        self.socket_timeout = 0.0

    def open(self) -> bool:
        return True

    def generic_message(self, **kwargs: object) -> _Tag:
        self.__class__.calls.append(kwargs)
        return self.__class__.responses.pop(0)

    def close(self) -> None:
        pass


def _fixture() -> tuple[CipSoftwareInventoryPlan, RoutedExecutionPermit]:
    target = DiscoveryTarget(address="192.168.1.10")
    route = CipRouteDeclaration(
        gateway=target,
        segments=(CipRouteSegment(port=1, link=0),),
        maximum_depth=1,
    )
    plan = CipSoftwareInventoryPlan(
        target=target,
        route=route,
        authorization_reference="LAB-001",
        capabilities=(
            CipSoftwareInventoryCapability.PROGRAMS,
            CipSoftwareInventoryCapability.ROUTINES,
            CipSoftwareInventoryCapability.TAG_DEFINITIONS,
            CipSoftwareInventoryCapability.TASKS,
        ),
        maximum_requests=3,
    )
    permit = RoutedExecutionPermit(
        authorization_reference="LAB-001",
        confirmed_by="operator@example.test",
        confirmed_at=TIMESTAMP,
        allowed_route_keys=(route.key,),
    )
    return plan, permit


def test_transport_enumerates_controller_then_program_scope_one_page_at_a_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan, permit = _fixture()
    _Driver.paths = []
    _Driver.calls = []
    _Driver.responses = [
        _Tag(_Packet(_record(1, "Program:MainProgram"), 6)),
        _Tag(_Packet(_record(4, "Task:MainTask"), 0)),
        _Tag(
            _Packet(
                _record(1, "Routine:MainRoutine")
                + _record(2, "MotorRun"),
                0,
            )
        ),
    ]
    monkeypatch.setattr(
        "twinforge.discovery.logix_symbol_pycomm3.LogixDriver",
        _Driver,
    )
    transport = ExperimentalPycomm3LogixSymbolTransport(
        laboratory_evidence_reference="OFFLINE-PACKET-FIXTURE",
    )

    observation = PermittedSoftwareInventoryExecutor(
        plan,
        permit=permit,
        transport=transport,
    ).capture(captured_at=TIMESTAMP)

    assert _Driver.paths == ["192.168.1.10/1/0"] * 3
    assert [call["instance"] for call in _Driver.calls] == [0, 2, 0]
    assert all(call["connected"] is True for call in _Driver.calls)
    assert observation.requests_used == 3
    assert [(item.name, item.parent) for item in observation.items] == [
        ("MainProgram", None),
        ("MainRoutine", "MainProgram"),
        ("MotorRun", "MainProgram"),
        ("MainTask", None),
    ]
    assert len(observation.object_evidence) == 3


def test_logix_path_rejects_binary_links() -> None:
    target = DiscoveryTarget(address="192.168.1.10")
    route = CipRouteDeclaration(
        gateway=target,
        segments=(CipRouteSegment(port=1, link=b"\x00"),),
        maximum_depth=1,
    )

    with pytest.raises(ValueError, match="binary"):
        pycomm3_logix_path(route)
