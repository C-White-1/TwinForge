import xml.etree.ElementTree as ET
from pathlib import Path

from twinforge.converters import DiagnosticSeverity
from twinforge.converters.l5x import (
    convert_program,
    convert_tag,
    resolve_engineering_units,
)
from twinforge.model import (
    Controller,
    EngineeringUnitConfidence,
    EngineeringUnitSource,
    Identity,
    LadderRung,
    Program,
    Routine,
    Tag,
)
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
    assert base.initial_value is not None
    assert base.initial_value.value is False
    assert base.initial_value.data_type == "BOOL"
    assert base.initial_value.lexical_value == "0"
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


def test_parser_resolves_tag_engineering_units_and_provenance():
    controller = L5XParser().parse(
        SAMPLE_L5X, report_mode=None
    ).controllers[0]

    process_value = controller.tags["PT102_PV"]
    assert process_value.engineering_unit is not None
    assert process_value.engineering_unit.symbol == "barg"
    assert (
        process_value.engineering_unit.source
        is EngineeringUnitSource.MODULE_CHANNEL
    )
    assert (
        process_value.engineering_unit.confidence
        is EngineeringUnitConfidence.EXPLICIT
    )
    assert process_value.engineering_unit.source_operand == "Local:4:I.CH2DATA"
    assert process_value.engineering_range is not None
    assert process_value.engineering_range.lower == 0.0
    assert process_value.engineering_range.upper == 150.0

    high_high = controller.tags["CFG_PT102_HH"]
    assert high_high.engineering_unit is not None
    assert high_high.engineering_unit.symbol == "barg"
    assert high_high.engineering_unit.source is EngineeringUnitSource.COMPARISON
    assert (
        high_high.engineering_unit.confidence
        is EngineeringUnitConfidence.DERIVED
    )
    assert high_high.engineering_unit.inherited_from == "PT102_PV"
    assert {
        evidence.source for evidence in high_high.engineering_unit_evidence
    } == {
        EngineeringUnitSource.COMPARISON,
        EngineeringUnitSource.TAG_DESCRIPTION,
    }

    assert controller.tags["PT102_HH_Alm"].engineering_unit is None


def test_engineering_unit_conflicts_are_diagnosed():
    controller = Controller(name="PLC", identity=Identity())
    controller.add_tag(Tag(name="Pressure", description="Pressure (barg)"))
    controller.add_tag(Tag(name="Limit", description="Limit (C)"))
    program = Program(name="Program")
    routine = Routine(name="Main", language="RLL")
    routine.ladder_rungs.append(
        LadderRung(number=0, text="GRT(Pressure,Limit);")
    )
    program.add_routine(routine)
    controller.add_program(program)
    diagnostics = []

    resolve_engineering_units(controller, diagnostics=diagnostics)

    assert any(
        diagnostic.code == "engineering_unit_conflict"
        and diagnostic.severity is DiagnosticSeverity.WARNING
        for diagnostic in diagnostics
    )


def test_parser_promotes_scalar_setpoint_values() -> None:
    parser = L5XParser()

    plant = parser.parse(SAMPLE_L5X, report_mode=None)
    controller = plant.controllers[0]

    pressure = controller.get_tag("CFG_PT102_HH")
    delay = controller.get_tag("CFG_TripDelay")
    assert pressure is not None and pressure.initial_value is not None
    assert pressure.initial_value.value == 120.0
    assert pressure.initial_value.data_type == "REAL"
    assert pressure.initial_value.radix == "Float"
    assert delay is not None and delay.initial_value is not None
    assert delay.initial_value.value == 2000
    assert delay.initial_value.data_type == "DINT"


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
