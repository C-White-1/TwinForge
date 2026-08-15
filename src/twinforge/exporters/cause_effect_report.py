"""Markdown and CSV exports for candidate cause-and-effect relationships."""

from __future__ import annotations

import csv
from io import StringIO

from twinforge.analysis.cause_effect import CauseEffectCandidateReport


class CauseEffectCandidateMarkdownExporter:
    """Render co-located logic evidence as an explicitly unverified matrix."""

    def export(
        self,
        report: CauseEffectCandidateReport,
        *,
        title: str = "Cause-and-effect candidate matrix",
    ) -> str:
        """Return deterministic review-oriented Markdown."""
        rows = sum(
            max(1, len(item.causes) + len(item.unresolved_causes))
            for item in report.candidates
        )
        lines = [
            f"# {title}",
            "",
            "These rows show reads and alarm/trip writes observed at the same "
            "logic location. Co-location is evidence for review, not proof of "
            "a causal relationship, polarity, voting rule, or shutdown action.",
            "",
            f"- Effect write locations: {len(report.candidates)}",
            f"- Matrix rows: {rows}",
            "- Verified causal relationships: "
            f"{sum(cause.review_status == 'verified' for item in report.candidates for cause in item.causes)}",
            "",
            "| Relationship key | Cause | Cause status | Effect | Effect kind | Program | Routine | "
            "Location | Read instruction | Write instruction | Evidence | Review status |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        if report.review is not None:
            lines[8:8] = [
                f"- Reviewed by: {report.review.reviewed_by}",
                f"- Reviewed at: {report.review.reviewed_at.isoformat()}",
                f"- Review authority: {report.review.authority_reference}",
                f"- Review source: {report.review.source_reference}",
            ]
        for item in report.candidates:
            location = _location(item.rung_number, item.line_number)
            effect_kinds = ", ".join(kind.value for kind in item.effect_kinds)
            if not item.causes and not item.unresolved_causes:
                lines.append(
                    _row(
                        "—",
                        "—",
                        "not observed",
                        item.effect_tag_name,
                        effect_kinds,
                        item.program_name,
                        item.routine_name,
                        location,
                        "—",
                        item.writer_instruction,
                        item.evidence_basis,
                        "unreviewed",
                    )
                )
            for cause in item.causes:
                name = cause.tag_name + (cause.member_path or "")
                lines.append(
                    _row(
                        cause.relationship_key,
                        name,
                        "resolved",
                        item.effect_tag_name,
                        effect_kinds,
                        item.program_name,
                        item.routine_name,
                        location,
                        cause.instruction,
                        item.writer_instruction,
                        item.evidence_basis,
                        cause.review_status,
                    )
                )
            for cause in item.unresolved_causes:
                lines.append(
                    _row(
                        cause.relationship_key,
                        cause.identifier,
                        "unresolved",
                        item.effect_tag_name,
                        effect_kinds,
                        item.program_name,
                        item.routine_name,
                        location,
                        cause.instruction,
                        item.writer_instruction,
                        item.evidence_basis,
                        cause.review_status,
                    )
                )
        return "\n".join(lines).rstrip() + "\n"


class CauseEffectCandidateCSVExporter:
    """Render one matrix row per resolved or unresolved cause candidate."""

    _FIELDS: tuple[str, ...] = (
        "RelationshipKey",
        "CauseTagKey",
        "Cause",
        "CauseStatus",
        "CauseOperand",
        "EffectTagKey",
        "Effect",
        "EffectKind",
        "Program",
        "Routine",
        "Rung",
        "Line",
        "ReadInstruction",
        "WriteInstruction",
        "EvidenceBasis",
        "CausalRelationshipVerified",
        "ReviewStatus",
        "Polarity",
        "Voting",
        "Delay",
        "OperatingModes",
        "ShutdownAction",
        "ReviewedBy",
        "ReviewedAt",
        "ReviewAuthorityReference",
        "ReviewSourceReference",
    )

    def export(self, report: CauseEffectCandidateReport) -> str:
        """Return deterministic UTF-8-ready CSV text."""
        stream = StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=self._FIELDS)
        writer.writeheader()
        for item in report.candidates:
            common = {
                "EffectTagKey": item.effect_tag_key,
                "Effect": item.effect_tag_name,
                "EffectKind": ";".join(kind.value for kind in item.effect_kinds),
                "Program": item.program_name,
                "Routine": item.routine_name,
                "Rung": item.rung_number if item.rung_number is not None else "",
                "Line": item.line_number if item.line_number is not None else "",
                "WriteInstruction": item.writer_instruction,
                "EvidenceBasis": item.evidence_basis,
                "CausalRelationshipVerified": "false",
                "ReviewedBy": report.review.reviewed_by if report.review else "",
                "ReviewedAt": (
                    report.review.reviewed_at.isoformat() if report.review else ""
                ),
                "ReviewAuthorityReference": (
                    report.review.authority_reference if report.review else ""
                ),
                "ReviewSourceReference": (
                    report.review.source_reference if report.review else ""
                ),
            }
            if not item.causes and not item.unresolved_causes:
                writer.writerow(
                    {
                        **common,
                        "RelationshipKey": "",
                        "CauseTagKey": "",
                        "Cause": "",
                        "CauseStatus": "not_observed",
                        "CauseOperand": "",
                        "ReadInstruction": "",
                        "ReviewStatus": "unreviewed",
                        "Polarity": "",
                        "Voting": "",
                        "Delay": "",
                        "OperatingModes": "",
                        "ShutdownAction": "",
                    }
                )
            for cause in item.causes:
                writer.writerow(
                    {
                        **common,
                        "RelationshipKey": cause.relationship_key,
                        "CauseTagKey": cause.tag_key,
                        "Cause": cause.tag_name + (cause.member_path or ""),
                        "CauseStatus": "resolved",
                        "CauseOperand": cause.operand,
                        "ReadInstruction": cause.instruction,
                        "CausalRelationshipVerified": str(
                            cause.review_status == "verified"
                        ).lower(),
                        "ReviewStatus": cause.review_status,
                        "Polarity": cause.polarity or "",
                        "Voting": cause.voting or "",
                        "Delay": cause.delay or "",
                        "OperatingModes": cause.operating_modes or "",
                        "ShutdownAction": cause.shutdown_action or "",
                    }
                )
            for cause in item.unresolved_causes:
                writer.writerow(
                    {
                        **common,
                        "RelationshipKey": cause.relationship_key,
                        "CauseTagKey": "",
                        "Cause": cause.identifier,
                        "CauseStatus": "unresolved",
                        "CauseOperand": cause.operand,
                        "ReadInstruction": cause.instruction,
                        "ReviewStatus": cause.review_status,
                        "Polarity": cause.polarity or "",
                        "Voting": cause.voting or "",
                        "Delay": cause.delay or "",
                        "OperatingModes": cause.operating_modes or "",
                        "ShutdownAction": cause.shutdown_action or "",
                    }
                )
        return stream.getvalue()


def _row(*values: object) -> str:
    return "| " + " | ".join(_cell(value) for value in values) + " |"


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _location(rung: int | None, line: int | None) -> str:
    if rung is not None:
        return f"rung {rung}"
    if line is not None:
        return f"line {line}"
    return "unavailable"
