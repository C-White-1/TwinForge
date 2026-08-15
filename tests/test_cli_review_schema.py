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
