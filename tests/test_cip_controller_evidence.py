import json
from datetime import datetime, timezone

import pytest

from twinforge.discovery import (
    CipControllerObservation,
    CipIdentityObservation,
    CipObjectEvidence,
    CipRouteDeclaration,
    CipRouteSegment,
    DiscoveryTarget,
    cip_controller_json,
)


def _identity(target: DiscoveryTarget) -> CipIdentityObservation:
    return CipIdentityObservation(
        target=target,
        captured_at=datetime(2026, 8, 9, tzinfo=timezone.utc),
        vendor_id=1,
        device_type=14,
        product_code=166,
        major_revision=35,
        minor_revision=17,
        status=96,
        serial_number=305419896,
        product_name="Controller",
        raw_payload_hex="01000e00",
        raw_attributes={"unknown_identity_attribute": 77},
    )


def test_controller_evidence_preserves_generic_and_vendor_specific_data() -> None:
    target = DiscoveryTarget(address="192.168.1.10", label="gateway")
    route = CipRouteDeclaration(
        gateway=target,
        segments=(CipRouteSegment(port=1, link=0),),
        maximum_depth=1,
    )
    observation = CipControllerObservation(
        target=target,
        captured_at=datetime(2026, 8, 9, tzinfo=timezone.utc),
        identity=_identity(target),
        route=route,
        logical_name="LabController",
        project_name="TestProject",
        firmware_revision="35.17",
        operating_mode="remote-run",
        raw_attributes={
            "vendor_attribute_99": {
                "type": "bytes",
                "value": "010203",
            }
        },
        object_evidence=(
            CipObjectEvidence(
                class_code=0xAC,
                instance=1,
                attribute=99,
                service=0x0E,
                general_status=0,
                response_payload_hex="010203",
                decoded={"observed_value": [1, 2, 3]},
            ),
        ),
    )

    document = json.loads(cip_controller_json(observation))

    assert document["metadata"]["logical_name"] == "LabController"
    assert document["identity"]["vendor_id"] == 1
    assert document["identity"]["raw_attributes"] == {
        "unknown_identity_attribute": 77
    }
    assert document["raw_attributes"]["vendor_attribute_99"]["value"] == (
        "010203"
    )
    assert document["object_evidence"][0]["response_payload_hex"] == "010203"
    assert document["route"]["segments"][0]["link"] == 0


def test_controller_evidence_sorts_object_responses_deterministically() -> None:
    target = DiscoveryTarget(address="192.168.1.10")
    observation = CipControllerObservation(
        target=target,
        captured_at=datetime.now(timezone.utc),
        identity=_identity(target),
        object_evidence=(
            CipObjectEvidence(2, 1, 14, 0),
            CipObjectEvidence(1, 1, 14, 0),
        ),
    )

    document = json.loads(cip_controller_json(observation))

    assert [item["class_code"] for item in document["object_evidence"]] == [1, 2]


def test_controller_evidence_rejects_mismatched_identity_target() -> None:
    target = DiscoveryTarget(address="192.168.1.10")

    with pytest.raises(ValueError, match="identity target"):
        CipControllerObservation(
            target=target,
            captured_at=datetime.now(timezone.utc),
            identity=_identity(DiscoveryTarget(address="192.168.1.11")),
        )


def test_controller_evidence_rejects_mismatched_route_gateway() -> None:
    target = DiscoveryTarget(address="192.168.1.10")
    route = CipRouteDeclaration(
        gateway=DiscoveryTarget(address="192.168.1.11"),
        segments=(CipRouteSegment(port=1, link=0),),
        maximum_depth=1,
    )

    with pytest.raises(ValueError, match="route gateway"):
        CipControllerObservation(
            target=target,
            captured_at=datetime.now(timezone.utc),
            identity=_identity(target),
            route=route,
        )


def test_controller_evidence_requires_timezone_and_valid_cip_numbers() -> None:
    target = DiscoveryTarget(address="192.168.1.10")
    with pytest.raises(ValueError, match="timezone"):
        CipControllerObservation(
            target=target,
            captured_at=datetime(2026, 8, 9),
            identity=_identity(target),
        )
    with pytest.raises(ValueError, match="must not be negative"):
        CipObjectEvidence(-1, 1, 14, 0)
