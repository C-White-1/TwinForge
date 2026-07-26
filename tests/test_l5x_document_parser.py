from pathlib import Path

import pytest

from twinforge.model import (
    AddOnInstruction,
    Module,
    Program,
    SoftwareComponentKind,
)
from twinforge.parsers.l5x import L5XParser, L5XTargetType


DATA = Path(__file__).parent / "data/standalone"
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
