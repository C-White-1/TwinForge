from datetime import datetime, timezone

from twinforge.discovery import (
    CipIdentityObservation,
    DiscoveryOperation,
    DiscoverySnapshot,
    DiscoveryTarget,
    SnmpNodeObservation,
    SnmpPhysicalEntityObservation,
    TopologyConfidence,
    identity_reconciliation_json,
    reconcile_cip_physical_identities,
)


CAPTURED_AT = datetime(2026, 8, 5, tzinfo=timezone.utc)
BASE = "1.3.6.1.2.1.47.1.1.1.1"


def _snapshot(*, model: str, serial: str) -> DiscoverySnapshot:
    target = DiscoveryTarget(address="192.0.2.80", label="lab-controller")
    return DiscoverySnapshot(
        schema_version="1.0",
        engagement="authorized-lab",
        authorization_reference="lab-ticket-reconcile",
        captured_at=CAPTURED_AT,
        operations=(
            DiscoveryOperation.CIP_IDENTITY,
            DiscoveryOperation.SNMP_NETWORK,
        ),
        targets=(target,),
        identities=(
            CipIdentityObservation(
                target=target,
                captured_at=CAPTURED_AT,
                vendor_id=1,
                device_type=14,
                product_code=165,
                major_revision=34,
                minor_revision=11,
                status=0,
                serial_number=12345,
                product_name="Example Controller",
            ),
        ),
        snmp_nodes=(
            SnmpNodeObservation(
                target=target,
                captured_at=CAPTURED_AT,
                physical_entities=(
                    SnmpPhysicalEntityObservation(
                        index=100,
                        physical_class=3,
                        model_name=model,
                        serial_number=serial,
                        raw_oids={
                            f"{BASE}.11.100": serial,
                            f"{BASE}.13.100": model,
                        },
                    ),
                ),
            ),
        ),
    )


def test_reconciles_exact_model_and_decimal_serial_with_provenance() -> None:
    result = reconcile_cip_physical_identities(
        _snapshot(model="  example   controller ", serial="12345")
    )

    assert len(result.matches) == 1
    match = result.matches[0]
    assert match.matched_fields == (
        "product_name",
        "serial_number_decimal",
    )
    assert match.confidence is TopologyConfidence.CORROBORATED
    assert {item.identifier for item in match.evidence} == {
        "cip.identity.product_name",
        "cip.identity.serial_number_decimal",
        f"{BASE}.11.100",
        f"{BASE}.13.100",
    }
    assert result.unmatched_cip_targets == ()
    assert result.unmatched_physical_assets == ()


def test_does_not_guess_hexadecimal_or_cross_target_serial_formats() -> None:
    result = reconcile_cip_physical_identities(
        _snapshot(model="Different Model", serial="0x3039")
    )

    assert result.matches == ()
    assert result.unmatched_cip_targets == ("192.0.2.80|",)
    assert len(result.unmatched_physical_assets) == 1


def test_reconciliation_serialization_is_deterministic() -> None:
    snapshot = _snapshot(model="Example Controller", serial="12345")

    first = identity_reconciliation_json(
        reconcile_cip_physical_identities(snapshot)
    )
    second = identity_reconciliation_json(
        reconcile_cip_physical_identities(snapshot)
    )

    assert first == second
    assert first.endswith("\n")
