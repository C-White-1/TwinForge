import json
from datetime import datetime, timezone

from twinforge.discovery.chassis import (
    CipChassisObservation,
    CipChassisSlotObservation,
    CipSlotState,
    plan_cip_chassis_slots,
)
from twinforge.discovery.cip_routes import CipRouteDeclaration, CipRouteSegment
from twinforge.discovery.configured_module_reconciliation import (
    ConfiguredModuleComparisonStatus,
    RoutedConfiguredModuleBinding,
    reconcile_routed_configured_modules,
    routed_configured_module_reconciliation_json,
)
from twinforge.discovery.contracts import (
    CipIdentityObservation,
    DiscoveryTarget,
)
from twinforge.discovery.routed_capture import (
    CipRoutedCapturePlan,
    CipRoutedDiscoverySnapshot,
)
from twinforge.model import Identity, Module, Revision, VendorIdentity


TIMESTAMP = datetime(2026, 8, 9, tzinfo=timezone.utc)


def _module(name: str, slot: int, product_code: int) -> Module:
    return Module(
        name=name,
        catalog="1756-IB16",
        slot=slot,
        identity=Identity(
            vendor=VendorIdentity(1),
            product_type=7,
            product_code=product_code,
            revision=Revision(3, 1),
        ),
    )


def _identity(target: DiscoveryTarget, product_code: int) -> CipIdentityObservation:
    return CipIdentityObservation(
        target=target,
        captured_at=TIMESTAMP,
        vendor_id=1,
        device_type=7,
        product_code=product_code,
        major_revision=3,
        minor_revision=1,
        status=0,
        serial_number=product_code,
        product_name="1756-IB16",
    )


def _snapshot() -> tuple[CipRoutedDiscoverySnapshot, CipRouteDeclaration]:
    target = DiscoveryTarget(address="192.168.1.10")
    route = CipRouteDeclaration(
        gateway=target,
        segments=(CipRouteSegment(port=1, link=0),),
        maximum_depth=1,
    )
    slot_plan = plan_cip_chassis_slots(route, (1, 2, 3))
    chassis = CipChassisObservation(
        plan=slot_plan,
        captured_at=TIMESTAMP,
        slots=(
            CipChassisSlotObservation(
                slot=1,
                state=CipSlotState.POPULATED,
                identity=_identity(target, 11),
            ),
            CipChassisSlotObservation(slot=2, state=CipSlotState.EMPTY),
            CipChassisSlotObservation(
                slot=3,
                state=CipSlotState.POPULATED,
                identity=_identity(target, 12),
            ),
        ),
    )
    capture_plan = CipRoutedCapturePlan(
        engagement="authorized lab",
        authorization_reference="LAB-001",
        chassis=(slot_plan,),
    )
    return (
        CipRoutedDiscoverySnapshot(
            schema_version="1.0",
            engagement=capture_plan.engagement,
            authorization_reference=capture_plan.authorization_reference,
            captured_at=TIMESTAMP,
            plan=capture_plan,
            chassis=(chassis,),
        ),
        route,
    )


def test_routed_reconciliation_uses_exact_route_and_slot_bindings() -> None:
    snapshot, route = _snapshot()
    result = reconcile_routed_configured_modules(
        snapshot,
        (
            RoutedConfiguredModuleBinding(
                key="Local/DI_Slot1",
                chassis_route_key=route.key,
                slot=1,
                module=_module("DI_Slot1", 1, 11),
            ),
            RoutedConfiguredModuleBinding(
                key="Local/DI_Slot2",
                chassis_route_key=route.key,
                slot=2,
                module=_module("DI_Slot2", 2, 11),
            ),
        ),
    )
    document = json.loads(routed_configured_module_reconciliation_json(result))

    assert len(result.candidates) == 1
    assert result.candidates[0].status is ConfiguredModuleComparisonStatus.EXACT
    assert "cip_routed_slot" in {
        evidence.protocol for evidence in result.candidates[0].evidence
    }
    assert {issue.reason for issue in result.issues} == {
        "empty",
        "populated_slot_without_binding",
    }
    assert document["issues"][0]["slot"] in {2, 3}


def test_routed_reconciliation_rejects_duplicate_locations() -> None:
    snapshot, route = _snapshot()
    binding = RoutedConfiguredModuleBinding(
        key="Local/DI_Slot1",
        chassis_route_key=route.key,
        slot=1,
        module=_module("DI_Slot1", 1, 11),
    )

    try:
        reconcile_routed_configured_modules(snapshot, (binding, binding))
    except ValueError as error:
        assert "unique locations" in str(error)
    else:
        raise AssertionError("duplicate routed bindings were accepted")
