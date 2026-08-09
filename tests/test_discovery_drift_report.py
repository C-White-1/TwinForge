from datetime import datetime, timezone

from twinforge.discovery import (
    DiscoveryDriftResult,
    DriftChangeType,
    DriftDomain,
    DriftFinding,
    DriftRecord,
)
from twinforge.discovery.topology import TopologyEvidenceReference
from twinforge.exporters import (
    DiscoveryDriftMarkdownExporter,
    sanitize_discovery_drift,
    sanitized_discovery_drift_json,
)


OLD = datetime(2026, 8, 8, tzinfo=timezone.utc)
NEW = datetime(2026, 8, 9, tzinfo=timezone.utc)


def _record(product_code: int, serial: int) -> DriftRecord:
    return DriftRecord(
        domain=DriftDomain.HARDWARE,
        key="cip:192.168.99.20|1:3",
        attributes=(
            ("device_type", 14),
            ("product_code", product_code),
            ("product_name", "Secret PLC Name"),
            ("serial_number", serial),
            ("vendor_id", 1),
        ),
        evidence=(
            TopologyEvidenceReference(
                protocol="cip_identity",
                observation_target="192.168.99.20|1:3",
                identifier="secret-route-object",
                description="sensitive description",
            ),
        ),
    )


def _result() -> DiscoveryDriftResult:
    return DiscoveryDriftResult(
        baseline_captured_at=OLD,
        current_captured_at=NEW,
        compared_domains=(DriftDomain.HARDWARE,),
        skipped_domains=(
            DriftDomain.CONFIGURATION,
            DriftDomain.FIRMWARE,
            DriftDomain.NETWORK,
        ),
        findings=(
            DriftFinding(
                domain=DriftDomain.HARDWARE,
                key="cip:192.168.99.20|1:3",
                change_type=DriftChangeType.CHANGED,
                before=_record(166, 123456),
                after=_record(167, 654321),
            ),
        ),
    )


def test_sanitized_report_omits_operational_and_serial_identifiers() -> None:
    report = sanitize_discovery_drift(_result())
    rendered = sanitized_discovery_drift_json(report)

    assert report.findings[0].reference == "DRIFT-0001"
    assert report.findings[0].confidence == "protocol_reported"
    assert '"product_code": 167' in rendered
    for secret in (
        "192.168.99.20",
        "Secret PLC Name",
        "123456",
        "654321",
        "secret-route-object",
        "sensitive description",
    ):
        assert secret not in rendered


def test_markdown_is_sanitized_and_markdownlint_friendly() -> None:
    markdown = DiscoveryDriftMarkdownExporter().export(
        sanitize_discovery_drift(_result())
    )

    assert "# Sanitized discovery drift report" in markdown
    assert "| DRIFT-0001 | hardware | changed | protocol_reported |" in markdown
    assert "192.168.99.20" not in markdown
    assert markdown.endswith("\n")
