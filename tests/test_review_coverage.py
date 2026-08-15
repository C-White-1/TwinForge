from __future__ import annotations

import json

from jsonschema import Draft202012Validator

from twinforge.analysis import (
    AlarmTripCandidateReport,
    CauseEffectCandidateReport,
    build_engineering_review_coverage,
    engineering_review_coverage_data,
    engineering_review_coverage_json,
    engineering_review_coverage_schema_text,
)
from twinforge.exporters import EngineeringReviewCoverageCSVExporter


def test_empty_reports_have_explicit_zero_coverage() -> None:
    coverage = build_engineering_review_coverage(
        AlarmTripCandidateReport(controller_name="PLC", candidates=()),
        CauseEffectCandidateReport(controller_name="PLC", candidates=()),
    )

    data = engineering_review_coverage_data(coverage)

    assert data["summary"] == {
        "alarm_candidate_count": 0,
        "reviewed_alarm_count": 0,
        "complete_alarm_count": 0,
        "relationship_count": 0,
        "verified_relationship_count": 0,
        "rejected_relationship_count": 0,
        "unreviewed_relationship_count": 0,
        "unresolved_relationship_count": 0,
    }
    assert EngineeringReviewCoverageCSVExporter().export(coverage) == (
        "RecordType,Key,ExplicitlyReviewed,MissingFields,CauseStatus,ReviewStatus\r\n"
    )


def test_packaged_schema_accepts_generated_coverage() -> None:
    coverage = build_engineering_review_coverage(
        AlarmTripCandidateReport(controller_name="PLC", candidates=()),
        CauseEffectCandidateReport(controller_name="PLC", candidates=()),
    )
    document = json.loads(engineering_review_coverage_json(coverage))
    schema = json.loads(engineering_review_coverage_schema_text())

    Draft202012Validator.check_schema(schema)
    assert list(Draft202012Validator(schema).iter_errors(document)) == []
    assert document["schema_version"] == (
        "twinforge.engineering-review-coverage.v1"
    )


def test_rejects_mixed_controller_reports() -> None:
    try:
        build_engineering_review_coverage(
            AlarmTripCandidateReport(controller_name="PLC_A", candidates=()),
            CauseEffectCandidateReport(controller_name="PLC_B", candidates=()),
        )
    except ValueError as error:
        assert "same controller" in str(error)
    else:
        raise AssertionError("mixed-controller coverage should fail")
