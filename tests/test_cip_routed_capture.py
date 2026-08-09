import json
from datetime import datetime, timezone

from twinforge.discovery.chassis import (
    CipChassisObservation,
    CipChassisSlotObservation,
    CipSlotState,
    plan_cip_chassis_slots,
)
from twinforge.discovery.cip_routes import CipRouteDeclaration, CipRouteSegment
from twinforge.discovery.contracts import CipIdentityObservation, DiscoveryTarget
from twinforge.discovery.controller import CipControllerObservation
from twinforge.discovery.fake_routed import FakeRoutedCipProvider
from twinforge.discovery.routed_capture import (
    CipControllerReadPlan,
    CipRoutedCapturePlan,
    capture_routed_cip,
    cip_routed_snapshot_json,
)


TIMESTAMP = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)


def _identity(
    target: DiscoveryTarget,
    *,
    product_name: str = "1756-L82E",
) -> CipIdentityObservation:
    return CipIdentityObservation(
        target=target,
        captured_at=TIMESTAMP,
        vendor_id=1,
        device_type=14,
        product_code=166,
        major_revision=35,
        minor_revision=17,
        status=0,
        serial_number=1234,
        product_name=product_name,
    )


def _fixtures():
    target = DiscoveryTarget(address="192.168.1.10", label="lab gateway")
    route = CipRouteDeclaration(
        gateway=target,
        segments=(CipRouteSegment(port=1, link=0),),
        maximum_depth=1,
    )
    controller_plan = CipControllerReadPlan(target=target, route=route)
    chassis_plan = plan_cip_chassis_slots(route, (0, 1))
    controller = CipControllerObservation(
        target=target,
        captured_at=TIMESTAMP,
        identity=_identity(target),
        route=route,
        logical_name="LabController",
    )
    chassis = CipChassisObservation(
        plan=chassis_plan,
        captured_at=TIMESTAMP,
        slots=(
            CipChassisSlotObservation(
                0,
                CipSlotState.POPULATED,
                identity=_identity(target),
            ),
            CipChassisSlotObservation(1, CipSlotState.EMPTY),
        ),
    )
    return target, route, controller_plan, chassis_plan, controller, chassis


def test_fake_routed_capture_runs_each_plan_once_and_serializes_evidence() -> None:
    (
        _,
        route,
        controller_plan,
        chassis_plan,
        controller,
        chassis,
    ) = _fixtures()
    plan = CipRoutedCapturePlan(
        engagement="controlled lab",
        authorization_reference="LAB-001",
        controllers=(controller_plan,),
        chassis=(chassis_plan,),
    )
    provider = FakeRoutedCipProvider(
        controllers={controller_plan.key: controller},
        chassis={route.key: chassis},
    )

    snapshot = capture_routed_cip(plan, provider, captured_at=TIMESTAMP)
    document = json.loads(cip_routed_snapshot_json(snapshot))

    assert provider.calls == [
        ("controller", controller_plan.key),
        ("chassis", route.key),
    ]
    assert plan.total_request_budget == 3
    assert len(snapshot.controllers) == 1
    assert len(snapshot.chassis) == 1
    assert snapshot.diagnostics == ()
    assert document["plan"]["total_request_budget"] == 3
    assert document["controllers"][0]["metadata"]["logical_name"] == (
        "LabController"
    )
    assert document["chassis"][0]["slots"][1]["state"] == "empty"


def test_routed_capture_retains_provider_failure_as_diagnostic() -> None:
    target, route, controller_plan, _, _, _ = _fixtures()
    plan = CipRoutedCapturePlan(
        engagement="controlled lab",
        authorization_reference="LAB-001",
        controllers=(controller_plan,),
    )
    provider = FakeRoutedCipProvider(
        failures={
            ("controller", controller_plan.key): (
                "controller_no_response",
                "controller did not respond",
            )
        }
    )

    snapshot = capture_routed_cip(plan, provider, captured_at=TIMESTAMP)

    assert snapshot.controllers == ()
    assert snapshot.diagnostics[0].target == target
    assert snapshot.diagnostics[0].code == "controller_no_response"
    assert route.key in controller_plan.key


def test_fake_provider_retimes_fixture_evidence_to_capture_timestamp() -> None:
    _, route, controller_plan, chassis_plan, controller, chassis = _fixtures()
    later = datetime(2026, 8, 10, tzinfo=timezone.utc)
    plan = CipRoutedCapturePlan(
        engagement="controlled lab",
        authorization_reference="LAB-001",
        controllers=(controller_plan,),
        chassis=(chassis_plan,),
    )
    provider = FakeRoutedCipProvider(
        controllers={controller_plan.key: controller},
        chassis={route.key: chassis},
    )

    snapshot = capture_routed_cip(plan, provider, captured_at=later)

    assert snapshot.controllers[0].captured_at == later
    assert snapshot.controllers[0].identity.captured_at == later
    assert snapshot.chassis[0].captured_at == later
    assert snapshot.chassis[0].slots[0].identity is not None
    assert snapshot.chassis[0].slots[0].identity.captured_at == later
