from datetime import datetime, timezone

import pytest

from twinforge.discovery import (
    CipIdentityObservation,
    DiscoveryOperation,
    DiscoverySnapshot,
    DiscoveryTarget,
    DriftChangeType,
    DriftDomain,
    build_discovery_drift_state,
    detect_discovery_drift,
    discovery_drift_json,
)


OLD = datetime(2026, 8, 8, tzinfo=timezone.utc)
NEW = datetime(2026, 8, 9, tzinfo=timezone.utc)


def _snapshot(
    captured_at: datetime,
    *,
    product_code: int = 166,
    major: int = 35,
) -> DiscoverySnapshot:
    target = DiscoveryTarget(address="192.168.1.10")
    return DiscoverySnapshot(
        schema_version="1.0",
        engagement="authorized lab",
        authorization_reference="LAB-001",
        captured_at=captured_at,
        operations=(DiscoveryOperation.CIP_IDENTITY,),
        targets=(target,),
        identities=(
            CipIdentityObservation(
                target=target,
                captured_at=captured_at,
                vendor_id=1,
                device_type=14,
                product_code=product_code,
                major_revision=major,
                minor_revision=11,
                status=96,
                serial_number=1234,
                product_name="Controller",
            ),
        ),
    )


def test_detects_hardware_and_firmware_changes_separately() -> None:
    domains = (DriftDomain.FIRMWARE, DriftDomain.HARDWARE)
    baseline = build_discovery_drift_state(
        captured_at=OLD,
        complete_domains=domains,
        snapshot=_snapshot(OLD),
    )
    current = build_discovery_drift_state(
        captured_at=NEW,
        complete_domains=domains,
        snapshot=_snapshot(NEW, product_code=167, major=36),
    )

    result = detect_discovery_drift(baseline, current)

    assert [(item.domain, item.change_type) for item in result.findings] == [
        (DriftDomain.FIRMWARE, DriftChangeType.CHANGED),
        (DriftDomain.HARDWARE, DriftChangeType.CHANGED),
    ]
    assert '"major_revision": 36' in discovery_drift_json(result)


def test_incomplete_current_domain_is_skipped_not_reported_removed() -> None:
    baseline = build_discovery_drift_state(
        captured_at=OLD,
        complete_domains=(DriftDomain.HARDWARE,),
        snapshot=_snapshot(OLD),
    )
    current = build_discovery_drift_state(
        captured_at=NEW,
        complete_domains=(),
    )

    result = detect_discovery_drift(baseline, current)

    assert result.findings == ()
    assert DriftDomain.HARDWARE in result.skipped_domains


def test_complete_empty_hardware_capture_reports_removal() -> None:
    baseline = build_discovery_drift_state(
        captured_at=OLD,
        complete_domains=(DriftDomain.HARDWARE,),
        snapshot=_snapshot(OLD),
    )
    empty = _snapshot(NEW)
    empty = DiscoverySnapshot(
        schema_version=empty.schema_version,
        engagement=empty.engagement,
        authorization_reference=empty.authorization_reference,
        captured_at=empty.captured_at,
        operations=empty.operations,
        targets=empty.targets,
        identities=(),
    )
    current = build_discovery_drift_state(
        captured_at=NEW,
        complete_domains=(DriftDomain.HARDWARE,),
        snapshot=empty,
    )

    result = detect_discovery_drift(baseline, current)

    assert result.findings[0].change_type is DriftChangeType.REMOVED


def test_declared_domain_requires_its_evidence_source() -> None:
    with pytest.raises(ValueError, match="network completeness"):
        build_discovery_drift_state(
            captured_at=NEW,
            complete_domains=(DriftDomain.NETWORK,),
        )
