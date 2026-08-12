"""Markdown reporting for PLX50 PROFIBUS-to-Logix correlations."""

from __future__ import annotations

from twinforge.assembly import Plx50LogixMappingResult


class Plx50LogixMappingMarkdownExporter:
    """Render generated assembly and controller-tag evidence for review."""

    def export(
        self,
        result: Plx50LogixMappingResult,
        *,
        title: str = "PLX50 Logix mapping",
    ) -> str:
        """Return deterministic Markdown without inferring missing mappings."""

        lines = [
            f"# {title}",
            "",
            "<!-- markdownlint-disable MD013 -->",
            "",
            (
                "This report correlates native PLX50 PROFIBUS configuration "
                "with controller tags and module assembly operands explicitly "
                "present in the generated Logix mapping routine."
            ),
            "",
            f"- Generated CPS transfers: {len(result.transfers)}",
            f"- Correlated PROFIBUS points: {len(result.correlations)}",
            f"- Unresolved PROFIBUS points: {len(result.unresolved_points)}",
            "",
            "## Point correlations",
            "",
            (
                "| Direction | PROFIBUS point | Controller tag | Assembly "
                "operand | CPS length | Type | Bytes |"
            ),
            "| --- | --- | --- | --- | ---: | --- | ---: |",
        ]
        for item in result.correlations:
            direction = (
                "PROFIBUS DP → EtherNet/IP"
                if item.point_type == "Input"
                else "EtherNet/IP → PROFIBUS DP"
            )
            lines.append(
                f"| {direction} | `{_cell(item.profibus_reference)}` "
                f"| `{_cell(item.controller_tag_path)}` "
                f"| `{_cell(item.assembly_reference)}` "
                f"| {item.copy_length} | `{_cell(item.data_type or 'unknown')}` "
                f"| {_value(item.byte_length)} |"
            )
        if not result.correlations:
            lines.append("| — | — | — | — | — | — | — |")

        lines.extend(
            [
                "",
                "## Generated CPS transfers",
                "",
                "| Assembly operand | Controller tag | Direction | CPS length |",
                "| --- | --- | --- | ---: |",
            ]
        )
        for item in result.transfers:
            direction = "input" if item.direction == "I" else "output"
            lines.append(
                f"| `{_cell(item.assembly_reference)}` "
                f"| `{_cell(item.controller_tag)}` "
                f"| {direction} | {item.copy_length} |"
            )
        if not result.transfers:
            lines.append("| — | — | — | — |")

        lines.extend(["", "## Unresolved evidence", ""])
        if result.unresolved_points:
            lines.extend(
                f"- `{_cell(item)}`" for item in result.unresolved_points
            )
        else:
            lines.append("No unresolved PROFIBUS points.")

        lines.extend(["", "## Diagnostics", ""])
        if result.diagnostics:
            lines.extend(
                f"- `{item.code}`: {item.message}"
                for item in result.diagnostics
            )
        else:
            lines.append("No correlation diagnostics.")
        lines.append("")
        return "\n".join(lines)


def _cell(value: str) -> str:
    return value.replace("|", r"\|").replace("\n", " ")


def _value(value: object | None) -> str:
    return "—" if value is None else str(value)
