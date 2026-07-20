import xml.etree.ElementTree as ET
from pathlib import Path

from twinforge.converters import DiagnosticSeverity
from twinforge.converters.l5x import convert_program, convert_tag
from twinforge.parsers import L5XParser
from twinforge.parsers.l5x.capture import capture_section
from twinforge.schema.l5x import (
    PROGRAM_ATTRIBUTES,
    PROGRAM_ELEMENTS,
    TAG_ATTRIBUTES,
    TAG_ELEMENTS,
)


SAMPLE_L5X = Path(__file__).parent / "data/basic/BoosterCompressor_20260128.L5X"


def _tag(xml: str):
    return capture_section(ET.fromstring(xml), TAG_ATTRIBUTES, TAG_ELEMENTS)


def test_parser_converts_all_sample_controller_tags():
    parser = L5XParser()

    plant = parser.parse(SAMPLE_L5X, report_mode=None)

    controller = plant.controllers[0]
    assert len(controller.tags) == 154

    alias = controller.get_tag("AlmActive")
    assert alias is not None
    assert alias.parent is controller
    assert alias.tag_type == "Alias"
    assert alias.alias_for == "Local:3:O.Data.14"
    assert alias.data_type is None
    assert alias.description == "Compressor Alarm Active"

    base = controller.get_tag("AlmHornSil")
    assert base is not None
    assert base.tag_type == "Base"
    assert base.data_type == "BOOL"
    assert base.constant is False
    assert base.external_access == "Read/Write"
    data_nodes = [
        child
        for child in base.source_extensions[0].root.children
        if child.name == "Data"
    ]
    assert [node.attributes["Format"] for node in data_nodes] == [
        "L5K",
        "Decorated",
    ]
    assert data_nodes[0].text.strip() == "0"
    assert data_nodes[1].children[0].attributes["Value"] == "0"
    assert parser.diagnostics == []


def test_program_scoped_tags_are_converted_and_parented():
    section = capture_section(
        ET.fromstring(
            """
            <Program Name="ProgramWithTags">
              <Tags>
                <Tag Name="LocalValue" TagType="Base" DataType="DINT"
                     Constant="false" />
              </Tags>
            </Program>
            """
        ),
        PROGRAM_ATTRIBUTES,
        PROGRAM_ELEMENTS,
    )

    program = convert_program(section)

    tag = program.get_tag("LocalValue")
    assert tag is not None
    assert tag.parent is program
    assert tag.data_type == "DINT"
    assert tag.constant is False


def test_tag_converter_reports_invalid_and_incomplete_metadata():
    diagnostics = []

    tag = convert_tag(
        _tag(
            """
            <Tag Name="Broken" TagType="Future" Constant="perhaps"
                 FutureAttribute="keep">
              <FutureData Preserve="yes" />
            </Tag>
            """
        ),
        diagnostics=diagnostics,
    )

    assert tag.tag_type == "Future"
    assert tag.constant is None
    assert tag.source_extensions[0].root.attributes["FutureAttribute"] == "keep"
    assert tag.source_extensions[0].root.children[0].name == "FutureData"
    assert {item.code for item in diagnostics} == {
        "unknown_tag_type",
        "invalid_boolean",
    }
    assert all(item.severity is DiagnosticSeverity.WARNING for item in diagnostics)


def test_alias_and_base_require_their_identity_fields():
    alias_diagnostics = []
    base_diagnostics = []

    convert_tag(
        _tag('<Tag Name="Alias" TagType="Alias" />'),
        diagnostics=alias_diagnostics,
    )
    convert_tag(
        _tag('<Tag Name="Base" TagType="Base" />'),
        diagnostics=base_diagnostics,
    )

    assert alias_diagnostics[0].code == "alias_target_missing"
    assert base_diagnostics[0].code == "base_tag_data_type_missing"
