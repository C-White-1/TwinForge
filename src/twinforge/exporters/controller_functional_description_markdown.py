"""Markdown export for controller-level functional-description drafts."""

from __future__ import annotations

from twinforge.analysis.controller_functional_description import (
    ControllerFunctionalDescription,
)


class ControllerFunctionalDescriptionMarkdownExporter:
    """Render a structural and evidence-backed controller overview."""

    def export(self, report: ControllerFunctionalDescription) -> str:
        """Return deterministic Markdown suitable for engineering review."""
        lines = [
            f"# {report.controller_name} functional-description draft",
            "",
            "## Scope",
            "",
            "This document summarizes captured controller structure and supported "
            "analysis evidence. It is a review draft, not a validated statement "
            "of plant intent.",
            "",
            "## Controller identity and inventory",
            "",
            f"- Product: {_value(report.product_name)}",
            f"- Vendor: {_value(report.vendor)}",
            f"- Revision: {_value(report.revision)}",
            f"- Chassis: {report.chassis_count}",
            f"- Modules: {report.module_count}",
            f"- Controller tags: {report.controller_tag_count}",
            f"- Datatypes: {report.datatype_count}",
            f"- Add-On Instructions: {report.add_on_instruction_count}",
            "",
            "## Execution schedule",
            "",
            "| Task | Type | Rate | Priority | Watchdog | Inhibited | "
            "Scheduled programs | Unresolved programs |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        lines.extend(
            f"| {_cell(item.name)} | {_cell(item.task_type)} "
            f"| {_cell(item.rate)} | {_cell(item.priority)} "
            f"| {_cell(item.watchdog)} | {_cell(item.inhibited)} "
            f"| {_cell(', '.join(item.scheduled_programs))} "
            f"| {_cell(', '.join(item.unresolved_programs))} |"
            for item in report.tasks
        )
        lines.extend(
            [
                "",
                "## Program and routine structure",
                "",
                "| Program | Disabled | Main routine | Routines | Languages | "
                "Ladder rungs | ST lines | Program tags | Observed calls |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        lines.extend(
            f"| {_cell(item.name)} | {_cell(item.disabled)} "
            f"| {_cell(item.main_routine)} "
            f"| {_cell(', '.join(item.routine_names))} "
            f"| {_cell(', '.join(item.routine_languages))} "
            f"| {item.ladder_rung_count} | {item.structured_text_line_count} "
            f"| {item.program_tag_count} "
            f"| {_cell(', '.join(item.observed_call_targets))} |"
            for item in report.programs
        )
        lines.extend(
            [
                "",
                "## Derived engineering evidence",
                "",
                f"- Modeled I/O channels: {report.io_channel_count}",
                f"- Explicitly assigned I/O channels: {report.assigned_io_count}",
                "- Explicit alarm/trip candidates: "
                f"{report.alarm_trip_candidate_count}",
                "- Cause/effect candidate write locations: "
                f"{report.cause_effect_candidate_count}",
                f"- Resolved tag references: {report.resolved_dependency_count}",
                "- Unresolved tag references: "
                f"{report.unresolved_dependency_count}",
                "",
                "Related generated evidence:",
                "",
                "- `io_list.md`",
                "- `alarm_trip_candidates.md`",
                "- `cause_effect_candidates.md`",
                "- `tag_dependencies.md`",
                "",
                "## Engineering boundaries",
                "",
            ]
        )
        lines.extend(f"- {item}" for item in report.boundaries)
        return "\n".join(lines).rstrip() + "\n"


def _value(value: object | None) -> str:
    return "not captured" if value is None or value == "" else str(value)


def _cell(value: object | None) -> str:
    if value is None or value == "":
        return "—"
    return str(value).replace("|", "\\|").replace("\n", " ")
