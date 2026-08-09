"""Sanitized deterministic exports for discovery drift findings."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from twinforge.discovery import (
    DiscoveryDriftResult,
    DriftDomain,
    DriftFinding,
    DriftRecord,
)


_SAFE_ATTRIBUTES: dict[DriftDomain, frozenset[str]] = {
    DriftDomain.HARDWARE: frozenset(
        {"state", "vendor_id", "device_type", "product_code"}
    ),
    DriftDomain.FIRMWARE: frozenset({"major_revision", "minor_revision"}),
    DriftDomain.CONFIGURATION: frozenset({"data_type", "language"}),
    DriftDomain.NETWORK: frozenset(
        {
            "relationship_type",
            "evidence_class",
            "source_interface_index",
            "source_port_number",
            "confidence",
        }
    ),
}


@dataclass(frozen=True)
class SanitizedDriftFinding:
    """Public-safe finding without target, route, tag, or serial identifiers."""

    reference: str
    domain: str
    change_type: str
    confidence: str
    before: tuple[tuple[str, object], ...] | None
    after: tuple[tuple[str, object], ...] | None
    evidence_protocols: tuple[str, ...]


@dataclass(frozen=True)
class SanitizedDriftReport:
    """Public-safe drift summary with capture provenance."""

    baseline_captured_at: str
    current_captured_at: str
    compared_domains: tuple[str, ...]
    skipped_domains: tuple[str, ...]
    findings: tuple[SanitizedDriftFinding, ...]


def sanitize_discovery_drift(
    result: DiscoveryDriftResult,
) -> SanitizedDriftReport:
    """Remove operational identifiers while retaining reviewable differences."""
    findings = tuple(
        _sanitize_finding(index, finding)
        for index, finding in enumerate(result.findings, start=1)
    )
    return SanitizedDriftReport(
        baseline_captured_at=result.baseline_captured_at.isoformat(),
        current_captured_at=result.current_captured_at.isoformat(),
        compared_domains=tuple(item.value for item in result.compared_domains),
        skipped_domains=tuple(item.value for item in result.skipped_domains),
        findings=findings,
    )


def _sanitize_finding(index: int, finding: DriftFinding) -> SanitizedDriftFinding:
    protocols = tuple(
        sorted(
            {
                evidence.protocol
                for record in (finding.before, finding.after)
                if record is not None
                for evidence in record.evidence
            }
        )
    )
    return SanitizedDriftFinding(
        reference=f"DRIFT-{index:04d}",
        domain=finding.domain.value,
        change_type=finding.change_type.value,
        confidence=_confidence(finding, protocols),
        before=_safe_attributes(finding.before),
        after=_safe_attributes(finding.after),
        evidence_protocols=protocols,
    )


def _safe_attributes(
    record: DriftRecord | None,
) -> tuple[tuple[str, object], ...] | None:
    if record is None:
        return None
    allowed = _SAFE_ATTRIBUTES[record.domain]
    return tuple((key, value) for key, value in record.attributes if key in allowed)


def _confidence(finding: DriftFinding, protocols: tuple[str, ...]) -> str:
    record = finding.after or finding.before
    assert record is not None
    if record.domain is DriftDomain.NETWORK:
        attributes = dict(record.attributes)
        value = attributes.get("confidence")
        if isinstance(value, str):
            return value
    if len(protocols) > 1:
        return "corroborated"
    if protocols:
        return "protocol_reported"
    return "indirect"


def sanitized_discovery_drift_data(
    report: SanitizedDriftReport,
) -> dict[str, Any]:
    """Return JSON-compatible sanitized drift report data."""
    return {
        "sanitized": True,
        "baseline_captured_at": report.baseline_captured_at,
        "current_captured_at": report.current_captured_at,
        "compared_domains": list(report.compared_domains),
        "skipped_domains": list(report.skipped_domains),
        "findings": [
            {
                "reference": item.reference,
                "domain": item.domain,
                "change_type": item.change_type,
                "confidence": item.confidence,
                "before": dict(item.before) if item.before is not None else None,
                "after": dict(item.after) if item.after is not None else None,
                "evidence_protocols": list(item.evidence_protocols),
            }
            for item in report.findings
        ],
    }


def sanitized_discovery_drift_json(report: SanitizedDriftReport) -> str:
    """Serialize a sanitized drift report deterministically."""
    return json.dumps(
        sanitized_discovery_drift_data(report), indent=2, ensure_ascii=False
    ) + "\n"


class DiscoveryDriftMarkdownExporter:
    """Render public-safe drift findings for review or version control."""

    def export(
        self,
        report: SanitizedDriftReport,
        *,
        title: str = "Sanitized discovery drift report",
    ) -> str:
        """Return deterministic Markdown without operational identifiers."""
        lines = [
            f"# {title}",
            "",
            "## Summary",
            "",
            "- Sanitized: yes",
            f"- Baseline captured: `{report.baseline_captured_at}`",
            f"- Current captured: `{report.current_captured_at}`",
            f"- Findings: {len(report.findings)}",
            "- Compared domains: " + _list(report.compared_domains),
            "- Skipped domains: " + _list(report.skipped_domains),
            "",
            "## Findings",
            "",
            "| Reference | Domain | Change | Confidence | Evidence protocols |",
            "| --- | --- | --- | --- | --- |",
        ]
        lines.extend(
            f"| {item.reference} | {item.domain} | {item.change_type} "
            f"| {item.confidence} | {_list(item.evidence_protocols)} |"
            for item in report.findings
        )
        lines.extend(["", "## Safe attributes", ""])
        for item in report.findings:
            lines.extend(
                [
                    f"### {item.reference}",
                    "",
                    f"- Before: {_attributes(item.before)}",
                    f"- After: {_attributes(item.after)}",
                    "",
                ]
            )
        return "\n".join(lines)


def _list(values: tuple[str, ...]) -> str:
    return ", ".join(f"`{value}`" for value in values) if values else "none"


def _attributes(values: tuple[tuple[str, object], ...] | None) -> str:
    if values is None:
        return "not present"
    if not values:
        return "no public-safe attributes"
    return ", ".join(f"`{key}={value}`" for key, value in values)
