"""Markdown export for engineering-review coverage and remaining gaps."""

from __future__ import annotations

import csv
from io import StringIO

from twinforge.analysis.review_coverage import EngineeringReviewCoverage


class EngineeringReviewCoverageMarkdownExporter:
    """Render coverage counts without presenting them as engineering approval."""

    def export(self, coverage: EngineeringReviewCoverage) -> str:
        """Return a deterministic, review-oriented Markdown document."""

        relationships = coverage.cause_effect_relationships
        lines = [
            f"# {coverage.controller_name} engineering review coverage",
            "",
            "Coverage records supplied review evidence; it does not certify that "
            "the controller design is safe, complete, or approved.",
            "",
            "## Summary",
            "",
            f"- Alarm/trip candidates: {len(coverage.alarm_candidates)}",
            f"- Explicitly reviewed alarm/trip candidates: {coverage.reviewed_alarm_count}",
            f"- Candidates with every tracked review field populated: {coverage.complete_alarm_count}",
            f"- Cause-and-effect relationships: {len(relationships)}",
            f"- Verified relationships: {coverage.verified_relationship_count}",
            f"- Rejected relationships: {coverage.rejected_relationship_count}",
            f"- Unreviewed relationships: {sum(item.review_status == 'unreviewed' for item in relationships)}",
            f"- Unresolved relationships: {sum(item.cause_status == 'unresolved' for item in relationships)}",
            "",
            "## Alarm/trip field gaps",
            "",
            "| Candidate key | Explicitly reviewed | Missing fields |",
            "| --- | --- | --- |",
        ]
        lines.extend(
            "| "
            + " | ".join(
                (
                    _cell(item.tag_key),
                    str(item.reviewed).lower(),
                    _cell(", ".join(item.missing_fields) or "none"),
                )
            )
            + " |"
            for item in coverage.alarm_candidates
        )
        return "\n".join(lines).rstrip() + "\n"


class EngineeringReviewCoverageCSVExporter:
    """Render alarm gaps and relationship dispositions in one stable table."""

    _FIELDS = (
        "RecordType",
        "Key",
        "ExplicitlyReviewed",
        "MissingFields",
        "CauseStatus",
        "ReviewStatus",
    )

    def export(self, coverage: EngineeringReviewCoverage) -> str:
        """Return deterministic UTF-8-ready coverage CSV text."""

        stream = StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=self._FIELDS)
        writer.writeheader()
        for item in coverage.alarm_candidates:
            writer.writerow(
                {
                    "RecordType": "alarm_candidate",
                    "Key": item.tag_key,
                    "ExplicitlyReviewed": str(item.reviewed).lower(),
                    "MissingFields": ";".join(item.missing_fields),
                    "CauseStatus": "",
                    "ReviewStatus": "",
                }
            )
        for item in coverage.cause_effect_relationships:
            writer.writerow(
                {
                    "RecordType": "cause_effect_relationship",
                    "Key": item.relationship_key,
                    "ExplicitlyReviewed": str(
                        item.review_status != "unreviewed"
                    ).lower(),
                    "MissingFields": "",
                    "CauseStatus": item.cause_status,
                    "ReviewStatus": item.review_status,
                }
            )
        return stream.getvalue()


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
