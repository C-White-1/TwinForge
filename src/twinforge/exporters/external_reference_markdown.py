"""Markdown export for configured external-reference evidence."""

from __future__ import annotations

from twinforge.analysis.external_references import ExternalReferenceInventory


class ExternalReferenceMarkdownExporter:
    """Render external addresses and controller references for review."""

    def export(
        self,
        inventory: ExternalReferenceInventory,
        *,
        title: str = "External address and controller-reference inventory",
    ) -> str:
        """Return deterministic Markdown without inferring reachable devices."""
        lines = [
            f"# {title}",
            "",
            "This inventory contains configured references observed in the L5X. "
            "It does not prove that a target exists, is reachable, or belongs to "
            "the same exported project.",
            "",
            f"- Controller: {_cell(inventory.controller_name)}",
            f"- External-reference fields: {len(inventory.references)}",
            "",
            "| Kind | Value | Source type | Source | Scope | Field |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for item in inventory.references:
            lines.append(
                f"| {item.kind.value} | {_cell(item.value)} "
                f"| {_cell(item.source_type)} | {_cell(item.source_name)} "
                f"| {_cell(item.source_scope)} | {_cell(item.source_field)} |"
            )
        return "\n".join(lines).rstrip() + "\n"


def _cell(value: object | None) -> str:
    if value is None or value == "":
        return "—"
    return str(value).replace("|", "\\|").replace("\n", " ")
