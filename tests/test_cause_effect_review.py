from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from twinforge.analysis import (
    CauseEffectCandidateReport,
    CauseEffectReviewDocument,
    CauseEffectReviewError,
    apply_cause_effect_review,
    build_alarm_trip_candidate_report,
    build_cause_effect_candidate_report,
    build_tag_dependency_graph,
    cause_effect_review_schema_text,
    cause_effect_candidate_report_json,
)
from twinforge.exporters import (
    CauseEffectCandidateCSVExporter,
    CauseEffectCandidateMarkdownExporter,
)
from twinforge.parsers import L5XParser


SAMPLE = Path(__file__).parent / "data/basic/BoosterCompressor_20260128.L5X"


def _report() -> CauseEffectCandidateReport:
    controller = L5XParser().parse(SAMPLE, report_mode=None).controllers[0]
    graph = build_tag_dependency_graph(controller)
    return build_cause_effect_candidate_report(
        build_alarm_trip_candidate_report(controller, graph), graph
    )


def _review(key: str, *, status: str = "verified") -> CauseEffectReviewDocument:
    return CauseEffectReviewDocument.model_validate(
        {
            "schema_version": "twinforge.cause-effect-review.v1",
            "controller_name": "booster_compressor",
            "reviewed_by": "Control systems engineer",
            "reviewed_at": datetime(2026, 8, 15, tzinfo=timezone.utc),
            "authority_reference": "ALARM-PHILOSOPHY-001",
            "source_reference": "C&E CE-001 revision B",
            "items": [
                {
                    "relationship_key": key,
                    "status": status,
                    "polarity": "Cause true initiates effect",
                    "voting": "1oo1",
                    "delay": "2 s",
                    "operating_modes": "Running",
                    "shutdown_action": "Trip compressor",
                }
            ],
        }
    )


def test_applies_review_to_one_exact_resolved_relationship() -> None:
    source = _report()
    key = next(
        cause.relationship_key for item in source.candidates for cause in item.causes
    )

    reviewed = apply_cause_effect_review(source, _review(key))

    assert all(
        cause.review_status == "unreviewed"
        for item in source.candidates
        for cause in item.causes
    )
    cause = next(
        cause
        for item in reviewed.candidates
        for cause in item.causes
        if cause.relationship_key == key
    )
    assert cause.review_status == "verified"
    assert cause.voting == "1oo1"
    assert reviewed.review is not None
    assert reviewed.review.applied_relationship_keys == (key,)
    payload = json.loads(cause_effect_candidate_report_json(reviewed))
    assert payload["review"]["reviewed_by"] == "Control systems engineer"
    row = next(
        row
        for row in csv.DictReader(
            StringIO(CauseEffectCandidateCSVExporter().export(reviewed))
        )
        if row["RelationshipKey"] == key
    )
    assert row["CausalRelationshipVerified"] == "true"
    assert row["ShutdownAction"] == "Trip compressor"
    markdown = CauseEffectCandidateMarkdownExporter().export(reviewed)
    reviewed_row = next(
        line for line in markdown.splitlines() if line.startswith(f"| {key} |")
    )
    assert "| verified | Cause true initiates effect | 1oo1 | 2 s | Running | " in (
        reviewed_row
    )
    assert reviewed_row.endswith("| Trip compressor |")


def test_rejects_unknown_relationship_key() -> None:
    with pytest.raises(CauseEffectReviewError, match="unknown relationship"):
        apply_cause_effect_review(_report(), _review("ce:000000000000000000000000"))


def test_unresolved_relationship_can_be_rejected_but_not_verified() -> None:
    source = _report()
    key = next(
        cause.relationship_key
        for item in source.candidates
        for cause in item.unresolved_causes
    )

    with pytest.raises(CauseEffectReviewError, match="cannot be verified"):
        apply_cause_effect_review(source, _review(key))

    rejected = apply_cause_effect_review(source, _review(key, status="rejected"))
    cause = next(
        cause
        for item in rejected.candidates
        for cause in item.unresolved_causes
        if cause.relationship_key == key
    )
    assert cause.review_status == "rejected"


def test_packaged_cause_effect_review_schema_accepts_example() -> None:
    schema = json.loads(cause_effect_review_schema_text())
    Draft202012Validator.check_schema(schema)
    example = json.loads(
        Path("examples/reporting/cause-effect-review.example.json").read_text(
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
