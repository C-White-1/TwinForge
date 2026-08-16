from __future__ import annotations

import json
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from twinforge.cli import main


CONTROLLER = (
    Path(__file__).parent / "data" / "basic" / "BoosterCompressor_20260128.L5X"
)


@pytest.mark.parametrize(
    ("kind", "schema_version", "label"),
    (
        ("alarm", "twinforge.alarm-review.v1", "alarm review v1"),
        (
            "cause-effect",
            "twinforge.cause-effect-review.v1",
            "cause-and-effect review v1",
        ),
        (
            "coverage",
            "twinforge.engineering-review-coverage.v1",
            "engineering-review coverage v1",
        ),
        (
            "validation-result",
            "twinforge.review-validation-result.v1",
            "review-validation result v1",
        ),
    ),
)
def test_exports_installed_review_schema(
    tmp_path: Path,
    kind: str,
    schema_version: str,
    label: str,
) -> None:
    destination = tmp_path / "schemas" / f"{kind}.schema.json"
    output = StringIO()
    errors = StringIO()

    result = main(
        (
            "review",
            "schema",
            kind,
            "--output",
            str(destination),
        ),
        stdout=output,
        stderr=errors,
    )

    assert result == 0
    assert errors.getvalue() == ""
    schema = json.loads(destination.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert schema["properties"]["schema_version"]["const"] == schema_version
    assert f"Exported TwinForge {label}" in output.getvalue()


@pytest.mark.parametrize(
    ("kind", "filename", "label"),
    (
        ("alarm", "alarm-review.example.json", "alarm review v1"),
        (
            "cause-effect",
            "cause-effect-review.example.json",
            "cause-and-effect review v1",
        ),
    ),
)
def test_validates_review_document_without_generating_reports(
    kind: str,
    filename: str,
    label: str,
) -> None:
    source = Path(__file__).parents[1] / "examples" / "reporting" / filename
    output = StringIO()
    errors = StringIO()

    result = main(
        ("review", "validate", kind, str(source)),
        stdout=output,
        stderr=errors,
    )

    assert result == 0
    assert errors.getvalue() == ""
    assert f"Validated TwinForge {label}" in output.getvalue()
    assert "1 items" in output.getvalue()


def test_rejects_invalid_review_document(tmp_path: Path) -> None:
    source = tmp_path / "invalid.json"
    source.write_text(
        '{"schema_version":"twinforge.alarm-review.v1"}',
        encoding="utf-8",
    )
    output = StringIO()
    errors = StringIO()

    result = main(
        ("review", "validate", "alarm", str(source)),
        stdout=output,
        stderr=errors,
    )

    assert result == 4
    assert output.getvalue() == ""
    assert "error: cannot load alarm review" in errors.getvalue()


def test_reconciles_alarm_review_against_source_l5x(tmp_path: Path) -> None:
    source = tmp_path / "alarm-review.json"
    source.write_text(
        json.dumps(
            {
                "schema_version": "twinforge.alarm-review.v1",
                "controller_name": "booster_compressor",
                "reviewed_by": "Control systems engineer",
                "reviewed_at": datetime(
                    2026, 8, 16, tzinfo=timezone.utc
                ).isoformat(),
                "authority_reference": "ALARM-PHILOSOPHY-001",
                "source_reference": "C&E CE-001 revision B",
                "items": [
                    {
                        "tag_key": "controller:PT102_HH_Alm",
                        "priority": "High",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output = StringIO()
    errors = StringIO()

    result = main(
        (
            "review",
            "validate",
            "alarm",
            str(source),
            "--source",
            str(CONTROLLER),
        ),
        stdout=output,
        stderr=errors,
    )

    assert result == 0
    assert errors.getvalue() == ""
    assert f"reconciled against {CONTROLLER}" in output.getvalue()


def test_rejects_review_key_missing_from_source_l5x(tmp_path: Path) -> None:
    source = tmp_path / "alarm-review.json"
    source.write_text(
        json.dumps(
            {
                "schema_version": "twinforge.alarm-review.v1",
                "controller_name": "booster_compressor",
                "reviewed_by": "Control systems engineer",
                "reviewed_at": "2026-08-16T00:00:00Z",
                "authority_reference": "ALARM-PHILOSOPHY-001",
                "source_reference": "C&E CE-001 revision B",
                "items": [
                    {
                        "tag_key": "controller:Unknown_Alm",
                        "priority": "High",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    errors = StringIO()

    result = main(
        (
            "review",
            "validate",
            "alarm",
            str(source),
            "--source",
            str(CONTROLLER),
        ),
        stdout=StringIO(),
        stderr=errors,
    )

    assert result == 4
    assert "unknown candidate tag_key" in errors.getvalue()


def test_emits_machine_readable_reconciled_validation_result(
    tmp_path: Path,
) -> None:
    source = tmp_path / "alarm-review.json"
    source.write_text(
        json.dumps(
            {
                "schema_version": "twinforge.alarm-review.v1",
                "controller_name": "booster_compressor",
                "reviewed_by": "Control systems engineer",
                "reviewed_at": "2026-08-16T00:00:00Z",
                "authority_reference": "ALARM-PHILOSOPHY-001",
                "source_reference": "C&E CE-001 revision B",
                "items": [
                    {
                        "tag_key": "controller:PT102_HH_Alm",
                        "priority": "High",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output = StringIO()

    result = main(
        (
            "review",
            "validate",
            "alarm",
            str(source),
            "--source",
            str(CONTROLLER),
            "--format",
            "json",
        ),
        stdout=output,
        stderr=StringIO(),
    )

    assert result == 0
    document = json.loads(output.getvalue())
    assert document["schema_version"] == (
        "twinforge.review-validation-result.v1"
    )
    assert document["status"] == "valid"
    assert document["review_kind"] == "alarm"
    assert document["controller_name"] == "booster_compressor"
    assert document["item_count"] == 1
    assert document["source_reconciled"] is True
    assert len(document["review_sha256"]) == 64
    assert len(document["source_sha256"]) == 64


def test_emits_machine_readable_validation_failure(tmp_path: Path) -> None:
    source = tmp_path / "invalid.json"
    source.write_text("{}", encoding="utf-8")
    output = StringIO()
    errors = StringIO()

    result = main(
        (
            "review",
            "validate",
            "alarm",
            str(source),
            "--format",
            "json",
        ),
        stdout=output,
        stderr=errors,
    )

    assert result == 4
    assert output.getvalue() == ""
    diagnostic = json.loads(errors.getvalue())
    assert diagnostic["schema_version"] == "1.0"
    assert diagnostic["status"] == "error"
    assert diagnostic["operation"] == "review.validate"
    assert diagnostic["exit_code"] == 4
    assert diagnostic["target"] == "alarm"
    assert diagnostic["source"] == str(source)
    assert diagnostic["diagnostics"][0]["code"] == (
        "review_validation_failed"
    )


def test_writes_validation_receipt_atomically(tmp_path: Path) -> None:
    source = Path(__file__).parents[1] / "examples" / "reporting" / (
        "alarm-review.example.json"
    )
    destination = tmp_path / "receipts" / "alarm-validation.json"
    output = StringIO()

    result = main(
        (
            "review",
            "validate",
            "alarm",
            str(source),
            "--output",
            str(destination),
        ),
        stdout=output,
        stderr=StringIO(),
    )

    assert result == 0
    receipt = json.loads(destination.read_text(encoding="utf-8"))
    assert receipt["status"] == "valid"
    assert receipt["source_reconciled"] is False
    assert f"Wrote validation receipt to {destination}" in output.getvalue()
    assert list(destination.parent.glob("*.tmp")) == []


def test_invalid_review_does_not_create_receipt(tmp_path: Path) -> None:
    source = tmp_path / "invalid.json"
    source.write_text("{}", encoding="utf-8")
    destination = tmp_path / "validation.json"

    result = main(
        (
            "review",
            "validate",
            "alarm",
            str(source),
            "--output",
            str(destination),
        ),
        stdout=StringIO(),
        stderr=StringIO(),
    )

    assert result == 4
    assert not destination.exists()
