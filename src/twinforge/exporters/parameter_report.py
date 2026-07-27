"""Markdown and CSV exports for vendor-neutral parameter reports."""

from __future__ import annotations

import csv
from io import StringIO

from twinforge.analysis.parameter_report import (
    ParameterReportEntry,
    ParameterSetpointReport,
)


_CSV_FIELDS = (
    "Number",
    "Code",
    "Name",
    "Group",
    "Purpose",
    "ConfiguredValue",
    "ConfiguredValueLabel",
    "ConfiguredValueAssessment",
    "ConfiguredValueSource",
    "ConfigurationNote",
    "RuntimeValue",
    "RuntimeValueSource",
    "EngineeringUnit",
    "Minimum",
    "Maximum",
    "Default",
    "Resolution",
    "ObservedRead",
    "ObservedWrite",
    "ReadOnly",
    "ChangeRequiresStop",
    "AdvisorySeverity",
    "AdvisoryCodes",
    "AdvisorySummaries",
    "Reference",
    "Evidence",
)


class ParameterReportMarkdownExporter:
    """Render a concise engineering view of parameter and setpoint evidence."""

    def export(
        self,
        report: ParameterSetpointReport,
        *,
        title: str | None = None,
    ) -> str:
        """Return deterministic Markdown without claiming unavailable values."""

        configured_count = sum(
            entry.configured_value is not None for entry in report.entries
        )
        runtime_count = sum(
            entry.runtime_value is not None for entry in report.entries
        )
        interpreted_count = sum(
            entry.configured_value_label is not None
            for entry in report.entries
        )
        verified_count = sum(
            entry.configured_value_assessment
            in {"Documented option", "Within documented range"}
            for entry in report.entries
        )
        exception_count = sum(
            entry.configured_value_assessment
            in {"Undocumented option", "Outside documented range"}
            for entry in report.entries
        )
        advisory_count = sum(bool(entry.advisory_codes) for entry in report.entries)
        high_advisory_count = sum(
            entry.advisory_severity == "High" for entry in report.entries
        )
        lines = [
            f"# {title or f'{report.device_name} parameter and setpoint report'}",
            "",
            (
                "Configured values are shown only when recoverable from "
                "offline source evidence. Runtime values require a separate "
                "online or captured-data source."
            ),
            "",
            (
                f"- Configured-value evidence: {configured_count}/"
                f"{len(report.entries)} parameters"
            ),
            (
                f"- Runtime-value evidence: {runtime_count}/"
                f"{len(report.entries)} parameters"
            ),
            (
                f"- Interpreted configured values: {interpreted_count}/"
                f"{configured_count}"
            ),
            (
                f"- Mechanically verified configured values: "
                f"{verified_count}/{configured_count}"
            ),
            f"- Configuration assessment exceptions: {exception_count}",
            f"- Parameters with QA advisories: {advisory_count}",
            f"- Parameters with high-severity advisories: {high_advisory_count}",
            "",
            "| Code | Name | Group | Configured value | Meaning | Assessment | "
            "Configuration note | Runtime value | Units | Range | Default | "
            "Access | Stop required | QA advisories |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | "
            "--- | --- | :---: | --- |",
        ]
        for entry in report.entries:
            access = _access(entry.observed_read, entry.observed_write)
            lines.append(
                f"| {_cell(entry.code or str(entry.number))} "
                f"| {_cell(entry.name)} "
                f"| {_cell(entry.group)} "
                f"| {_cell(entry.configured_value)} "
                f"| {_cell(entry.configured_value_label)} "
                f"| {_cell(entry.configured_value_assessment)} "
                f"| {_cell(entry.configuration_note)} "
                f"| {_cell(entry.runtime_value)} "
                f"| {_cell(entry.engineering_unit)} "
                f"| {_cell(_range(entry.minimum, entry.maximum))} "
                f"| {_cell(entry.default)} "
                f"| {access} "
                f"| {_optional_yes_no(entry.change_requires_stop)} "
                f"| {_cell(_advisory_text(entry))} |"
            )
        _append_review_priorities(lines, report)
        return "\n".join(lines).rstrip() + "\n"


