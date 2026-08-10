"""Markdown and CSV exports for tag cross-reference evidence."""

from __future__ import annotations

import csv
from collections import Counter
from io import StringIO

from twinforge.analysis.tag_dependencies import TagDependencyGraph


class TagDependencyMarkdownExporter:
    """Render a reviewable signal and program dependency report."""

    def export(
        self,
        graph: TagDependencyGraph,
        *,
        title: str = "Tag and program dependency report",
    ) -> str:
        """Return deterministic Markdown with resolved and unresolved evidence."""
        counts = Counter(item.access.value for item in graph.references)
        lines = [
            f"# {title}",
            "",
            "This report contains observed source references. Unknown or "
            "unresolved operands are retained and are not inferred as tags.",
            "",
            f"- Resolved references: {len(graph.references)}",
            f"- Read references: {counts['read']}",
            f"- Write references: {counts['write']}",
            f"- Read/write references: {counts['read_write']}",
            f"- Alias dependencies: {counts['alias']}",
            f"- Unknown-flow references: {counts['unknown']}",
            f"- Unresolved references: {len(graph.unresolved_references)}",
            "",
            "## Resolved references",
            "",
            "| Tag | Scope | Member | Access | Source alias | Program | "
            "Routine | Location | Instruction | Operand |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for item in graph.references:
            lines.append(
                f"| {_cell(item.tag_name)} | {item.tag_scope.value} "
                f"| {_cell(item.member_path)} | {item.access.value} "
                f"| {_cell(item.source_tag_key)} | {_cell(item.program_name)} "
                f"| {_cell(item.routine_name)} | {_location(item.rung_number, item.line_number)} "
                f"| {_cell(item.instruction)} | {_cell(item.operand)} |"
            )
        lines.extend(
            [
                "",
                "## Unresolved references",
                "",
                "| Identifier | Source alias | Program | Routine | Location | "
                "Instruction | Operand |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for item in graph.unresolved_references:
            lines.append(
                f"| {_cell(item.identifier)} | {_cell(item.source_tag_key)} "
                f"| {_cell(item.program_name)} | {_cell(item.routine_name)} "
                f"| {_location(item.rung_number, item.line_number)} "
                f"| {_cell(item.instruction)} | {_cell(item.operand)} |"
            )
        return "\n".join(lines).rstrip() + "\n"


class TagDependencyCSVExporter:
    """Render one complete row per resolved or unresolved reference."""

    _FIELDS = (
        "Status",
        "TagKey",
        "TagName",
        "TagScope",
        "MemberPath",
        "Access",
        "Identifier",
        "SourceTagKey",
        "Program",
        "Routine",
        "Rung",
        "Line",
        "Instruction",
        "ArgumentPosition",
        "Operand",
    )

    def export(self, graph: TagDependencyGraph) -> str:
        """Return deterministic UTF-8-ready CSV text."""
        stream = StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=self._FIELDS)
        writer.writeheader()
        for item in graph.references:
            writer.writerow(
                {
                    "Status": "resolved",
                    "TagKey": item.tag_key,
                    "TagName": item.tag_name,
                    "TagScope": item.tag_scope.value,
                    "MemberPath": item.member_path or "",
                    "Access": item.access.value,
                    "Identifier": "",
                    "SourceTagKey": item.source_tag_key or "",
                    "Program": item.program_name,
                    "Routine": item.routine_name,
                    "Rung": item.rung_number if item.rung_number is not None else "",
                    "Line": item.line_number if item.line_number is not None else "",
                    "Instruction": item.instruction,
                    "ArgumentPosition": item.argument_position,
                    "Operand": item.operand,
                }
            )
        for item in graph.unresolved_references:
            writer.writerow(
                {
                    "Status": "unresolved",
                    "TagKey": "",
                    "TagName": "",
                    "TagScope": "",
                    "MemberPath": "",
                    "Access": "",
                    "Identifier": item.identifier,
                    "SourceTagKey": item.source_tag_key or "",
                    "Program": item.program_name,
                    "Routine": item.routine_name,
                    "Rung": item.rung_number if item.rung_number is not None else "",
                    "Line": item.line_number if item.line_number is not None else "",
                    "Instruction": item.instruction,
                    "ArgumentPosition": item.argument_position,
                    "Operand": item.operand,
                }
            )
        return stream.getvalue()


def _cell(value: object | None) -> str:
    if value is None or value == "":
        return "—"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _location(rung: int | None, line: int | None) -> str:
    if rung is not None:
        return f"rung {rung}"
    if line is not None:
        return f"line {line}"
    return "—"
