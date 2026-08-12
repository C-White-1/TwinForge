from pathlib import Path

from twinforge.exporters import TextReportExporter
from twinforge.parsers import L5XParser


SAMPLE = Path(__file__).parent / "data/aoi/Str_Capacity_AOI.L5X"
DEPENDENCY_SAMPLE = (
    Path(__file__).parent / "data/aoi/dependencies_and_locals.L5X"
)
SCAN_MODE_SAMPLE = (
    Path(__file__).parent / "data/aoi/scan_mode_routines.L5X"
)


def test_converts_structured_text_add_on_instruction() -> None:
    parser = L5XParser()
    controller = parser.parse(SAMPLE, report_mode=None).controllers[0]

    assert parser.diagnostics == []
    instruction = controller.add_on_instructions["Str_Capacity"]
    assert instruction.revision == "1.0"
    assert instruction.vendor == "Jeremy Medders"
    assert instruction.execute_prescan is False
    assert instruction.execute_postscan is False
    assert instruction.execute_enable_in_false is False

    ref_data = instruction.parameters["Ref_Data"]
    assert ref_data.usage == "InOut"
    assert ref_data.data_type == "SINT"
    assert ref_data.dimensions == "1"
    assert ref_data.required is True
    assert ref_data.constant is True

    value = instruction.parameters["Val"]
    assert value.default_value is not None
    assert value.default_value.value == 0
    assert value.default_value.data_type == "DINT"

    routine = instruction.routines["Logic"]
    assert routine.language == "ST"
    assert [line.number for line in routine.structured_text_lines] == list(
        range(7)
    )
    assert routine.structured_text_lines[2].text == "\tStr_Capacity"
    assert "SIZE(Ref_Data, 0, Val);" in routine.structured_text


def test_reports_aoi_parameters_and_structured_text() -> None:
    controller = L5XParser().parse(
        SAMPLE, report_mode=None
    ).controllers[0]

    report = TextReportExporter().export(controller).files[
        "add_on_instructions.txt"
    ]
    assert "Instruction: Str_Capacity" in report
    assert "Ref_Data" in report
    assert "InOut" in report
    assert "SIZE(Ref_Data, 0, Val);" in report


def test_converts_local_tags_alias_parameters_and_dependencies() -> None:
    parser = L5XParser()
    controller = parser.parse(
        DEPENDENCY_SAMPLE, report_mode=None
    ).controllers[0]

    assert parser.diagnostics == []
    instruction = controller.add_on_instructions["MainAOI"]
    datatype = controller.datatypes["ExampleData"]
    config = instruction.parameters["Config"]
    config_state = instruction.local_tags["ConfigState"]
    assert config.data_type_definition is datatype
    assert config_state.data_type_definition is datatype
    assert config.default_value is None
    assert config.composite_default_value is not None
    assert config.composite_default_value.data_type_definition is datatype
    config_value = config.composite_default_value.root.children[0]
    assert config_value.value == 7
    assert config_value.member_definition is datatype.members[0]
    assert config_state.initial_value is None
    assert config_state.composite_initial_value is not None
    assert config_state.composite_initial_value.data_type_definition is datatype
    state_value = config_state.composite_initial_value.root.children[0]
    assert state_value.value == 9
    assert state_value.member_definition is datatype.members[0]
    state = instruction.local_tags["State"]
    assert instruction.parameters["Status"].alias_for == "State.0"
    assert instruction.parameters["Status"].alias_target is state
    assert instruction.parameters["Status"].data_type is None
    assert instruction.parameters["Status"].resolved_data_type == "BOOL"
    assert instruction.parameters["Status"].effective_data_type == "BOOL"
    config_value_alias = instruction.parameters["ConfigValue"]
    assert config_value_alias.alias_target is config
    assert config_value_alias.alias_member_path == (datatype.members[0],)
    assert config_value_alias.effective_data_type == "DINT"
    history_alias = instruction.parameters["HistoryValue"]
    assert history_alias.alias_target is instruction.local_tags["History"]
    assert history_alias.alias_array_indices == (1,)
    assert history_alias.alias_member_path == (datatype.members[0],)
    assert history_alias.effective_data_type == "DINT"
    assert state.data_type == "DINT"
    assert state.initial_value is not None
    assert state.initial_value.value == 0
    assert [
        (dependency.dependency_type, dependency.name)
        for dependency in instruction.dependencies
    ] == [
        ("DataType", "ExampleData"),
        ("AddOnInstructionDefinition", "Helper"),
    ]
    assert all(
        dependency.target is not None
        for dependency in instruction.dependencies
    )


