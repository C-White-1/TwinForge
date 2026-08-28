"""Synthetic coverage for lowering CCW interchange into neutral models."""

from typing import Any

from twinforge.converters.ccw import lower_ccw_project
from twinforge.interchange import load_ccw_project
from twinforge.model import (
    LadderInstruction,
    LadderOperation,
    LadderParallel,
)


def _instruction(
    mnemonic: str,
    operand: str,
    column: int,
) -> dict[str, Any]:
    return {
        "kind": "instruction",
        "mnemonic": mnemonic,
        "operand": operand,
        "alias": f"{operand} alias",
        "annotations": [f"{mnemonic} evidence"],
        "position": {"column": column, "row": 0},
    }


def _document() -> dict[str, Any]:
    return {
        "schema_version": "ccw-project-v1",
        "source": {
            "reference": "synthetic-lowering-fixture",
            "size": 2048,
            "sha256": "a" * 64,
            "entry_count": 9,
        },
        "project": {
            "name": "Synthetic Parallel Conveyor",
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
                            "elements": [
                                {
                                    "kind": "parallel",
                                    "branches": [
                                        {
                                            "kind": "series",
                                            "elements": [
                                                _instruction("XIC", "Start", 1)
                                            ],
                                        },
                                        {
                                            "kind": "series",
                                            "elements": [
                                                _instruction("XIO", "Stop", 1)
                                            ],
                                        },
                                    ],
                                },
                                _instruction("OTE", "Motor", 2),
                                _instruction("ADD", "Counter", 3),
                            ],
                        },
                        "raw_sha256": "b" * 64,
                    }
                ],
                "diagnostics": ["program evidence retained"],
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
                "usages": [],
                "seal_in_rungs": [],
            }
        ],
        "unresolved_operands": ["Counter"],
        "diagnostics": ["source evidence retained"],
        "evidence": {
            "sensitive_entries": ["Controller/DevicePref.xml"],
            "unknown_entries": ["Controller/opaque.bin"],
        },
    }


def test_lowering_preserves_variables_programs_and_recursive_topology() -> None:
    document = _document()

    result = lower_ccw_project(load_ccw_project(document))

    controller = result.controller
    assert controller.name == "Synthetic Parallel Conveyor"
    assert controller.source_extensions[0].metadata["document"] == document
    tag = controller.tags["Start"]
    assert tag.data_type == "BOOL"
    assert tag.description == "Start PB"
    assert tag.metadata["physical_source"] == "_IO_EM_DI_00"
    assert tag.source_extensions[0].metadata["evidence"] == document["variables"][0]

    program = controller.programs["Sequence"]
    assert program.parent is controller
    routine = program.routines["Sequence"]
    assert routine.parent is program
    rung = routine.ladder_rungs[0]
    assert rung.source_sha256 == "b" * 64
    assert rung.position is not None and rung.position.row == 1
    assert rung.network is not None

    parallel = rung.network.elements[0]
    assert isinstance(parallel, LadderParallel)
    first_contact = parallel.branches[0].elements[0]
    second_contact = parallel.branches[1].elements[0]
    assert isinstance(first_contact, LadderInstruction)
    assert isinstance(second_contact, LadderInstruction)
    assert first_contact.operation is LadderOperation.NORMALLY_OPEN_CONTACT
    assert second_contact.operation is LadderOperation.NORMALLY_CLOSED_CONTACT

    coil = rung.network.elements[1]
    unknown = rung.network.elements[2]
    assert isinstance(coil, LadderInstruction)
    assert isinstance(unknown, LadderInstruction)
    assert coil.operation is LadderOperation.COIL
    assert unknown.operation is LadderOperation.UNSUPPORTED
    assert unknown.source_mnemonic == "ADD"
    assert unknown.operand == "Counter"
    assert result.artifact.to_document() == document


def test_lowering_reports_unsupported_and_source_evidence() -> None:
    result = lower_ccw_project(load_ccw_project(_document()))

    assert result.converted_instruction_count == 3
    assert result.unsupported_instruction_count == 1
    assert {diagnostic.code for diagnostic in result.diagnostics} == {
        "unsupported_ccw_instruction",
        "ccw_program_diagnostic",
        "ccw_source_diagnostic",
        "ccw_unresolved_operand",
    }
    unsupported = next(
        diagnostic
        for diagnostic in result.diagnostics
        if diagnostic.code == "unsupported_ccw_instruction"
    )
    assert unsupported.raw_value == "ADD"
    assert unsupported.object_name == "Counter"


def test_lowering_maps_ccw_otr_to_reset_coil_semantics() -> None:
    document = _document()
    instruction = document["programs"][0]["rungs"][0]["network"]["elements"][2]
    instruction["mnemonic"] = "OTR"
    instruction["operand"] = "SizeFault"

    result = lower_ccw_project(load_ccw_project(document))
    rung = result.controller.programs["Sequence"].routines["Sequence"].ladder_rungs[0]
    assert rung.network is not None
    reset = rung.network.elements[2]

    assert isinstance(reset, LadderInstruction)
    assert reset.operation is LadderOperation.RESET_COIL
    assert reset.source_mnemonic == "OTR"
    assert result.converted_instruction_count == 4
    assert result.unsupported_instruction_count == 0


def test_lowering_marks_physical_io_for_target_device_mapping() -> None:
    document = _document()
    variable = document["variables"][0]
    variable["classification"] = "physical_io"
    variable["aliases"] = []
    variable["physical_source"] = None

    result = lower_ccw_project(load_ccw_project(document))

    assert result.controller.tags["Start"].description is None


def test_lowering_drops_duplicate_variable_and_reports_it_as_dropped() -> None:
    document = _document()
    duplicate = dict(document["variables"][0])
    duplicate["aliases"] = ["Second Start"]
    document["variables"].append(duplicate)

    result = lower_ccw_project(load_ccw_project(document))

    assert result.controller.tags["Start"].description == "Start PB"
    duplicate_diagnostic = next(
        diagnostic
        for diagnostic in result.diagnostics
        if diagnostic.code == "duplicate_ccw_variable"
    )
    assert "was dropped" in duplicate_diagnostic.message
    assert "retained" not in duplicate_diagnostic.message


def test_lowering_drops_duplicate_program_without_leaking_instruction_counts() -> None:
    document = _document()
    duplicate = {
        "name": "Sequence",
        "language": "LD",
        "source_entry": "Controller/Sequence2.stf",
        "rungs": [
            {
                "number": 1,
                "position": {"column": 0, "row": 1},
                "network": {
                    "kind": "series",
                    "elements": [
                        _instruction("XIC", "Extra", 1),
                        _instruction("OTE", "ExtraOut", 2),
                    ],
                },
                "raw_sha256": "c" * 64,
            }
        ],
        "diagnostics": [],
    }
    document["programs"].append(duplicate)

    result = lower_ccw_project(load_ccw_project(document))

    assert tuple(result.controller.programs) == ("Sequence",)
    assert result.converted_instruction_count == 3
    assert result.unsupported_instruction_count == 1
    duplicate_diagnostic = next(
        diagnostic
        for diagnostic in result.diagnostics
        if diagnostic.code == "duplicate_ccw_program"
    )
    assert "was dropped" in duplicate_diagnostic.message
    assert "retained" not in duplicate_diagnostic.message
