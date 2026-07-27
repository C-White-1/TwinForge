"""Markdown export for evidence-backed functional descriptions."""

from __future__ import annotations

from twinforge.analysis import DeviceFunctionalDescription


class FunctionalDescriptionMarkdownExporter:
    """Render a concise device functional description."""

    def export(self, report: DeviceFunctionalDescription) -> str:
        """Return deterministic Markdown suitable for engineering review."""

        cyclic = report.cyclic_io
        lines = [
            f"# {report.device_name} functional description",
            "",
            "## Scope and purpose",
            "",
            (
                f"`{report.implementation_name}` represents a "
                f"{report.device_model or 'drive'} controller interface. "
                f"{report.purpose}"
            ),
            "",
            (
                "This document is generated from offline L5X and curated "
                "device-reference evidence. It describes observed software "
                "behavior and does not certify the implemented plant function."
            ),
            "",
            "## Communications",
            "",
            (
                f"- Cyclic protocol: {cyclic.protocol or 'not captured'}, "
                f"RPI {_milliseconds(cyclic.requested_packet_interval_microseconds)}"
            ),
            (
                f"- Drive-to-controller image: connection point "
                f"{_value(cyclic.input_image.connection_point)}, "
                f"{_bytes(cyclic.input_image.configured_size_bytes)}"
            ),
            (
                f"- Controller-to-drive image: connection point "
                f"{_value(cyclic.output_image.connection_point)}, "
                f"{_bytes(cyclic.output_image.configured_size_bytes)}"
            ),
            (
                f"- Explicit parameter inventory: "
                f"{report.observed_parameter_count} observed parameter numbers"
            ),
            "",
            "## Command-source modes",
            "",
            "| Mode | Status | Speed source | Command behavior |",
            "| --- | --- | --- | --- |",
        ]
        lines.extend(
            f"| {mode.name} | `{mode.status_parameter}` "
            f"| {_cell(mode.speed_source)} | {_cell(mode.command_behavior)} |"
            for mode in report.modes
        )
        lines.extend(["", "## Functional behavior", ""])
        for behavior in report.behaviors:
            lines.extend(
                [
                    f"### {behavior.name}",
                    "",
                    behavior.description,
                    "",
                    "Evidence:",
                    "",
                ]
            )
            lines.extend(f"- `{item}`" for item in behavior.evidence)
            lines.append("")
        lines.extend(
            [
                "## Status and diagnostics",
                "",
                (
                    f"- Live diagnostic indications: "
                    f"{len(report.diagnostics.indicators)}"
                ),
                (
                    f"- Configured communication-loss policies: "
                    f"{len(report.diagnostics.policies)}"
                ),
                (
                    f"- Fault-history positions with observed parameter "
                    f"contracts: {len(report.diagnostics.fault_history)}"
                ),
                (
                    "- Active-fault reset uses cyclic LogicCommand bit 3; "
                    "fault-history clearing uses explicit parameter A551 value 2."
                ),
                "",
                "## Engineering boundaries and verification",
                "",
            ]
        )
        lines.extend(f"- {item}" for item in report.boundaries)
        lines.extend(
            [
                "",
                "Related generated evidence:",
                "",
                "- `cyclic_io_contract.md`",
                "- `diagnostic_fault_report.md`",
                "- `parameter_setpoint_report.md` and its CSV companion",
                "- `aoi_qa_issues.md`",
                "",
            ]
        )
        return "\n".join(lines)


def _milliseconds(value: int | None) -> str:
    return "not captured" if value is None else f"{value / 1000:g} ms"


def _value(value: object | None) -> str:
    return "not captured" if value is None else str(value)


def _bytes(value: int | None) -> str:
    return "size not captured" if value is None else f"{value} bytes"


def _cell(value: str) -> str:
    return value.replace("|", r"\|").replace("\n", " ")
