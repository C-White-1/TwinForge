"""Markdown and CSV exports for module and spare-I/O schedules."""

from __future__ import annotations

import csv
from io import StringIO

from twinforge.analysis.module_schedule import ModuleScheduleReport


class ModuleScheduleMarkdownExporter:
    """Render module capacity without hiding unknown capability."""

    def export(
        self,
        report: ModuleScheduleReport,
        *,
        title: str = "Module and spare-I/O schedule",
    ) -> str:
        """Return deterministic review-oriented Markdown."""
        lines = [
            f"# {title}",
            "",
            "Spare counts mean no explicit software alias assignment was observed. "
            "They require wiring and configuration review. Unknown capability is "
            "retained rather than treated as zero capacity.",
            "",
            f"- Modules: {len(report.modules)}",
            "- Modules with known I/O capability: "
            f"{sum(item.capability_status == 'known' for item in report.modules)}",
            "- Modules with unknown I/O capability: "
            f"{sum(item.capability_status == 'unknown' for item in report.modules)}",
            "- Assigned channels: "
            f"{sum(item.assigned_channels for item in report.modules)}",
            "- Spare candidates: "
            f"{sum(item.spare_candidates for item in report.modules)}",
            "- Unavailable by configuration: "
            f"{sum(item.unavailable_by_configuration for item in report.modules)}",
            "",
            "| Chassis | Parent | Slot/address | Module | Catalog | Vendor | Signal | "
            "Direction | Nominal | Configured | Assigned | Spare candidates | "
            "Unavailable | Capability | Source | Inhibited | Fault on loss | Keying |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | "
            "--- | --- | --- | --- | --- | --- | --- |",
        ]
        for item in report.modules:
            slot_or_address = item.slot if item.slot is not None else item.address
            lines.append(
                f"| {_cell(item.chassis)} | {_cell(item.parent_module)} "
                f"| {_cell(slot_or_address)} | {_cell(item.module_name)} "
                f"| {_cell(item.catalog_number)} | {_cell(item.vendor)} "
                f"| {_cell(item.signal_type)} | {_cell(item.direction)} "
                f"| {_cell(item.nominal_channels)} "
                f"| {_cell(item.configured_channels)} | {item.assigned_channels} "
                f"| {item.spare_candidates} "
                f"| {item.unavailable_by_configuration} "
                f"| {item.capability_status} | {_cell(item.capability_source)} "
                f"| {_cell(item.inhibited)} "
                f"| {_cell(item.major_fault_on_connection_loss)} "
                f"| {_cell(item.electronic_keying)} |"
            )
        return "\n".join(lines).rstrip() + "\n"


class ModuleScheduleCSVExporter:
    """Render one complete row per modeled module."""

    _FIELDS: tuple[str, ...] = (
        "Chassis",
        "ParentModule",
        "Slot",
        "Address",
        "Module",
        "CatalogNumber",
        "Vendor",
        "SignalType",
        "Direction",
        "NominalChannels",
        "ConfiguredChannels",
        "AssignedChannels",
        "SpareCandidates",
        "UnavailableByConfiguration",
        "CapabilityStatus",
        "CapabilitySource",
        "Inhibited",
        "MajorFaultOnConnectionLoss",
        "ElectronicKeying",
    )

    def export(self, report: ModuleScheduleReport) -> str:
        """Return deterministic UTF-8-ready CSV text."""
        stream = StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=self._FIELDS)
        writer.writeheader()
        for item in report.modules:
            writer.writerow(
                {
                    "Chassis": item.chassis or "",
                    "ParentModule": item.parent_module or "",
                    "Slot": item.slot if item.slot is not None else "",
                    "Address": item.address or "",
                    "Module": item.module_name,
                    "CatalogNumber": item.catalog_number,
                    "Vendor": item.vendor or "",
                    "SignalType": item.signal_type or "",
                    "Direction": item.direction or "",
                    "NominalChannels": item.nominal_channels
                    if item.nominal_channels is not None
                    else "",
                    "ConfiguredChannels": item.configured_channels
                    if item.configured_channels is not None
                    else "",
                    "AssignedChannels": item.assigned_channels,
                    "SpareCandidates": item.spare_candidates,
                    "UnavailableByConfiguration": item.unavailable_by_configuration,
                    "CapabilityStatus": item.capability_status,
                    "CapabilitySource": item.capability_source or "",
                    "Inhibited": item.inhibited if item.inhibited is not None else "",
                    "MajorFaultOnConnectionLoss": item.major_fault_on_connection_loss
                    if item.major_fault_on_connection_loss is not None
                    else "",
                    "ElectronicKeying": item.electronic_keying or "",
                }
            )
        return stream.getvalue()


def _cell(value: object | None) -> str:
    if value is None or value == "":
        return "—"
    return str(value).replace("|", "\\|").replace("\n", " ")
