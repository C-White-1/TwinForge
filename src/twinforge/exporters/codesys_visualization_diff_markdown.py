"""Markdown reporting for controlled CODESYS visualization experiments."""

from twinforge.analysis.codesys_visualization_diff import (
    CodesysVisualizationDiff,
)


class CodesysVisualizationDiffMarkdownExporter:
    """Render observed archive changes without assigning guessed semantics."""

    def export(self, result: CodesysVisualizationDiff) -> str:
        """Return a lint-compatible differential-evidence report."""
        lines = [
            "# CODESYS visualization differential evidence",
            "",
            f"- Before profile: {_value(result.profile_before)}",
            f"- After profile: {_value(result.profile_after)}",
            f"- Changed elements: {len(result.element_changes)}",
            "",
            "## Element changes",
            "",
        ]
        if not result.element_changes:
            lines.extend(["No element changes were observed.", ""])
        for element in result.element_changes:
            lines.extend(
                [
                    f"### {element.visualization} / {element.element_key}",
                    "",
                    f"- Change: {element.change_kind}",
                    f"- Type: {_value(element.element_type)}",
                    "",
                    "| Property ID | Known name | Before | After |",
                    "| --- | --- | --- | --- |",
                ]
            )
            if element.property_changes:
                for change in element.property_changes:
                    lines.append(
                        f"| {_value(change.property_id)} "
                        f"| {_value(change.property_name)} "
                        f"| {_value(change.before)} "
                        f"| {_value(change.after)} |"
                    )
            else:
                lines.append("| — | — | — | — |")
            lines.extend(
                [
                    "",
                    f"- Bindings before: {_items(element.bindings_before)}",
                    f"- Bindings after: {_items(element.bindings_after)}",
                    f"- Actions before: {_items(element.actions_before)}",
                    f"- Actions after: {_items(element.actions_after)}",
                    "",
                ]
            )
            if element.action_property_changes:
                lines.extend(
                    [
                        "| Action | Property | Before | After |",
                        "| --- | --- | --- | --- |",
                    ]
                )
                for change in element.action_property_changes:
                    lines.append(
                        f"| {_value(change.action)} "
                        f"| {_value(change.property_name)} "
                        f"| {_value(change.before)} "
                        f"| {_value(change.after)} |"
                    )
                lines.append("")
        lines.extend(["## Visualization Manager changes", ""])
        if result.manager_changes:
            lines.extend(
                [
                    "| Setting | Before | After |",
                    "| --- | --- | --- |",
                ]
            )
            for change in result.manager_changes:
                lines.append(
                    f"| {_value(change.property_name)} "
                    f"| {_value(change.before)} "
                    f"| {_value(change.after)} |"
                )
            lines.append("")
        else:
            lines.extend(["No manager changes were observed.", ""])
        lines.extend(
            [
                "## Interpretation rule",
                "",
                "An opaque property ID is not assigned a meaning from a single "
                "coincidence. A mapping becomes a candidate only when controlled "
                "exports vary one editor property at a time, and should be treated "
                "as profile-specific until repeated across CODESYS profiles.",
                "",
            ]
        )
        return "\n".join(lines)


def _value(value: str | None) -> str:
    if value is None or value == "":
        return "—"
    return value.replace("|", r"\|").replace("\n", " ")


def _items(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "—"
