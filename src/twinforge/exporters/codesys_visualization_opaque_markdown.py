"""Markdown report for opaque CODESYS visualization properties."""

from twinforge.analysis.codesys_visualization_opaque import (
    CodesysOpaqueProperty,
)


class CodesysVisualizationOpaqueMarkdownExporter:
    """Render a ranked experiment register without guessing property names."""

    def export(
        self,
        properties: tuple[CodesysOpaqueProperty, ...],
        *,
        profile: str | None,
    ) -> str:
        """Return deterministic Markdown."""

        lines = [
            "# CODESYS opaque visualization-property register",
            "",
            f"- Profile: {profile or 'unknown'}",
            f"- Unmapped property IDs: {len(properties)}",
            "- Promotion rule: controlled differential evidence on compatible "
            "controls",
            "",
            "| Property ID | Occurrences | Element types | Preserved samples |",
            "| --- | ---: | --- | --- |",
        ]
        lines.extend(
            f"| `{item.property_id}` | {item.occurrences} "
            f"| {_cell(', '.join(item.element_types))} "
            f"| {_cell(', '.join(_sample(v) for v in item.sample_values))} |"
            for item in properties
        )
        lines.extend(
            [
                "",
                "## Interpretation boundary",
                "",
                (
                    "Names are deliberately absent. Repeated values such as "
                    "alignment, font, color, or Boolean-looking tokens are "
                    "experiment candidates, not sufficient mapping evidence."
                ),
                "",
                (
                    "Every value remains preserved in the parsed source "
                    "extension and source-backed native export."
                ),
                "",
            ]
        )
        return "\n".join(lines)


def _sample(value: str) -> str:
    stripped = value.strip()
    return f"`{stripped}`" if stripped else "`<empty>`"


def _cell(value: str) -> str:
    return value.replace("|", r"\|").replace("\n", " ")
