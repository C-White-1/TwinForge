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
    assert alarm_type.members[1].target_member is alarm_type.members[0]
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


def test_unresolved_udt_bit_overlay_target_is_diagnosed_and_preserved(tmp_path):
    source = tmp_path / "overlay.L5X"
    source.write_text(
        """
        <RSLogix5000Content TargetName="Demo">
          <Controller Name="Demo">
            <DataTypes>
              <DataType Name="Flags" Family="NoFamily" Class="User">
                <Members>
                  <Member Name="Ready" DataType="BIT" Dimension="0"
                   Target="MissingWord" BitNumber="0"/>
                </Members>
              </DataType>
            </DataTypes>
          </Controller>
        </RSLogix5000Content>
        """,
        encoding="utf-8",
    )
    parser = L5XParser()

    controller = parser.parse(source, report_mode=None).controllers[0]

    member = controller.datatypes["Flags"].members[0]
    assert member.target == "MissingWord"
    assert member.bit_number == 0
    assert member.target_member is None
    assert [item.code for item in parser.diagnostics] == [
        "unresolved_datatype_overlay_target"
    ]
    assert parser.diagnostics[0].severity is DiagnosticSeverity.WARNING


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


def test_composite_values_diagnose_only_explicit_udt_schema_conflicts(tmp_path):
    source = tmp_path / "composite_conflicts.L5X"
    source.write_text(
        """
        <RSLogix5000Content TargetName="Demo">
          <Controller Name="Demo">
            <DataTypes>
              <DataType Name="Recipe" Family="NoFamily" Class="User">
                <Members>
                  <Member Name="Count" DataType="DINT" Dimension="0"/>
                  <Member Name="Optional" DataType="BOOL" Dimension="0"/>
                </Members>
              </DataType>
            </DataTypes>
            <Tags>
              <Tag Name="Current" TagType="Base" DataType="Recipe">
                <Data Format="Decorated">
                  <Structure DataType="Recipe">
                    <DataValueMember Name="Count" DataType="REAL" Value="1.0"/>
                    <DataValueMember Name="Future" DataType="DINT" Value="2"/>
                  </Structure>
                </Data>
              </Tag>
            </Tags>
          </Controller>
        </RSLogix5000Content>
        """,
        encoding="utf-8",
    )
    parser = L5XParser()

    controller = parser.parse(source, report_mode=None).controllers[0]

    assert {item.code for item in parser.diagnostics} == {
        "composite_member_not_in_datatype",
        "composite_member_type_mismatch",
    }
    assert all(
        item.severity is DiagnosticSeverity.WARNING
        for item in parser.diagnostics
    )
    composite = controller.tags["Current"].composite_initial_value
    assert composite is not None
    assert composite.root.children[0].member_definition is not None
    assert composite.root.children[1].member_definition is None


def test_logix_decorated_bit_and_string_members_are_type_compatible(tmp_path):
    source = tmp_path / "decorated_equivalence.L5X"
    source.write_text(
        """
        <RSLogix5000Content TargetName="Demo">
          <Controller Name="Demo">
            <DataTypes>
              <DataType Name="Status">
                <Members>
                  <Member Name="Storage" DataType="SINT" Dimension="0"/>
                  <Member Name="Ready" DataType="BIT" Dimension="0"
                   Target="Storage" BitNumber="0"/>
                </Members>
              </DataType>
              <DataType Name="ShortString" Family="StringFamily">
                <Members>
                  <Member Name="LEN" DataType="DINT" Dimension="0"/>
                  <Member Name="DATA" DataType="SINT" Dimension="8"/>
                </Members>
              </DataType>
            </DataTypes>
            <Tags>
              <Tag Name="State" TagType="Base" DataType="Status">
                <Data Format="Decorated">
                  <Structure DataType="Status">
                    <DataValueMember Name="Ready" DataType="BOOL" Value="0"/>
                  </Structure>
                </Data>
              </Tag>
              <Tag Name="Label" TagType="Base" DataType="ShortString">
                <Data Format="Decorated">
                  <Structure DataType="ShortString">
                    <DataValueMember Name="LEN" DataType="DINT" Value="0"/>
                    <DataValueMember Name="DATA" DataType="ShortString"/>
                  </Structure>
                </Data>
              </Tag>
            </Tags>
          </Controller>
        </RSLogix5000Content>
        """,
        encoding="utf-8",
    )
    parser = L5XParser()

    parser.parse(source, report_mode=None)

    assert parser.diagnostics == []
