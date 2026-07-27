"""Markdown inventory for decoded CODESYS-native visualizations."""

from twinforge.parsers.codesys_native import CodesysNativeExport


class CodesysVisualizationMarkdownExporter:
    """Render evidence extracted from a native CODESYS archive."""

    def export(self, document: CodesysNativeExport) -> str:
        """Return a readable inventory without implying archive portability."""
        lines = [
            "# CODESYS visualization inventory",
            "",
            f"- Profile: {document.profile or 'unknown'}",
            "- Verified profile mappings: "
            + ("applied" if document.profile_mappings_applied else "not applied"),
            f"- Visualizations: {len(document.visualizations)}",
            "",
        ]
        for visualization in document.visualizations:
            size = (
                f"{visualization.width or '?'} × "
                f"{visualization.height or '?'}"
            )
            lines.extend(
                [
                    f"## {visualization.name}",
                    "",
                    f"- Canvas: {size}",
                    f"- Elements: {len(visualization.elements)}",
                    "",
                    "| ID | Identifier | Type | Geometry | Text | Bindings | Actions |",
                    "| --- | --- | --- | --- | --- | --- | --- |",
                ]
            )
            for element in visualization.elements:
                p = element.properties
                geometry = (
                    f"{p.get('x', '?')},{p.get('y', '?')} "
                    f"{p.get('width', '?')}×{p.get('height', '?')}"
                )
                lines.append(
                    "| "
                    + " | ".join(
                        (
                            _cell(
                                str(element.element_id)
                                if element.element_id is not None
                                else None
                            ),
                            _cell(element.identifier),
                            _cell(element.element_type),
                            geometry,
                            _cell(p.get("text")),
                            _cell(", ".join(element.bindings)),
                            _cell(", ".join(a.kind for a in element.actions)),
                        )
                    )
                    + " |"
                )
            lines.append("")
        lines.extend(
            [
                "## Generation boundary",
                "",
                "The native archive is profile-dependent and uses opaque numeric "
                "property identifiers. TwinForge preserves the complete source and "
                "raw element XML, but does not yet generate this format. Numeric "
                "property mappings must be verified against additional CODESYS "
                "exports before generation is considered safe.",
                "",
            ]
        )
        return "\n".join(lines)


def _cell(value: str | None) -> str:
    if not value:
        return "—"
    return value.replace("|", r"\|").replace("\n", " ")