def test_unresolved_aoi_parameter_alias_target_is_diagnosed_and_preserved(
    tmp_path,
) -> None:
    source = tmp_path / "missing_alias_target.L5X"
    source.write_text(
        """
        <RSLogix5000Content TargetName="AOIContext">
          <Controller Name="TestController">
            <AddOnInstructionDefinitions>
              <AddOnInstructionDefinition Name="AliasAOI">
                <Parameters>
                  <Parameter Name="Ready" TagType="Alias" Usage="Output"
                   AliasFor="MissingState.0"/>
                </Parameters>
              </AddOnInstructionDefinition>
            </AddOnInstructionDefinitions>
          </Controller>
        </RSLogix5000Content>
        """,
        encoding="utf-8",
    )
    parser = L5XParser()

    controller = parser.parse(source, report_mode=None).controllers[0]

    parameter = controller.add_on_instructions["AliasAOI"].parameters["Ready"]
    assert parameter.alias_for == "MissingState.0"
    assert parameter.alias_target is None
    assert parameter.resolved_data_type is None
    assert [item.code for item in parser.diagnostics] == [
        "unresolved_aoi_parameter_alias_target"
    ]
    assert parser.diagnostics[0].raw_value == "MissingState.0"


def test_unresolved_aoi_alias_udt_member_is_diagnosed_and_preserved(
    tmp_path,
) -> None:
    source = tmp_path / "missing_alias_member.L5X"
    source.write_text(
        """
        <RSLogix5000Content TargetName="AOIContext">
          <Controller Name="TestController">
            <DataTypes>
              <DataType Name="ConfigType">
                <Members><Member Name="Value" DataType="DINT"/></Members>
              </DataType>
            </DataTypes>
            <AddOnInstructionDefinitions>
              <AddOnInstructionDefinition Name="AliasAOI">
                <Parameters>
                  <Parameter Name="Config" DataType="ConfigType"
                   Usage="Input"/>
                  <Parameter Name="Ready" TagType="Alias" Usage="Output"
                   AliasFor="Config.Missing"/>
                </Parameters>
              </AddOnInstructionDefinition>
            </AddOnInstructionDefinitions>
          </Controller>
        </RSLogix5000Content>
        """,
        encoding="utf-8",
    )
    parser = L5XParser()

    controller = parser.parse(source, report_mode=None).controllers[0]

    parameter = controller.add_on_instructions["AliasAOI"].parameters["Ready"]
    assert parameter.alias_for == "Config.Missing"
    assert parameter.alias_target is not None
    assert parameter.alias_member_path == ()
    assert parameter.resolved_data_type is None
    assert [item.code for item in parser.diagnostics] == [
        "unresolved_aoi_alias_member"
    ]
    assert parser.diagnostics[0].raw_value == "Config.Missing"


def test_out_of_bounds_aoi_alias_index_is_diagnosed_and_preserved(tmp_path):
    source = tmp_path / "alias_index.L5X"
    source.write_text(
        """
        <RSLogix5000Content TargetName="AOIContext">
          <Controller Name="TestController">
            <AddOnInstructionDefinitions>
              <AddOnInstructionDefinition Name="AliasAOI">
                <Parameters>
                  <Parameter Name="Selected" TagType="Alias" Usage="Output"
                   AliasFor="Values[2]"/>
                </Parameters>
                <LocalTags>
                  <LocalTag Name="Values" DataType="DINT" Dimensions="2"/>
                </LocalTags>
              </AddOnInstructionDefinition>
            </AddOnInstructionDefinitions>
          </Controller>
        </RSLogix5000Content>
        """,
        encoding="utf-8",
    )
    parser = L5XParser()

    controller = parser.parse(source, report_mode=None).controllers[0]

    parameter = controller.add_on_instructions["AliasAOI"].parameters["Selected"]
    assert parameter.alias_for == "Values[2]"
    assert parameter.alias_array_indices == (2,)
    assert parameter.alias_target is not None
    assert [item.code for item in parser.diagnostics] == [
        "aoi_alias_array_index_out_of_bounds"
    ]


def test_captures_scan_mode_routines_separately_from_primary_logic():
    parser = L5XParser()
    controller = parser.parse(
        SCAN_MODE_SAMPLE,
        report_mode=None,
    ).controllers[0]

    assert parser.diagnostics == []
    instruction = controller.add_on_instructions["LifecycleAOI"]
    assert list(instruction.routines) == ["Logic"]
    assert list(instruction.scan_mode_routines) == [
        "Prescan",
        "Postscan",
        "EnableInFalse",
    ]
    assert instruction.execute_prescan is True
    assert instruction.execute_postscan is False
    assert instruction.execute_enable_in_false is True
    assert (
        instruction.scan_mode_routines["Postscan"].structured_text
        == "Value := -1;"
    )
    assert [item.name for item in instruction.iter_routines()] == [
        "Logic",
        "Prescan",
        "Postscan",
        "EnableInFalse",
    ]
