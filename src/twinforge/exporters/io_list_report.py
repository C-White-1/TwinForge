"""Markdown and CSV renderers for the vendor-neutral I/O schedule."""

from __future__ import annotations

import csv
from collections import Counter
from io import StringIO

from twinforge.analysis.io_list import IOListReport


class IOListMarkdownExporter:
    """Render known channels, assignments, spares, and unresolved aliases."""

    def export(
        self,
        report: IOListReport,
        *,
        title: str = "I/O list",
    ) -> str:
        """Return deterministic review-oriented Markdown."""
        counts = Counter(item.assignment_status for item in report.channels)
        lines = [
            f"# {title}",
            "",
            "Channels are emitted only from modeled module capability. A spare "
            "means no explicit alias assignment was observed; it does not prove "
            "the physical terminal is unused.",
            "",
            f"- Channels: {len(report.channels)}",
            f"- Assigned: {counts['assigned']}",
            f"- Spare candidates: {counts['spare']}",
            "- Unavailable by configuration: "
            f"{counts['unavailable_by_configuration']}",
            f"- Unresolved local aliases: {len(report.unresolved_aliases)}",
            "",
            "## Channels",
            "",
            "| Chassis | Slot | Module | Catalog | Vendor | Signal | Direction | "
            "Channel | Operand | Status | Tags | Description | Units | Lower | "
            "Upper | Capability evidence |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | "
            "--- | --- | --- | --- | --- |",
        ]
        for item in report.channels:
            lines.append(
                f"| {_cell(item.chassis)} | {_cell(item.slot)} "
                f"| {_cell(item.module_name)} | {_cell(item.catalog_number)} "
                f"| {_cell(item.vendor)} | {item.signal_type.value} "
                f"| {item.direction.value} | {item.channel} "
                f"| {_cell(item.source_operand)} | {item.assignment_status} "
                f"| {_cell('; '.join(item.assigned_tags))} "
                f"| {_cell('; '.join(item.descriptions))} "
                f"| {_cell(item.engineering_unit)} | {_cell(item.lower_range)} "
                f"| {_cell(item.upper_range)} | {_cell(item.capability_source)} |"
            )
        lines.extend(
            [
                "",
                "## Unresolved local aliases",
                "",
                "| Tag | Alias target | Reason |",
                "| --- | --- | --- |",
            ]
        )
        for item in report.unresolved_aliases:
            lines.append(
                f"| {_cell(item.tag_name)} | {_cell(item.alias_for)} "
                f"| {_cell(item.reason)} |"
            )
        return "\n".join(lines).rstrip() + "\n"


class IOListCSVExporter:
    """Render a complete row for each known physical channel."""

    _FIELDS = (
        "Chassis",
        "Slot",
        "Module",
        "CatalogNumber",
        "Vendor",
        "SignalType",
        "Direction",
        "Channel",
        "Member",
        "SourceOperand",
        "AssignmentStatus",
        "AssignedTags",
        "Descriptions",
        "EngineeringUnit",
        "LowerRange",
        "UpperRange",
        "CapabilitySource",
    )

    def export(self, report: IOListReport) -> str:
        """Return deterministic UTF-8-ready CSV text."""
        stream = StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=self._FIELDS)
        writer.writeheader()
        for item in report.channels:
            writer.writerow(
                {
                    "Chassis": item.chassis or "",
                    "Slot": item.slot if item.slot is not None else "",
                    "Module": item.module_name,
                    "CatalogNumber": item.catalog_number,
                    "Vendor": item.vendor or "",
                    "SignalType": item.signal_type.value,
                    "Direction": item.direction.value,
                    "Channel": item.channel,
                    "Member": item.member,
                    "SourceOperand": item.source_operand or "",
                    "AssignmentStatus": item.assignment_status,
                    "AssignedTags": ";".join(item.assigned_tags),
                    "Descriptions": ";".join(item.descriptions),
                    "EngineeringUnit": item.engineering_unit or "",
                    "LowerRange": (
                        item.lower_range if item.lower_range is not None else ""
                    ),
                    "UpperRange": (
                        item.upper_range if item.upper_range is not None else ""
                    ),
                    "CapabilitySource": item.capability_source,
                }
            )
        return stream.getvalue()


def _cell(value: object | None) -> str:
    if value is None or value == "":
        return "—"
    return str(value).replace("|", "\\|").replace("\n", " ")
