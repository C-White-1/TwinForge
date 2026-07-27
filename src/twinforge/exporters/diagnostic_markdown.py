"""Markdown export for device diagnostic and fault reports."""

from __future__ import annotations

from twinforge.analysis import DeviceDiagnosticReport


class DeviceDiagnosticMarkdownExporter:
    """Render separated diagnostic evidence for engineering review."""

    def export(self, report: DeviceDiagnosticReport) -> str:
        """Return deterministic Markdown."""

        lines = [
            f"# {report.device_name} diagnostic and fault report",
            "",
            (
                f"Source implementation: `{report.implementation_name}`. "
                "This is an offline evidence report; blank runtime values are "
                "not interpreted as healthy or fault-free."
            ),
            "",
            "## Live diagnostic contract",
            "",
            "| Layer | Signal | Source | Meaning | Visible |",
            "| --- | --- | --- | --- | :---: |",
        ]
        lines.extend(
            f"| {item.layer} | `{item.name}` | `{item.source or '—'}` "
            f"| {_cell(item.meaning)} | {_yes_no(item.visible)} |"
            for item in report.indicators
        )
        lines.extend(
            [
                "",
                "## Communication-loss policies",
                "",
                "| Parameter | Purpose | Offline configured value | Source |",
                "| --- | --- | --- | --- |",
            ]
        )
        lines.extend(
            f"| `{item.code}` {item.name} | {_cell(item.purpose)} "
            f"| {_configured(item.configured_value, item.configured_label)} "
            f"| `{item.source or 'not captured'}` |"
            for item in report.policies
        )
        lines.extend(
            [
                "",
                "## Fault-history contract",
                "",
                (
                    "Entry 1 is the most recent unique fault. Codes are paired "
                    "with the captured operating snapshots below."
                ),
                "",
                "| Entry | Code | Frequency (Hz) | Current (A) "
                "| DC bus voltage (V DC) |",
                "| ---: | --- | --- | --- | --- |",
            ]
        )
        lines.extend(
            f"| {item.position} | `{item.code_parameter or '—'}` "
            f"| `{item.frequency_parameter or '—'}` "
            f"| `{item.current_parameter or '—'}` "
            f"| `{item.bus_voltage_parameter or '—'}` |"
            for item in report.fault_history
        )
        lines.extend(["", "## Fault commands", ""])
        for command in report.commands:
            lines.extend(
                [
                    f"### {command.name}",
                    "",
                    f"- Sources: `{command.source or 'not captured'}`",
                    f"- Effect: {command.effect}",
                ]
            )
            if command.evidence:
                lines.append("- Evidence:")
                lines.append("")
                lines.extend(f"  - `{item}`" for item in command.evidence)
            lines.append("")
        lines.extend(["## Important boundaries", ""])
        lines.extend(f"- {item}" for item in report.limitations)
        lines.append("")
        return "\n".join(lines)


def _cell(value: str | None) -> str:
    return (value or "—").replace("|", r"\|").replace("\n", " ")


def _yes_no(value: bool | None) -> str:
    if value is None:
        return "—"
    return "yes" if value else "no"


def _configured(value: str | None, label: str | None) -> str:
    if value is None:
        return "not captured"
    return f"`{value}` ({label})" if label else f"`{value}`"
