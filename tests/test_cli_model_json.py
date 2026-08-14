"""Tests for installed neutral-model JSON commands."""

from __future__ import annotations

from io import StringIO
import json
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


def test_model_inspect_reports_deterministic_evidence_inventory(
    tmp_path: Path,
) -> None:
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
    text_output = StringIO()

    assert main(
        ("model", "inspect", str(destination)),
        stdout=text_output,
    ) == 0
    assert "Target: Module 'DriveModule'" in text_output.getvalue()
    assert "Typed records:" in text_output.getvalue()
    assert "Source extensions: 1" in text_output.getvalue()

    json_output = StringIO()
    assert main(
        ("model", "inspect", str(destination), "--format", "json"),
        stdout=json_output,
    ) == 0
    inventory = json.loads(json_output.getvalue())
    assert inventory["target_type"] == "Module"
    assert inventory["target_name"] == "DriveModule"
    assert inventory["record_count"] > 0
    assert inventory["reference_count"] >= 0
    assert inventory["record_types"] == dict(
        sorted(inventory["record_types"].items())
    )


def test_model_schema_exports_packaged_contract(tmp_path: Path) -> None:
    destination = tmp_path / "schemas/model-json-1.0.schema.json"
    output = StringIO()

    result = main(
        ("model", "schema", "--output", str(destination)),
        stdout=output,
    )

    assert result == 0
    schema = json.loads(destination.read_text(encoding="utf-8"))
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["schema_version"]["const"] == "1.0"
    assert "Exported TwinForge model JSON 1.0 schema" in output.getvalue()


def test_model_query_selects_validated_evidence(tmp_path: Path) -> None:
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

    result = main(
        (
            "model",
            "query",
            str(destination),
            "#/document/target/catalog",
            "--compact",
        ),
        stdout=output,
    )

    assert result == 0
    assert json.loads(output.getvalue()) == "ETHERNET-MODULE"


def test_model_query_reports_missing_pointer(tmp_path: Path) -> None:
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
    errors = StringIO()

    result = main(
        (
            "model",
            "query",
            str(destination),
            "#/document/not-present",
        ),
        stderr=errors,
    )

    assert result == 1
    assert "pointer does not exist" in errors.getvalue()


def test_model_records_lists_typed_evidence_with_queryable_pointers(
    tmp_path: Path,
) -> None:
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

    result = main(
        (
            "model",
            "records",
            str(destination),
            "--type",
            "Module",
            "--format",
            "json",
        ),
        stdout=output,
    )

    assert result == 0
    listing = json.loads(output.getvalue())
    assert listing["count"] == 1
    assert listing["records"] == [
        {
            "name": "DriveModule",
            "pointer": "#/document/target",
            "type": "twinforge.model.module.Module",
        }
    ]


def test_model_compare_reports_machine_readable_evidence_changes(
    tmp_path: Path,
) -> None:
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    assert main(
        (
            "export",
            str(DATA),
            "--target",
            "json",
            "--output",
            str(before),
        )
    ) == 0
    payload = json.loads(before.read_text(encoding="utf-8"))
    payload["document"]["target"]["catalog"] = "CHANGED-CATALOG"
    after.write_text(json.dumps(payload), encoding="utf-8")
    output = StringIO()

    result = main(
        (
            "model",
            "compare",
            str(before),
            str(after),
            "--format",
            "json",
        ),
        stdout=output,
    )

    assert result == 0
    comparison = json.loads(output.getvalue())
    assert comparison["change_count"] == 1
    assert comparison["changes"] == [
        {
            "operation": "replace",
            "pointer": "#/document/target/catalog",
            "before": "ETHERNET-MODULE",
            "after": "CHANGED-CATALOG",
        }
    ]
