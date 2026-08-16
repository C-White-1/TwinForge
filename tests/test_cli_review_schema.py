from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from twinforge.cli import main


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

    assert result == 1
    assert output.getvalue() == ""
    assert "error: cannot load alarm review" in errors.getvalue()
