"""Contract and persistence tests for L5X EDS reconciliation output."""

import json
from io import StringIO
from pathlib import Path

from jsonschema import Draft202012Validator

from twinforge.cli import main
from twinforge.cli.l5x_eds_catalog import (
    eds_catalog_reconciliation_schema_text,
)


def test_packaged_schema_is_draft_2020_12_and_self_validating() -> None:
    schema = json.loads(eds_catalog_reconciliation_schema_text())

    Draft202012Validator.check_schema(schema)


def test_catalog_schema_command_exports_exact_packaged_bytes(tmp_path: Path) -> None:
    destination = tmp_path / "schema.json"
    output = StringIO()

    result = main(
        ["catalog", "schema", "--output", str(destination)],
        stdout=output,
        stderr=StringIO(),
    )

    assert result == 0
    assert destination.read_text(encoding="utf-8") == (
        eds_catalog_reconciliation_schema_text()
    )
    assert "Exported" in output.getvalue()
