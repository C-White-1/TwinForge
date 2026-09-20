"""Markdown/CSV/JSON export for the SFC test-coverage/traceability skeleton."""
from __future__ import annotations

import csv
from dataclasses import asdict
import json
from io import StringIO

from twinforge.analysis.sfc_coverage import SFCCoverageReport

_CSV_FIELDS = (
    "Key", "Program", "Routine", "Chart", "Type", "Element", "Description",
    "ConnectivityStatus", "DiagnosticCode", "RequirementID", "TestID", "Status",
)


class SFCCoverageMarkdownExporter:
    """Render the coverage skeleton without presenting it as test completion."""

    def export(self, report: SFCCoverageReport) -> str:
        """Return a deterministic Markdown traceability skeleton."""
        lines = [
            f"# {report.controller_name} SFC test-coverage skeleton",
            "",
            "This lists every step, every transition, and every SFC-relevant "
            "diagnostic TwinForge found. It is a starting point for a test "
            "matrix, not a record of tests performed or a safety approval. "
            "Requirement ID, Test ID and Status are blank for a reviewer to "
            "fill in; regenerating this file replaces it and does not merge "
            "back those annotations.",
            "",
            "## Summary",
            "",
            f"- Steps: {report.step_count}",
            f"- Transitions: {report.transition_count}",
            f"- Unresolved connectivity (steps/transitions with no traced successor): "
            f"{report.unresolved_connectivity_count}",
            f"- SFC-relevant diagnostics: {report.diagnostic_count}",
            "",
            "## Coverage items",
            "",
            "| Program | Routine | Chart | Type | Element | Description | "
            "Connectivity | Diagnostic | Requirement ID | Test ID | Status |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        lines.extend(
            "| " + " | ".join((
                _cell(item.program_name), _cell(item.routine_name),
                _cell(item.chart_name or f"chart{item.chart_index}" if item.chart_index >= 0 else "—"),
                item.item_type, _cell(item.element_name or "—"), _cell(item.description),
                item.connectivity_status, _cell(item.diagnostic_code or "—"), "", "", "",
            )) + " |"
            for item in report.items
        )
        return "\n".join(lines).rstrip() + "\n"


class SFCCoverageCSVExporter:
    """Render the coverage skeleton as an editable spreadsheet import."""

    def export(self, report: SFCCoverageReport) -> str:
        """Return deterministic UTF-8-ready coverage CSV text, blank for a reviewer to fill in."""
        stream = StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=_CSV_FIELDS)
        writer.writeheader()
        for item in report.items:
            writer.writerow({
                "Key": item.key, "Program": item.program_name, "Routine": item.routine_name,
                "Chart": item.chart_name or (f"chart{item.chart_index}" if item.chart_index >= 0 else ""),
                "Type": item.item_type, "Element": item.element_name or "",
                "Description": item.description, "ConnectivityStatus": item.connectivity_status,
                "DiagnosticCode": item.diagnostic_code or "",
                "RequirementID": "", "TestID": "", "Status": "",
            })
        return stream.getvalue()


def sfc_coverage_data(report: SFCCoverageReport) -> dict[str, object]:
    """Return deterministic JSON-compatible coverage data."""
    return {
        "schema_version": "twinforge.sfc-coverage.v1",
        "controller_name": report.controller_name,
        "summary": {
            "step_count": report.step_count,
            "transition_count": report.transition_count,
            "unresolved_connectivity_count": report.unresolved_connectivity_count,
            "diagnostic_count": report.diagnostic_count,
        },
        "items": [asdict(item) for item in report.items],
    }


def sfc_coverage_json(report: SFCCoverageReport) -> str:
    """Serialize the coverage skeleton deterministically."""
    return json.dumps(sfc_coverage_data(report), indent=2) + "\n"


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
