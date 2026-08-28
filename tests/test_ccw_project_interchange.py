"""Synthetic tests for the external CCW project interchange boundary."""

from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

import pytest

from twinforge.cli import main
from twinforge.exporters import PLCOPEN_CODESYS_NAMESPACE
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


def test_cli_reports_neutral_lowering_without_target_export(
    tmp_path: Path,
) -> None:
    source = tmp_path / "ccw-project.json"
    _write_document(source)
    output = StringIO()

    assert (
        main(
            ("ccw-project", "lower", str(source), "--format", "json"),
            stdout=output,
        )
        == 0
    )

    summary = json.loads(output.getvalue())
    assert summary["controller_name"] == "Synthetic Conveyor"
    assert summary["tag_count"] == 1
    assert summary["rung_count"] == 1
    assert summary["converted_instruction_count"] == 1
    assert summary["unsupported_instruction_count"] == 0


def test_cli_reports_physical_io_sizing_summary(tmp_path: Path) -> None:
    source = tmp_path / "ccw-project.json"
    document = deepcopy(_document())

    def _physical_tag(name: str) -> dict:
        tag = deepcopy(document["variables"][0])
        tag["name"] = name
        tag["classification"] = "physical_io"
        tag["aliases"] = []
        tag["physical_source"] = None
        tag["physical_destination"] = None
        tag["usages"] = []
        return tag

    # _IO_EM_DI_00 is bound (via the fixture's "Start" variable, aliased
    # "Start PB") and its own physical_io point now exists too.
    document["variables"].append(_physical_tag("_IO_EM_DI_00"))

    output_variable = deepcopy(document["variables"][0])
    output_variable["name"] = "OUT00"
    output_variable["classification"] = "user"
    output_variable["aliases"] = ["Motor Contactor"]
    output_variable["physical_source"] = None
    output_variable["physical_destination"] = "_IO_EM_DO_00"
    output_variable["usages"] = []
    document["variables"].append(output_variable)
    document["variables"].append(_physical_tag("_IO_EM_DO_00"))

    # A spare point: declared, but nothing binds to it.
    document["variables"].append(_physical_tag("_IO_EM_DI_05"))

    # An unresolved binding: references a physical address with no matching
    # physical_io-classified variable.
    unresolved_variable = deepcopy(document["variables"][0])
    unresolved_variable["name"] = "OUT99"
    unresolved_variable["classification"] = "user"
    unresolved_variable["aliases"] = []
    unresolved_variable["physical_source"] = None
    unresolved_variable["physical_destination"] = "_IO_EM_DO_99"
    unresolved_variable["usages"] = []
    document["variables"].append(unresolved_variable)

    _write_document(source, document)
    output = StringIO()

    assert (
        main(
            ("ccw-project", "io-summary", str(source), "--format", "json"),
            stdout=output,
        )
        == 0
    )

    summary = json.loads(output.getvalue())
    assert summary["controller_catalog_number"] == "2080-LC50-48QWB-SIM"
    assert summary["total_point_count"] == 3
    assert summary["counts_by_assignment_status"] == {"assigned": 2, "spare": 1}
    assert summary["assigned_unaliased_point_count"] == 0
    assert summary["counts_by_direction_and_signal_type"] == {
        "Input/Digital": 2,
        "Output/Digital": 1,
    }
    points = {point["physical_address"]: point for point in summary["points"]}
    assert points["_IO_EM_DI_00"]["direction"] == "Input"
    assert points["_IO_EM_DI_00"]["signal_type"] == "Digital"
    assert points["_IO_EM_DI_00"]["assignment_status"] == "assigned"
    assert points["_IO_EM_DI_00"]["aliases"] == ["Start PB"]
    assert points["_IO_EM_DO_00"]["direction"] == "Output"
    assert points["_IO_EM_DO_00"]["assignment_status"] == "assigned"
    assert points["_IO_EM_DO_00"]["aliases"] == ["Motor Contactor"]
    assert points["_IO_EM_DI_05"]["direction"] == "Input"
    assert points["_IO_EM_DI_05"]["assignment_status"] == "spare"
    assert points["_IO_EM_DI_05"]["aliases"] == []

    unresolved = {item["physical_address"]: item for item in summary["unresolved_bindings"]}
    assert unresolved["_IO_EM_DO_99"]["tag_name"] == "OUT99"


def test_cli_exports_codesys_xml_and_attributable_coverage(
    tmp_path: Path,
) -> None:
    source = tmp_path / "ccw-project.json"
    destination = tmp_path / "ccw-project-codesys.xml"
    coverage_path = tmp_path / "ccw-project-coverage.json"
    document = _document()
    system_variable = deepcopy(document["variables"][0])
    system_variable["name"] = "SystemClock"
    system_variable["classification"] = "system"
    system_variable["aliases"] = []
    system_variable["physical_source"] = None
    system_variable["usages"] = []
    document["variables"].append(system_variable)
    _write_document(source, document)

    assert (
        main(
            (
                "ccw-project",
                "export",
                str(source),
                "--target",
                "codesys",
                "--output",
                str(destination),
                "--coverage",
                str(coverage_path),
            )
        )
        == 0
    )

    root = ET.fromstring(destination.read_text(encoding="utf-8"))
    namespace = {"p": PLCOPEN_CODESYS_NAMESPACE}
    assert root.find(".//p:pou[@name='PLC_PRG']", namespace) is not None
    assert root.find(".//p:task[@name='MainTask']", namespace) is not None
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    assert coverage["target"] == "codesys-plcopen-xml"
    assert coverage["global_variable_count"] == 2
    assert coverage["user_variable_count"] == 1
    assert coverage["physical_io_variable_count"] == 0
    assert coverage["other_classification_variable_count"] == 1
    assert coverage["physical_io_binding_status"] == "not_applicable"
    assert coverage["preserved_rung_count"] == 1
