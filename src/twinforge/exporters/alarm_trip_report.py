"""Review-oriented Markdown and CSV exports for alarm/trip candidates."""

from __future__ import annotations

import csv
from collections import Counter
from io import StringIO

from twinforge.analysis.alarm_candidates import AlarmTripCandidateReport


class AlarmTripCandidateMarkdownExporter:
    """Render evidence-bound candidates without inventing alarm philosophy."""

    def export(
        self,
        report: AlarmTripCandidateReport,
        *,
        title: str = "Alarm and trip candidate report",
    ) -> str:
        """Return deterministic, reviewable Markdown."""
        counts = Counter(
            kind.value
            for candidate in report.candidates
            for kind in candidate.kinds
        )
        lines = [
            f"# {title}",
            "",
            "This is an evidence-bound candidate list, not a verified alarm "
            "philosophy. Unknown fields are not inferred from naming alone.",
            "",
            f"- Candidates: {len(report.candidates)}",
            f"- Alarm classifications: {counts['alarm']}",
            f"- Trip classifications: {counts['trip']}",
            "",
            "| Tag | Scope | Kind | Description | Priority | Setpoint | Units | "
            "Delay | Latching | Acknowledgement | Suppression | Shutdown action | "
            "Applicability | Readers | Writers | Aliases | Classification evidence |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | "
            "--- | --- | --- | --- | --- | --- |",
        ]
        for item in report.candidates:
            scope = item.tag_scope.value
            if item.program_name:
                scope = f"{scope}: {item.program_name}"
            lines.append(
                f"| {_cell(item.tag_name)} | {_cell(scope)} "
                f"| {_cell(', '.join(kind.value for kind in item.kinds))} "
                f"| {_cell(item.description)} | {_cell(item.priority)} "
                f"| {_cell(item.setpoint)} | {_cell(item.engineering_unit)} "
                f"| {_cell(item.delay)} | {_cell(item.latching)} "
                f"| {_cell(item.acknowledgement)} | {_cell(item.suppression)} "
                f"| {_cell(item.shutdown_action)} | {_cell(item.applicability)} "
                f"| {_cell('; '.join(item.reader_locations))} "
                f"| {_cell('; '.join(item.writer_locations))} "
                f"| {_cell('; '.join(item.alias_source_keys))} "
                f"| {_cell('; '.join(item.classification_evidence))} |"
            )
        return "\n".join(lines).rstrip() + "\n"


class AlarmTripCandidateCSVExporter:
    """Render one complete review row per candidate."""

    _FIELDS = (
        "TagKey",
        "TagName",
        "Scope",
        "Program",
        "Kind",
        "Description",
        "Priority",
        "Setpoint",
        "EngineeringUnit",
        "Delay",
        "Latching",
        "Acknowledgement",
        "Suppression",
        "ShutdownAction",
        "Applicability",
        "Readers",
        "Writers",
        "AliasSources",
        "ClassificationEvidence",
    )

    def export(self, report: AlarmTripCandidateReport) -> str:
        """Return deterministic UTF-8-ready CSV text."""
        stream = StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=self._FIELDS)
        writer.writeheader()
        for item in report.candidates:
            writer.writerow(
                {
                    "TagKey": item.tag_key,
                    "TagName": item.tag_name,
                    "Scope": item.tag_scope.value,
                    "Program": item.program_name or "",
                    "Kind": ";".join(kind.value for kind in item.kinds),
                    "Description": item.description or "",
                    "Priority": item.priority or "",
                    "Setpoint": item.setpoint or "",
                    "EngineeringUnit": item.engineering_unit or "",
                    "Delay": item.delay or "",
                    "Latching": item.latching or "",
                    "Acknowledgement": item.acknowledgement or "",
                    "Suppression": item.suppression or "",
                    "ShutdownAction": item.shutdown_action or "",
                    "Applicability": item.applicability or "",
                    "Readers": ";".join(item.reader_locations),
                    "Writers": ";".join(item.writer_locations),
                    "AliasSources": ";".join(item.alias_source_keys),
                    "ClassificationEvidence": ";".join(
                        item.classification_evidence
                    ),
                }
            )
        return stream.getvalue()


def _cell(value: object | None) -> str:
    if value is None or value == "":
        return "—"
    return str(value).replace("|", "\\|").replace("\n", " ")
