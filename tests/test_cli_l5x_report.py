from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path

from twinforge.cli import main


DATA = Path(__file__).parent / "data"
CONTROLLER = DATA / "basic/BoosterCompressor_20260128.L5X"


def test_report_writes_controller_engineering_bundle(tmp_path: Path) -> None:
    destination = tmp_path / "reports"
    output = StringIO()
    errors = StringIO()

    result = main(
        ("report", str(CONTROLLER), "--output", str(destination)),
        stdout=output,
        stderr=errors,
    )

    assert result == 0
    assert errors.getvalue() == ""
    assert {path.name for path in destination.iterdir()} == {
        "controller.txt",
        "tags.txt",
        "datatypes.txt",
        "add_on_instructions.txt",
        "modules.txt",
        "tasks.txt",
        "programs.txt",
        "tag_dependencies.md",
        "tag_dependencies.csv",
        "tag_dependencies.json",
        "alarm_trip_candidates.md",
        "alarm_trip_candidates.csv",
        "alarm_trip_candidates.json",
        "io_list.md",
        "io_list.csv",
        "io_list.json",
        "cause_effect_candidates.md",
        "cause_effect_candidates.csv",
        "cause_effect_candidates.json",
        "engineering_review_coverage.md",
        "engineering_review_coverage.csv",
        "engineering_review_coverage.json",
        "functional_description.md",
        "module_schedule.md",
        "module_schedule.csv",
        "module_schedule.json",
        "external_references.md",
        "external_references.json",
    }
    assert "Exported 28 reports" in output.getvalue()
    assert "1756-IB16" in (destination / "modules.txt").read_text(encoding="utf-8")
    dependency_report = (destination / "tag_dependencies.md").read_text(
        encoding="utf-8"
    )
    assert "booster_compressor tag and program dependency report" in (dependency_report)
    assert "## Unresolved references" in dependency_report
    alarm_report = (destination / "alarm_trip_candidates.md").read_text(
        encoding="utf-8"
    )
    assert "alarm and trip candidate report" in alarm_report
    assert "not a verified alarm philosophy" in alarm_report
    io_report = (destination / "io_list.md").read_text(encoding="utf-8")
    assert "booster_compressor I/O list" in io_report
    assert "PT102_PV" in io_report
    assert "unavailable_by_configuration" in io_report
    cause_effect_report = (destination / "cause_effect_candidates.md").read_text(
        encoding="utf-8"
    )
    assert "cause-and-effect candidate matrix" in cause_effect_report
    assert "PT102_HH_Alm" in cause_effect_report
    assert "not proof of a causal relationship" in cause_effect_report
    review_coverage = json.loads(
        (destination / "engineering_review_coverage.json").read_text(
            encoding="utf-8"
        )
    )
    assert review_coverage["summary"]["reviewed_alarm_count"] == 0
    assert review_coverage["summary"]["verified_relationship_count"] == 0
    coverage_rows = list(
        csv.DictReader(
            StringIO(
                (destination / "engineering_review_coverage.csv").read_text(
                    encoding="utf-8"
                )
            )
        )
    )
    assert {row["RecordType"] for row in coverage_rows} == {
        "alarm_candidate",
        "cause_effect_relationship",
    }
    assert all(
        row["ExplicitlyReviewed"] == "false" for row in coverage_rows
    )
    functional_description = (destination / "functional_description.md").read_text(
        encoding="utf-8"
    )
    assert "functional-description draft" in functional_description
    assert "MainTask" in functional_description
    assert "MainProgram" in functional_description
    module_schedule = (destination / "module_schedule.md").read_text(encoding="utf-8")
    assert "module and spare-I/O schedule" in module_schedule
    assert "AI_Slot4" in module_schedule
    assert "Unknown capability is retained" in module_schedule
    external_references = (destination / "external_references.md").read_text(
        encoding="utf-8"
    )
    assert "external address and controller-reference inventory" in (
        external_references
    )
    assert "does not prove that a target exists" in external_references


def test_report_rejects_non_controller_target(tmp_path: Path) -> None:
    destination = tmp_path / "reports"
    errors = StringIO()

    result = main(
        (
            "report",
            str(DATA / "standalone/program.L5X"),
            "--output",
            str(destination),
        ),
        stderr=errors,
    )

    assert result == 1
    assert not destination.exists()
    assert "require a Controller L5X target" in errors.getvalue()


def test_report_returns_failure_for_invalid_source(tmp_path: Path) -> None:
    errors = StringIO()

    assert (
        main(
            (
                "report",
                str(tmp_path / "missing.L5X"),
                "--output",
                str(tmp_path / "reports"),
            ),
            stderr=errors,
        )
        == 1
    )
    assert "cannot generate reports" in errors.getvalue()


