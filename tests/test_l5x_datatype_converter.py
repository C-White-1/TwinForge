import xml.etree.ElementTree as ET

from twinforge.converters import DiagnosticSeverity
from twinforge.converters.l5x import convert_datatype
from twinforge.parsers import L5XParser
from twinforge.parsers.l5x.capture import capture_section
from twinforge.schema.l5x import DATATYPE_ATTRIBUTES, DATATYPE_ELEMENTS


def _datatype(xml: str):
    return capture_section(
        ET.fromstring(xml),
        DATATYPE_ATTRIBUTES,
        DATATYPE_ELEMENTS,
    )


def test_parser_converts_datatypes_and_resolves_tag_and_member_references(tmp_path):
    source = tmp_path / "datatypes.L5X"
    source.write_text(
        """
        <RSLogix5000Content TargetName="Demo">
          <Controller Name="Demo">
            <DataTypes>
              <DataType Name="AlarmConfig" Family="NoFamily" Class="User">
                <Members>
                  <Member Name="Enabled" DataType="BOOL" Dimension="0"
                          Radix="Decimal" Hidden="false"
                          ExternalAccess="Read/Write" />
                  <Member Name="EnabledBit" DataType="BIT" Dimension="0"
                          Target="Enabled" BitNumber="0" Hidden="false" />
                </Members>
              </DataType>
              <DataType Name="MotorConfig" Family="NoFamily" Class="User">
                <Description>Motor configuration</Description>
                <Members>
                  <Member Name="Alarm" DataType="AlarmConfig" Dimension="0"
                          Hidden="false" Future="keep" />
                  <Member Name="Speed" DataType="REAL" Dimension="0" />
                </Members>
              </DataType>
            </DataTypes>
            <Tags>
              <Tag Name="Motor" TagType="Base" DataType="MotorConfig" />
            </Tags>
            <Programs>
              <Program Name="Main">
                <Tags><Tag Name="Alarm" TagType="Base" DataType="AlarmConfig" /></Tags>
              </Program>
            </Programs>
          </Controller>
        </RSLogix5000Content>
        """,
        encoding="utf-8",
    )
    parser = L5XParser()

    controller = parser.parse(source, report_mode=None).controllers[0]

    alarm_type = controller.get_datatype("AlarmConfig")
    motor_type = controller.get_datatype("MotorConfig")
    assert alarm_type is not None
    assert motor_type is not None
    assert alarm_type.parent is controller
    assert alarm_type.members[1].target == "Enabled"
    assert alarm_type.members[1].bit_number == 0
    assert motor_type.description == "Motor configuration"
    assert motor_type.members[0].data_type is alarm_type
    assert motor_type.members[1].data_type_name == "REAL"
    assert motor_type.members[1].data_type is None
    assert motor_type.members[0].source_extensions[0].root.attributes["Future"] == "keep"

    controller_tag = controller.get_tag("Motor")
    program = controller.get_program("Main")
    assert program is not None
    program_tag = program.get_tag("Alarm")
    assert controller_tag is not None
    assert program_tag is not None
    assert controller_tag.data_type_definition is motor_type
    assert program_tag.data_type_definition is alarm_type
    assert parser.diagnostics == []


def test_datatype_converter_reports_bad_members_and_preserves_unknown_data():
    section = _datatype(
        """
        <DataType Name="Broken" FutureAttribute="keep">
          <Members>
            <Member Name="Duplicate" DataType="BOOL" Hidden="perhaps" />
            <Member Name="Duplicate" DataType="DINT" />
            <Member Name="NoType" />
            <Member DataType="BOOL" />
          </Members>
          <FutureElement Preserve="yes" />
        </DataType>
        """
    )
    diagnostics = []

    datatype = convert_datatype(section, diagnostics=diagnostics)

    assert [member.name for member in datatype.members] == ["Duplicate", "NoType"]
    assert datatype.source_extensions[0].root.attributes["FutureAttribute"] == "keep"
    assert datatype.source_extensions[0].root.children[-1].name == "FutureElement"
    assert {item.code for item in diagnostics} == {
        "invalid_boolean",
        "duplicate_datatype_member",
        "datatype_member_type_missing",
        "datatype_member_missing_name",
    }
    assert any(item.severity is DiagnosticSeverity.ERROR for item in diagnostics)
