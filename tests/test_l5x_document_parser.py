from pathlib import Path

import pytest

from twinforge.model import (
    AddOnInstruction,
    Module,
    Program,
    SoftwareComponentKind,
)
from twinforge.model.source_extension import SourceNode
from twinforge.parsers.l5x import L5XParser, L5XTargetType


DATA = Path(__file__).parent / "data/standalone"
REGRESSION_DATA = Path(__file__).parent / "data/regression"
CONTROLLER = (
    Path(__file__).parent
    / "data/basic/BoosterCompressor_20260128.L5X"
)


def test_dispatches_standalone_module_and_preserves_document():
    document = L5XParser().parse_document(DATA / "module.L5X")

    assert document.target_type is L5XTargetType.MODULE
    assert isinstance(document.target, Module)
    assert document.target.name == "DriveModule"
    assert document.target.address == "192.168.1.80"
    connection = document.target.connections[0]
    assert connection.input_connection_point == 1
    assert connection.output_connection_point == 2
    assert connection.input_size_bytes == 8
    assert connection.output_size_bytes == 4
    assert document.software_component is None
    root = document.source_extensions[0].root
    assert root.name == "RSLogix5000Content"
    assert root.attributes["TargetType"] == "Module"
    assert any(child.name == "Controller" for child in root.children)


def test_dispatches_program_with_software_component_wrapper():
    document = L5XParser().parse_document(DATA / "program.L5X")

    assert document.target_type is L5XTargetType.PROGRAM
    assert isinstance(document.target, Program)
    assert list(document.target.tags) == ["Dvc"]
    assert document.software_component is not None
    assert (
        document.software_component.kind
        is SoftwareComponentKind.PROGRAM
    )
    assert document.software_component.implementation is document.target


def test_dispatches_aoi_with_function_block_wrapper():
    document = L5XParser().parse_document(DATA / "aoi.L5X")

    assert document.target_type is L5XTargetType.ADD_ON_INSTRUCTION
    assert isinstance(document.target, AddOnInstruction)
    assert document.target.description == "PowerFlex 525"
    assert document.software_component is not None
    assert (
        document.software_component.kind
        is SoftwareComponentKind.FUNCTION_BLOCK
    )
    assert document.software_component.vendor == "Example"


def test_rejects_ambiguous_target_elements(tmp_path: Path):
    path = tmp_path / "ambiguous.L5X"
    path.write_text(
        """
        <RSLogix5000Content TargetType="Module" TargetName="Duplicate">
          <Module Use="Target" Name="One"/>
          <Module Use="Target" Name="Two"/>
        </RSLogix5000Content>
        """,
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="exactly one"):
        L5XParser().parse_document(path)


def test_dispatches_controller_without_changing_legacy_parse():
    parser = L5XParser()
    document = parser.parse_document(CONTROLLER)
    plant = parser.parse(CONTROLLER, report_mode=None)

    assert document.target_type is L5XTargetType.CONTROLLER
    assert next(plant.iter_controllers()).name == document.target.name
    assert document.target_name == "booster_compressor"


def test_unknown_content_fixture_survives_document_and_model_conversion():
    document = L5XParser().parse_document(
        REGRESSION_DATA / "unknown_content.L5X"
    )

    document_root = document.source_extensions[0].root
    assert document_root.attributes["FutureDocumentAttribute"] == (
        "preserve-document-attribute"
    )
    assert _child(document_root, "FutureDocumentElement").attributes == {
        "Evidence": "preserve-document-element"
    }

    program = document.target
    assert isinstance(program, Program)
    program_root = program.source_extensions[0].root
    assert program_root.attributes["FutureProgramAttribute"] == (
        "preserve-program-attribute"
    )
    assert _child(program_root, "FutureProgramElement").attributes == {
        "Evidence": "preserve-program-element"
    }

    tag_root = program.tags["Input"].source_extensions[0].root
    assert tag_root.attributes["FutureTagAttribute"] == (
        "preserve-tag-attribute"
    )
    future_tag = _child(tag_root, "FutureTagElement")
    assert future_tag.attributes == {"Evidence": "preserve-tag-element"}
    assert _child(future_tag, "NestedFuture").attributes == {
        "Value": "preserve-nested-element"
    }

    routine = program.routines["Main"]
    routine_root = routine.source_extensions[0].root
    assert routine_root.attributes["FutureRoutineAttribute"] == (
        "preserve-routine-attribute"
    )
    assert _child(routine_root, "FutureRoutineElement").attributes == {
        "Evidence": "preserve-routine-element"
    }

    rung_root = routine.ladder_rungs[0].source_extensions[0].root
    assert rung_root.attributes["FutureRungAttribute"] == (
        "preserve-rung-attribute"
    )
    assert _child(rung_root, "FutureRungElement").attributes == {
        "Evidence": "preserve-rung-element"
    }


def _child(node: SourceNode, name: str) -> SourceNode:
    return next(child for child in node.children if child.name == name)