def _write_alarm_review(path: Path, tag_key: str) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "twinforge.alarm-review.v1",
                "controller_name": "booster_compressor",
                "reviewed_by": "Control systems engineer",
                "reviewed_at": "2026-08-15T10:00:00+10:00",
                "authority_reference": "ALARM-PHILOSOPHY-001",
                "source_reference": "C&E drawing CE-102 revision B",
                "items": [
                    {
                        "tag_key": tag_key,
                        "priority": "High",
                        "setpoint": "12.5",
                        "engineering_unit": "barg",
                        "shutdown_action": "Trip compressor",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_report_applies_explicit_alarm_review_overlay(tmp_path: Path) -> None:
    destination = tmp_path / "reports"
    review = tmp_path / "alarm-review.json"
    _write_alarm_review(review, "controller:PT102_HH_Alm")
    output = StringIO()
    errors = StringIO()

    result = main(
        (
            "report",
            str(CONTROLLER),
            "--output",
            str(destination),
            "--alarm-review",
            str(review),
        ),
        stdout=output,
        stderr=errors,
    )

    assert result == 0
    assert errors.getvalue() == ""
    report = json.loads(
        (destination / "alarm_trip_candidates.json").read_text(encoding="utf-8")
    )
    candidate = next(
        item
        for item in report["candidates"]
        if item["tag_key"] == "controller:PT102_HH_Alm"
    )
    assert candidate["priority"] == "High"
    assert candidate["setpoint"] == "12.5"
    assert candidate["engineering_unit"] == "barg"
    assert report["review"]["reviewed_by"] == "Control systems engineer"
    coverage = json.loads(
        (destination / "engineering_review_coverage.json").read_text(
            encoding="utf-8"
        )
    )
    assert coverage["summary"]["reviewed_alarm_count"] == 1


def test_report_rejects_unknown_alarm_review_before_writing(tmp_path: Path) -> None:
    destination = tmp_path / "reports"
    review = tmp_path / "alarm-review.json"
    _write_alarm_review(review, "controller:Unknown_Alm")
    errors = StringIO()

    result = main(
        (
            "report",
            str(CONTROLLER),
            "--output",
            str(destination),
            "--alarm-review",
            str(review),
        ),
        stderr=errors,
    )

    assert result == 1
    assert not destination.exists()
    assert "unknown candidate" in errors.getvalue()


def test_report_applies_exact_cause_effect_review_overlay(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    assert (
        main(
            ("report", str(CONTROLLER), "--output", str(baseline)),
            stdout=StringIO(),
            stderr=StringIO(),
        )
        == 0
    )
    matrix = json.loads(
        (baseline / "cause_effect_candidates.json").read_text(encoding="utf-8")
    )
    relationship_key = next(
        cause["relationship_key"]
        for candidate in matrix["candidates"]
        for cause in candidate["causes"]
    )
    review = tmp_path / "cause-effect-review.json"
    review.write_text(
        json.dumps(
            {
                "schema_version": "twinforge.cause-effect-review.v1",
                "controller_name": "booster_compressor",
                "reviewed_by": "Control systems engineer",
                "reviewed_at": "2026-08-15T10:00:00+10:00",
                "authority_reference": "ALARM-PHILOSOPHY-001",
                "source_reference": "C&E drawing CE-102 revision B",
                "items": [
                    {
                        "relationship_key": relationship_key,
                        "status": "verified",
                        "polarity": "Cause true initiates effect",
                        "shutdown_action": "Trip compressor",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    destination = tmp_path / "reviewed"

    result = main(
        (
            "report",
            str(CONTROLLER),
            "--output",
            str(destination),
            "--cause-effect-review",
            str(review),
        ),
        stdout=StringIO(),
        stderr=StringIO(),
    )

    assert result == 0
    reviewed = json.loads(
        (destination / "cause_effect_candidates.json").read_text(encoding="utf-8")
    )
    cause = next(
        cause
        for candidate in reviewed["candidates"]
        for cause in candidate["causes"]
        if cause["relationship_key"] == relationship_key
    )
    assert cause["review_status"] == "verified"
    assert cause["shutdown_action"] == "Trip compressor"
    assert reviewed["review"]["applied_relationship_keys"] == [relationship_key]
    coverage = json.loads(
        (destination / "engineering_review_coverage.json").read_text(
            encoding="utf-8"
        )
    )
    assert coverage["summary"]["verified_relationship_count"] == 1
