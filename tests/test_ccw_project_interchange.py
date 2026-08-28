"""Synthetic tests for the external CCW project interchange boundary."""

from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
from typing import Any

import pytest

from twinforge.cli import main
from twinforge.interchange import (
    CCWProjectValidationError,
    UnsupportedCCWProjectVersionError,
    ccw_project_inventory,
    load_ccw_project,
)


def _document() -> dict[str, Any]:
    instruction = {
        "kind": "instruction",
        "mnemonic": "XIC",
        "operand": "Start",
        "alias": "Start PB",
        "annotations": ["source annotation"],
        "position": {"column": 1, "row": 0},
    }
    return {
        "schema_version": "ccw-project-v1",
        "source": {
            "reference": "synthetic-ccw-fixture",
            "size": 1234,
            "sha256": "a" * 64,
            "entry_count": 7,
        },
        "project": {
            "name": "Synthetic Conveyor",
            "engineering_tool": "Connected Components Workbench",
            "engineering_tool_version": "22",
        },
        "controller": {
            "catalog_number": "2080-LC50-48QWB-SIM",
            "simulated": True,
        },
        "programs": [
            {
                "name": "Sequence",
                "language": "LD",
                "source_entry": "Controller/Sequence.stf",
                "rungs": [
                    {
                        "number": 1,
                        "position": {"column": 0, "row": 1},
                        "network": {
                            "kind": "series",
                            "elements": [instruction],
                        },
                        "raw_sha256": "b" * 64,
                    }
                ],
                "diagnostics": ["program diagnostic retained"],
            }
        ],
        "variables": [
            {
                "name": "Start",
                "scope": "global",
                "classification": "user",
                "data_type": "BOOL",
                "aliases": ["Start PB"],
                "physical_source": "_IO_EM_DI_00",
                "physical_destination": None,
                "evidence_entries": ["Controller/GlobalVariable.rtc"],
                "usages": [
                    {
                        "program": "Sequence",
                        "rung": 1,
                        "branch_path": [],
                        "mnemonic": "XIC",
                        "access": "read",
                        "position": {"column": 1, "row": 0},
                    }
                ],
                "seal_in_rungs": [],
            }
        ],
        "unresolved_operands": ["UnresolvedTag"],
        "diagnostics": ["source diagnostic retained"],
        "evidence": {
            "sensitive_entries": ["Controller/DevicePref.xml"],
            "unknown_entries": ["Controller/evidence.opaque"],
        },
    }


def _write_document(path: Path, document: dict[str, Any] | None = None) -> None:
    path.write_text(
        json.dumps(document or _document(), indent=2),
        encoding="utf-8",
    )


def test_adapter_preserves_complete_validated_artifact() -> None:
    source = _document()

    artifact = load_ccw_project(source)

    assert artifact.to_document() == source
    assert artifact.source_reference == "synthetic-ccw-fixture"
    assert artifact.source_sha256 == "a" * 64
    assert artifact.source_diagnostics == ("source diagnostic retained",)
    assert artifact.unknown_evidence_entries == ("Controller/evidence.opaque",)
    returned = artifact.to_document()
    returned["diagnostics"].clear()
    assert artifact.source_diagnostics == ("source diagnostic retained",)


def test_adapter_rejects_unsupported_version_before_lowering() -> None:
    document = _document()
    document["schema_version"] = "ccw-project-v2"

    with pytest.raises(
        UnsupportedCCWProjectVersionError,
        match="supported version is 'ccw-project-v1'",
    ):
        load_ccw_project(document)


def test_adapter_reports_schema_path_and_rejects_duplicate_members() -> None:
    document = _document()
    document["source"]["sha256"] = "not-a-hash"
    with pytest.raises(CCWProjectValidationError, match=r"#/source/sha256"):
        load_ccw_project(document)

    with pytest.raises(CCWProjectValidationError, match="duplicate JSON"):
        load_ccw_project(
            '{"schema_version":"ccw-project-v1","schema_version":"ccw-project-v1"}'
        )


def test_inventory_is_deterministic_and_non_semantic() -> None:
    inventory = ccw_project_inventory(load_ccw_project(_document()))

    assert inventory == {
        "schema_version": "ccw-project-v1",
        "source_reference": "synthetic-ccw-fixture",
        "source_sha256": "a" * 64,
        "project_name": "Synthetic Conveyor",
        "controller_catalog_number": "2080-LC50-48QWB-SIM",
        "program_count": 1,
        "rung_count": 1,
        "variable_count": 1,
        "unresolved_operand_count": 1,
        "diagnostic_count": 1,
        "unknown_evidence_entry_count": 1,
    }


def test_cli_validates_inspects_and_exports_schema(tmp_path: Path) -> None:
    source = tmp_path / "ccw-project.json"
    _write_document(source)

    validation_output = StringIO()
    assert (
        main(
            ("ccw-project", "validate", str(source)),
            stdout=validation_output,
        )
        == 0
    )
    assert "Valid CCW project ccw-project-v1" in validation_output.getvalue()

    inspection_output = StringIO()
    assert (
        main(
            ("ccw-project", "inspect", str(source), "--format", "json"),
            stdout=inspection_output,
        )
        == 0
    )
    assert json.loads(inspection_output.getvalue())["program_count"] == 1

    schema_path = tmp_path / "schemas/ccw-project-v1.schema.json"
    assert (
        main(
            (
                "ccw-project",
                "schema",
                "--output",
                str(schema_path),
            )
        )
        == 0
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == "urn:rockwell-file-research:ccw-project:v1"


def test_cli_reports_an_unsupported_contract_version(tmp_path: Path) -> None:
    source = tmp_path / "future.json"
    document = deepcopy(_document())
    document["schema_version"] = "ccw-project-v99"
    _write_document(source, document)
    errors = StringIO()

    result = main(
        ("ccw-project", "validate", str(source)),
        stderr=errors,
    )

    assert result == 1
    assert "unsupported CCW project schema_version" in errors.getvalue()
