"""Markdown export for conversion-readiness reports."""

from __future__ import annotations

from collections import Counter

from twinforge.analysis import ConversionReadinessReport


class ConversionReadinessMarkdownExporter:
    """Render an actionable, target-aware implementation checklist."""

    def export(self, report: ConversionReadinessReport) -> str:
        """Return deterministic Markdown."""

        counts = Counter(item.disposition.value for item in report.items)
        lines = [
            f"# {report.implementation_name} conversion-readiness report",
            "",
            "## Decision",
            "",
            (
                f"The source is classified `{report.source_disposition}` and "
                f"should become an IEC `{report.recommended_pou}`. Conversion "
                "is feasible as a staged implementation; direct translation "
                "alone is not sufficient."
            ),
            "",
            f"- Unresolved dependencies: {report.unresolved_dependency_count}",
            f"- Unanalyzed routines: {report.unanalyzed_routine_count}",
            f"- Directly portable areas: {counts['direct_portable']}",
            f"- Datatype/instruction adaptations: {counts['type_adaptation']}",
            f"- Target-adapter areas: {counts['target_adapter']}",
            f"- Manual-review areas: {counts['manual_review']}",
            f"- Hardware-validation areas: {counts['hardware_validation']}",
            "",
            "## Readiness matrix",
            "",
            "| Area | Classification | Implementation action | Evidence "
            "| Completion criterion |",
            "| --- | --- | --- | --- | --- |",
        ]
        lines.extend(
            f"| {item.area} | `{item.disposition.value}` "
            f"| {_cell(item.implementation_action)} "
            f"| {_cell('; '.join(item.evidence))} "
            f"| {_cell(item.completion_criterion)} |"
            for item in report.items
        )
        lines.extend(
            [
                "",
                "## Dependency plan",
                "",
                "| Dependency | Classification | Action |",
                "| --- | --- | --- |",
            ]
        )
        lines.extend(
            f"| `{item.name}` | `{item.disposition.value}` "
            f"| {_cell(item.action)} |"
            for item in report.dependencies
        )
        lines.extend(["", "## Recommended implementation order", ""])
        lines.extend(
            f"{index}. {item}"
            for index, item in enumerate(report.recommended_order, start=1)
        )
        lines.extend(
            [
                "",
                "## Architecture boundary",
                "",
                (
                    "The generated IEC function block should depend on neutral "
                    "cyclic-I/O, parameter-service, module-service, and timing "
                    "contracts. CODESYS implementations belong in a CODESYS "
                    "adapter module; a later OpenPLC implementation can satisfy "
                    "the same contracts independently."
                ),
                "",
                (
                    "No adapter may return invented healthy values or silently "
                    "ignore unsupported inhibit, fault, or write operations."
                ),
                "",
            ]
        )
        return "\n".join(lines)


def _cell(value: str) -> str:
    return value.replace("|", r"\|").replace("\n", " ")
