"""Tests for installed neutral-model JSON commands."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

from twinforge.cli import main


DATA = Path(__file__).parent / "data/standalone/module.L5X"


def test_model_validate_accepts_exported_document(tmp_path: Path) -> None:
    destination = tmp_path / "module.json"
    assert main(
        (
            "export",
            str(DATA),
            "--target",
            "json",
            "--output",
            str(destination),
        )
    ) == 0
    output = StringIO()
    errors = StringIO()

    result = main(
        ("model", "validate", str(destination)),
        stdout=output,
        stderr=errors,
    )

    assert result == 0
    assert errors.getvalue() == ""
    assert "Valid TwinForge model JSON 1.0: Module 'DriveModule'." in (
        output.getvalue()
    )


def test_model_validate_rejects_unsupported_version(tmp_path: Path) -> None:
    source = tmp_path / "invalid.json"
    source.write_text(
        '{"schema_version":"2.0","source_format":"l5x","document":{}}',
        encoding="utf-8",
    )
    errors = StringIO()

    result = main(
        ("model", "validate", str(source)),
        stderr=errors,
    )

    assert result == 1
    assert "schema_version must be '1.0'" in errors.getvalue()


def test_model_validate_rejects_missing_file(tmp_path: Path) -> None:
    errors = StringIO()

    result = main(
        ("model", "validate", str(tmp_path / "missing.json")),
        stderr=errors,
    )

    assert result == 1
    assert "model JSON file does not exist" in errors.getvalue()
