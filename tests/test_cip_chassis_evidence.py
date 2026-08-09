import json
from datetime import datetime, timezone

import pytest

from twinforge.discovery.chassis import (
    CipChassisObservation,
    CipChassisSlotObservation,
    CipSlotState,
    cip_chassis_json,
    plan_cip_chassis_slots,
)
from twinforge.discovery.cip_routes import CipRouteDeclaration, CipRouteSegment
from twinforge.discovery.contracts import CipIdentityObservation, DiscoveryTarget


def _route(target: DiscoveryTarget) -> CipRouteDeclaration:
    return CipRouteDeclaration(
        gateway=target,
        segments=(CipRouteSegment(port=1, link=0),),
        maximum_depth=1,
    )


def _identity(target: DiscoveryTarget) -> CipIdentityObservation:
    return CipIdentityObservation(
        target=target,
        captured_at=datetime(2026, 8, 9, tzinfo=timezone.utc),
        vendor_id=1,
        device_type=7,
        product_code=11,
        major_revision=3,
        minor_revision=1,
        status=0,
        serial_number=1234,
        product_name="1756-IB16",
        raw_payload_hex="01000700",
    )


def test_chassis_plan_is_explicit_sorted_and_bounded() -> None:
    target = DiscoveryTarget(address="192.168.1.10")

    plan = plan_cip_chassis_slots(_route(target), (3, 0, 2))

    assert plan.slots == (0, 2, 3)
    assert plan.request_budget_per_slot == 1
    assert plan.total_request_budget == 3


def test_chassis_preserves_each_distinct_slot_outcome() -> None:
    target = DiscoveryTarget(address="192.168.1.10")
    plan = plan_cip_chassis_slots(_route(target), (0, 1, 2, 3, 4))
    observation = CipChassisObservation(
        plan=plan,
        captured_at=datetime(2026, 8, 9, tzinfo=timezone.utc),
        slots=(
            CipChassisSlotObservation(
                slot=4,
                state=CipSlotState.DEVICE_FAULT,
                general_status=1,
                additional_status=(513,),
                raw_response_hex="01020102",
                raw_attributes={"vendor_detail": {"code": 513}},
            ),
            CipChassisSlotObservation(
                slot=0,
                state=CipSlotState.POPULATED,
                identity=_identity(target),
            ),
            CipChassisSlotObservation(slot=1, state=CipSlotState.EMPTY),
            CipChassisSlotObservation(
                slot=2,
                state=CipSlotState.NO_RESPONSE,
            ),
            CipChassisSlotObservation(
                slot=3,
                state=CipSlotState.UNSUPPORTED_ROUTE,
            ),
        ),
    )

    document = json.loads(cip_chassis_json(observation))

    assert document["plan"]["slots"] == [0, 1, 2, 3, 4]
    assert document["plan"]["total_request_budget"] == 5
    assert [item["state"] for item in document["slots"]] == [
        "populated",
        "empty",
        "no_response",
        "unsupported_route",
        "device_fault",
    ]
    assert document["slots"][0]["identity"]["product_name"] == "1756-IB16"
    assert document["slots"][4]["raw_attributes"] == {
        "vendor_detail": {"code": 513}
    }


def test_chassis_requires_exactly_one_outcome_for_every_planned_slot() -> None:
    target = DiscoveryTarget(address="192.168.1.10")
    plan = plan_cip_chassis_slots(_route(target), (0, 1))

    with pytest.raises(ValueError, match="every planned slot"):
        CipChassisObservation(
            plan=plan,
            captured_at=datetime.now(timezone.utc),
            slots=(CipChassisSlotObservation(0, CipSlotState.EMPTY),),
        )


def test_only_populated_slot_may_have_identity() -> None:
    target = DiscoveryTarget(address="192.168.1.10")
    with pytest.raises(ValueError, match="requires identity"):
        CipChassisSlotObservation(0, CipSlotState.POPULATED)
    with pytest.raises(ValueError, match="only a populated"):
        CipChassisSlotObservation(
            0,
            CipSlotState.EMPTY,
            identity=_identity(target),
        )


def test_chassis_rejects_slot_identity_from_another_gateway() -> None:
    target = DiscoveryTarget(address="192.168.1.10")
    plan = plan_cip_chassis_slots(_route(target), (0,))

    with pytest.raises(ValueError, match="identity target"):
        CipChassisObservation(
            plan=plan,
            captured_at=datetime.now(timezone.utc),
            slots=(
                CipChassisSlotObservation(
                    0,
                    CipSlotState.POPULATED,
                    identity=_identity(DiscoveryTarget(address="192.168.1.11")),
                ),
            ),
        )


def test_chassis_plan_rejects_duplicates_and_negative_slots() -> None:
    target = DiscoveryTarget(address="192.168.1.10")
    with pytest.raises(ValueError, match="unique and sorted"):
        plan_cip_chassis_slots(_route(target), (0, 0))
    with pytest.raises(ValueError, match="non-negative"):
        plan_cip_chassis_slots(_route(target), (-1,))
