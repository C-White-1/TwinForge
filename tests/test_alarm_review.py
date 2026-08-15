from __future__ import annotations

import csv
import json
from dataclasses import replace
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import ValidationError

from twinforge.analysis import (
    AlarmReviewDocument,
    AlarmReviewError,
    AlarmReviewItem,
    AlarmTripCandidate,
    AlarmTripCandidateKind,
    AlarmTripCandidateReport,
    alarm_review_schema_text,
    alarm_trip_candidate_report_json,
    apply_alarm_review,
)
from twinforge.exporters import (
    AlarmTripCandidateCSVExporter,
    AlarmTripCandidateMarkdownExporter,
)
from twinforge.model import SoftwareTagScope


def _report() -> AlarmTripCandidateReport:
    return AlarmTripCandidateReport(
        controller_name="PLC",
        candidates=(
            AlarmTripCandidate(
                tag_key="controller:PT102_HH_Alm",
                tag_name="PT102_HH_Alm",
                tag_scope=SoftwareTagScope.CONTROLLER,
                program_name=None,
                description="Discharge pressure high-high alarm",
                kinds=(AlarmTripCandidateKind.ALARM,),
                classification_evidence=("name explicitly contains an alarm token",),
                reader_locations=("Main.Alarms: rung 2",),
                writer_locations=("Main.Trips: rung 1",),
                alias_source_keys=(),
            ),
        ),
    )


def _review(**overrides: object) -> AlarmReviewDocument:
    values: dict[str, object] = {
        "schema_version": "twinforge.alarm-review.v1",
        "controller_name": "PLC",
        "reviewed_by": "Control systems engineer",
        "reviewed_at": datetime(2026, 8, 15, tzinfo=timezone.utc),
        "authority_reference": "ALARM-PHILOSOPHY-001",
        "source_reference": "C&E drawing CE-102 revision B",
        "items": (
            AlarmReviewItem(
                tag_key="controller:PT102_HH_Alm",
                priority="High",
                setpoint="12.5",
                engineering_unit="barg",
                shutdown_action="Trip compressor",
            ),
        ),
    }
    values.update(overrides)
    return AlarmReviewDocument.model_validate(values)


def test_applies_attributable_review_without_mutating_candidate_evidence() -> None:
    source = _report()

    reviewed = apply_alarm_review(source, _review())

    assert source.candidates[0].priority is None
    candidate = reviewed.candidates[0]
    assert candidate.priority == "High"
    assert candidate.setpoint == "12.5"
    assert candidate.engineering_unit == "barg"
    assert candidate.shutdown_action == "Trip compressor"
    assert candidate.reader_locations == source.candidates[0].reader_locations
    assert reviewed.review is not None
    assert reviewed.review.applied_tag_keys == ("controller:PT102_HH_Alm",)

    document = json.loads(alarm_trip_candidate_report_json(reviewed))
    assert document["review"]["authority_reference"] == ("ALARM-PHILOSOPHY-001")
    markdown = AlarmTripCandidateMarkdownExporter().export(reviewed)
    assert "Reviewed by: Control systems engineer" in markdown
    rows = list(
        csv.DictReader(StringIO(AlarmTripCandidateCSVExporter().export(reviewed)))
    )
    assert rows[0]["ReviewedBy"] == "Control systems engineer"
    assert rows[0]["Priority"] == "High"
    assert rows[0]["ExplicitlyReviewed"] == "true"


def test_partial_review_does_not_attribute_unreviewed_candidate() -> None:
    source = _report()
    other = replace(
        source.candidates[0],
        tag_key="controller:PT103_HH_Alm",
        tag_name="PT103_HH_Alm",
    )
    reviewed = apply_alarm_review(
        replace(source, candidates=source.candidates + (other,)),
        _review(),
    )

    document = json.loads(alarm_trip_candidate_report_json(reviewed))
    by_key = {item["tag_key"]: item for item in document["candidates"]}
    assert by_key["controller:PT102_HH_Alm"]["explicitly_reviewed"] is True
    assert by_key["controller:PT103_HH_Alm"]["explicitly_reviewed"] is False
    rows = {
        row["TagKey"]: row
        for row in csv.DictReader(
            StringIO(AlarmTripCandidateCSVExporter().export(reviewed))
        )
    }
    assert rows["controller:PT102_HH_Alm"]["ReviewedBy"] == (
        "Control systems engineer"
    )
    assert rows["controller:PT103_HH_Alm"]["ExplicitlyReviewed"] == "false"
    assert rows["controller:PT103_HH_Alm"]["ReviewedBy"] == ""
    markdown = AlarmTripCandidateMarkdownExporter().export(reviewed)
    table_lines = [line for line in markdown.splitlines() if line.startswith("|")]
    assert {line.count("|") for line in table_lines} == {19}
    unreviewed_row = next(
        line for line in markdown.splitlines() if "PT103_HH_Alm" in line
    )
    assert "| false |" in unreviewed_row


def test_rejects_unknown_candidate_without_partial_application() -> None:
    review = _review(
        items=(AlarmReviewItem(tag_key="controller:Unknown_Alm", priority="Low"),)
    )

    with pytest.raises(AlarmReviewError, match="unknown candidate"):
        apply_alarm_review(_report(), review)


def test_review_contract_rejects_naive_time_duplicate_keys_and_empty_rows() -> None:
    with pytest.raises(ValidationError, match="timezone"):
        _review(reviewed_at=datetime(2026, 8, 15))
    duplicate = AlarmReviewItem(tag_key="controller:PT102_HH_Alm", priority="High")
    with pytest.raises(ValidationError, match="unique"):
        _review(items=(duplicate, duplicate))
    with pytest.raises(ValidationError, match="at least one"):
        AlarmReviewItem(tag_key="controller:PT102_HH_Alm")
    with pytest.raises(ValidationError, match="must not be null"):
        AlarmReviewItem(
            tag_key="controller:PT102_HH_Alm",
            priority="High",
            setpoint=None,
        )


def test_packaged_alarm_review_schema_accepts_example() -> None:
    schema = json.loads(alarm_review_schema_text())
    Draft202012Validator.check_schema(schema)
    example = json.loads(
        Path("examples/reporting/alarm-review.example.json").read_text(
            encoding="utf-8"
        )
    )

    errors = list(
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).iter_errors(example)
    )

    assert errors == []
