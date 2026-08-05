from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from twinforge.discovery import (
    DiscoveryScope,
    DiscoveryTarget,
    FakeCipIdentity,
    FakeDiscoveryProvider,
    capture_snapshot,
    snapshot_data,
    snapshot_json,
)


CAPTURED_AT = datetime(2026, 8, 4, 1, 2, 3, tzinfo=timezone.utc)


def target(address: str, *route: int) -> DiscoveryTarget:
    return DiscoveryTarget(address=address, route=route)


def identity(name: str, serial: int) -> FakeCipIdentity:
    return FakeCipIdentity(
        vendor_id=1,
        device_type=14,
        product_code=166,
        major_revision=35,
        minor_revision=11,
        status=0x0060,
        serial_number=serial,
        product_name=name,
        state=3,
        raw_payload_hex="01000e00a60023116000785634120544657374",
        raw_attributes={"attribute_99": "preserved", "connected": True},
    )


def test_capture_is_deterministic_and_preserves_raw_identity_evidence() -> None:
    second = target("192.0.2.20", 1, 1)
    first = target("192.0.2.10")
    scope = DiscoveryScope(
        engagement="authorized-lab",
        authorization_reference="change-1234",
        targets=(second, first),
    )
    provider = FakeDiscoveryProvider(
        {
            first.key: identity("Controller", 0x12345678),
            second.key: identity("Remote IO", 0x87654321),
        }
    )

    snapshot = capture_snapshot(scope, provider, captured_at=CAPTURED_AT)
    repeated = capture_snapshot(scope, provider, captured_at=CAPTURED_AT)

    assert [item.target.address for item in snapshot.identities] == [
        "192.0.2.10",
        "192.0.2.20",
    ]
    assert snapshot.identities[0].raw_attributes == {
        "attribute_99": "preserved",
        "connected": True,
    }
    assert snapshot_data(snapshot)["schema_version"] == "1.0"
    assert snapshot_json(snapshot) == snapshot_json(repeated)
    assert snapshot_json(snapshot).endswith("\n")


def test_provider_failure_becomes_evidence_diagnostic() -> None:
    endpoint = target("192.0.2.30")
    scope = DiscoveryScope(
        engagement="authorized-lab",
        authorization_reference="change-1234",
        targets=(endpoint,),
    )
    provider = FakeDiscoveryProvider(
        {},
        failures={endpoint.key: ("timeout", "identity request timed out")},
    )

    snapshot = capture_snapshot(scope, provider, captured_at=CAPTURED_AT)

    assert snapshot.identities == ()
    assert len(snapshot.diagnostics) == 1
    assert snapshot.diagnostics[0].code == "timeout"
    assert snapshot.diagnostics[0].target == endpoint


def test_scope_rejects_duplicate_targets() -> None:
    endpoint = target("192.0.2.40")

    with pytest.raises(ValidationError, match="scope targets must be unique"):
        DiscoveryScope(
            engagement="authorized-lab",
            authorization_reference="change-1234",
            targets=(endpoint, endpoint),
        )


def test_capture_rejects_naive_timestamp() -> None:
    endpoint = target("192.0.2.50")
    scope = DiscoveryScope(
        engagement="authorized-lab",
        authorization_reference="change-1234",
        targets=(endpoint,),
    )

    with pytest.raises(ValueError, match="must include a timezone"):
        capture_snapshot(
            scope,
            FakeDiscoveryProvider({endpoint.key: identity("PLC", 1)}),
            captured_at=datetime(2026, 8, 4),
        )