class ParameterReportCSVExporter:
    """Render the complete parameter report contract as UTF-8-ready CSV."""

    def export(self, report: ParameterSetpointReport) -> str:
        """Return deterministic CSV text suitable for writing as UTF-8."""

        stream = StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=_CSV_FIELDS)
        writer.writeheader()
        for entry in report.entries:
            writer.writerow(
                {
                    "Number": entry.number,
                    "Code": entry.code or "",
                    "Name": entry.name or "",
                    "Group": entry.group or "",
                    "Purpose": entry.purpose or "",
                    "ConfiguredValue": entry.configured_value or "",
                    "ConfiguredValueLabel": (
                        entry.configured_value_label or ""
                    ),
                    "ConfiguredValueAssessment": (
                        entry.configured_value_assessment or ""
                    ),
                    "ConfiguredValueSource": (
                        entry.configured_value_source or ""
                    ),
                    "ConfigurationNote": entry.configuration_note or "",
                    "RuntimeValue": entry.runtime_value or "",
                    "RuntimeValueSource": entry.runtime_value_source or "",
                    "EngineeringUnit": entry.engineering_unit or "",
                    "Minimum": entry.minimum or "",
                    "Maximum": entry.maximum or "",
                    "Default": entry.default or "",
                    "Resolution": entry.resolution or "",
                    "ObservedRead": _yes_no(entry.observed_read),
                    "ObservedWrite": _yes_no(entry.observed_write),
                    "ReadOnly": _optional_yes_no(entry.read_only),
                    "ChangeRequiresStop": _optional_yes_no(
                        entry.change_requires_stop
                    ),
                    "AdvisorySeverity": entry.advisory_severity or "",
                    "AdvisoryCodes": "; ".join(entry.advisory_codes),
                    "AdvisorySummaries": "\n".join(
                        entry.advisory_summaries
                    ),
                    "Reference": entry.reference or "",
                    "Evidence": "\n".join(entry.evidence),
                }
            )
        return stream.getvalue()


def _cell(value: str | None) -> str:
    if value is None or value == "":
        return "—"
    return value.replace("|", "\\|").replace("\n", "<br>")


def _range(minimum: str | None, maximum: str | None) -> str | None:
    if minimum is None and maximum is None:
        return None
    return f"{minimum or '—'} to {maximum or '—'}"


def _access(observed_read: bool, observed_write: bool) -> str:
    if observed_read and observed_write:
        return "read/write"
    if observed_read:
        return "read"
    if observed_write:
        return "write"
    return "not observed"


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _optional_yes_no(value: bool | None) -> str:
    if value is None:
        return "unknown"
    return _yes_no(value)


def _advisory_text(entry: ParameterReportEntry) -> str | None:
    if not entry.advisory_codes:
        return None
    codes = ", ".join(entry.advisory_codes)
    return f"{entry.advisory_severity}: {codes}"


def _append_review_priorities(
    lines: list[str],
    report: ParameterSetpointReport,
) -> None:
    priorities = [
        entry
        for entry in report.entries
        if entry.advisory_severity in {"High", "Medium"}
    ]
    if not priorities:
        return
    lines.extend(
        [
            "",
            "## Review priorities",
            "",
            (
                "These are evidence-backed manual-review findings, not "
                "confirmed runtime defects."
            ),
        ]
    )
    for severity in ("High", "Medium"):
        entries = [
            entry
            for entry in priorities
            if entry.advisory_severity == severity
        ]
        if not entries:
            continue
        lines.extend(["", f"### {severity}", ""])
        for entry in entries:
            configured = _configured_context(entry)
            summaries = (
                "; ".join(
                    summary.rstrip(".")
                    for summary in entry.advisory_summaries
                )
                + "."
            )
            lines.append(
                f"- `{entry.code or entry.number}` {_cell(entry.name)}"
                f"{configured}: {', '.join(entry.advisory_codes)} — "
                f"{summaries}"
            )


def _configured_context(entry: ParameterReportEntry) -> str:
    if entry.configured_value is None:
        return ""
    meaning = (
        f" ({entry.configured_value_label})"
        if entry.configured_value_label is not None
        else ""
    )
    return f"; configured `{entry.configured_value}`{meaning}"
