from pathlib import Path

from twinforge.assembly import assemble_corpus_devices
from twinforge.parsers.l5x import (
    L5XCorpusParser,
    L5XTargetType,
    WorkspaceEvidence,
)
from twinforge.model import (
    ModuleDataDirection,
    SoftwareCallBindingRole,
    SoftwareParameterFlow,
    SoftwareTagScope,
)


STANDALONE = Path(__file__).parent / "data/standalone"


def _write_controller(path: Path, name: str) -> None:
    path.write_text(
        f"""
        <RSLogix5000Content TargetType="Controller" TargetName="{name}">
          <Controller Use="Target" Name="{name}" />
        </RSLogix5000Content>
        """,
        encoding="utf-8",
    )


def _write_program(path: Path, controller: str, program: str) -> None:
    path.write_text(
        f"""
        <RSLogix5000Content TargetType="Program" TargetName="{program}">
          <Controller Use="Context" Name="{controller}">
            <Programs Use="Context">
              <Program Use="Target" Name="{program}"
               TestEdits="false" Disabled="false" UseAsFolder="false" />
            </Programs>
          </Controller>
        </RSLogix5000Content>
        """,
        encoding="utf-8",
    )


def test_component_bundle_forms_provisional_workspace_and_shared_software():
    corpus = L5XCorpusParser().parse_directory(STANDALONE)

    assert len(corpus.documents) == 3
    assert len(corpus.workspaces) == 1
    workspace = corpus.workspaces[0]
    assert workspace.controller_name == "Example"
    assert workspace.evidence is WorkspaceEvidence.CONTEXT_NAME_ONLY
    assert workspace.confirmed is False
    assert {
        document.target_type for document in workspace.documents
    } == {L5XTargetType.MODULE, L5XTargetType.PROGRAM}
    assert [item.name for item in corpus.shared_software] == ["Dvc_PF525"]
    assert list(corpus.software_index) == ["dvc_pf525"]
    assert len(corpus.software_bindings) == 1
    binding = corpus.software_bindings[0]
    assert binding.target.name == "Dvc"
    assert binding.metadata["controller_name"] == "Example"
    assert [(call.callee, call.line_number) for call in corpus.call_sites] == [
        ("Dvc_PF525", 0)
    ]
    assert len(corpus.resolved_calls) == 1
    resolved_call = corpus.resolved_calls[0]
    assert resolved_call.definition.name == "Dvc_PF525"
    assert resolved_call.instance_tag is binding.target
    assert corpus.unassigned_documents == ()


def test_multiple_plcs_resolve_independently_and_order_does_not_matter(
    tmp_path: Path,
):
    controller_a = tmp_path / "controller_a.L5X"
    controller_b = tmp_path / "controller_b.L5X"
    program_a = tmp_path / "program_a.L5X"
    program_b = tmp_path / "program_b.L5X"
    _write_controller(controller_a, "PLC_A")
    _write_controller(controller_b, "PLC_B")
    _write_program(program_a, "PLC_A", "ProgramA")
    _write_program(program_b, "PLC_B", "ProgramB")

    parser = L5XCorpusParser()
    forward = parser.parse_files(
        [controller_a, program_b, controller_b, program_a]
    )
    reverse = parser.parse_files(
        [program_a, controller_b, program_b, controller_a]
    )

    def ownership(corpus):
        return {
            workspace.controller_name: tuple(
                sorted(document.target_name for document in workspace.documents)
            )
            for workspace in corpus.workspaces
        }

    assert ownership(forward) == {
        "PLC_A": ("PLC_A", "ProgramA"),
        "PLC_B": ("PLC_B", "ProgramB"),
    }
    assert ownership(reverse) == ownership(forward)
    assert all(workspace.confirmed for workspace in forward.workspaces)
    assert forward.unassigned_documents == ()


def test_duplicate_controller_names_leave_component_unassigned(
    tmp_path: Path,
):
    first = tmp_path / "first.L5X"
    second = tmp_path / "second.L5X"
    program = tmp_path / "program.L5X"
    _write_controller(first, "PLC01")
    _write_controller(second, "PLC01")
    _write_program(program, "PLC01", "DriveProgram")

    corpus = L5XCorpusParser().parse_files([first, program, second])

    assert len(corpus.workspaces) == 2
    assert [item.target_name for item in corpus.unassigned_documents] == [
        "DriveProgram"
    ]
    assert {item.code for item in corpus.diagnostics} == {
        "ambiguous_controller_context",
        "duplicate_controller_name",
    }


def test_duplicate_aoi_definitions_do_not_bind_instance_tag(
    tmp_path: Path,
):
    duplicate = tmp_path / "duplicate_aoi.L5X"
    duplicate.write_text(
        (STANDALONE / "aoi.L5X").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    corpus = L5XCorpusParser().parse_files(
        [
            STANDALONE / "program.L5X",
            STANDALONE / "aoi.L5X",
            duplicate,
        ]
    )

    assert len(corpus.shared_software) == 2
    assert corpus.software_bindings == ()
    assert {item.code for item in corpus.diagnostics} == {
        "ambiguous_software_call",
        "ambiguous_software_instance",
        "duplicate_software_definition",
    }


def test_resolved_call_binds_instance_and_required_parameters(
    tmp_path: Path,
):
    aoi = tmp_path / "aoi.L5X"
    program = tmp_path / "program.L5X"
    module = tmp_path / "module.L5X"
    aoi.write_text(
        """
        <RSLogix5000Content TargetType="AddOnInstructionDefinition"
         TargetName="Dvc_PF525">
          <Controller Use="Context" Name="PLC">
            <AddOnInstructionDefinitions Use="Context">
              <AddOnInstructionDefinition Use="Target" Name="Dvc_PF525">
                <Description><![CDATA[PowerFlex 525]]></Description>
                <Parameters>
                  <Parameter Name="EnableIn" DataType="BOOL" Usage="Input"
                   Required="false" Visible="false"/>
                  <Parameter Name="Ref_Module" DataType="MODULE" Usage="InOut"
                   Required="true" Visible="true"/>
                  <Parameter Name="Ref_IO" DataType="DINT" Usage="InOut"
                   Required="true" Visible="true"/>
                  <Parameter Name="Command" DataType="BOOL" Usage="Input"
                   Required="true" Visible="true"/>
                  <Parameter Name="Status" DataType="BOOL" Usage="Output"
                   Required="false" Visible="true"/>
                  <Parameter Name="Ref_ReadMsg" DataType="MESSAGE"
                   Usage="InOut" Required="true" Visible="true"/>
                  <Parameter Name="Ref_MsgData" DataType="DINT"
                   Usage="InOut" Required="true" Visible="true"/>
                  <Parameter Name="Ref_Class" DataType="ST_Class"
                   Usage="InOut" Required="true" Visible="true"/>
                </Parameters>
                <Routines>
                  <Routine Name="Logic" Type="ST">
                    <STContent>
                      <Line Number="0"><![CDATA[
                        Ref_MsgData[0] := 38; // P038 [VoltageClass]
                      ]]></Line>
                      <Line Number="1"><![CDATA[
                        WriteInstance := 34;
                      ]]></Line>
                      <Line Number="2"><![CDATA[
                        WriteInstance := 0;
                      ]]></Line>
                    </STContent>
                  </Routine>
                </Routines>
              </AddOnInstructionDefinition>
            </AddOnInstructionDefinitions>
          </Controller>
        </RSLogix5000Content>
        """,
        encoding="utf-8",
    )
    program.write_text(
        """
        <RSLogix5000Content TargetType="Program" TargetName="Drive">
          <Controller Use="Context" Name="PLC">
            <Programs Use="Context">
              <Program Use="Target" Name="Drive">
                <Tags>
                  <Tag Name="Instance" TagType="Base" DataType="Dvc_PF525"/>
                  <Tag Name="Cmd" TagType="Base" DataType="BOOL"/>
                  <Tag Name="ReadMsg" TagType="Base" DataType="MESSAGE">
                    <Data Format="Message">
                      <MessageParameters MessageType="CIP Generic"
                       RequestedLength="32" ConnectionPath="DriveModule"
                       ServiceCode="16#0032" ObjectType="16#0093"
                       TargetObject="0" AttributeNumber="16#0000"
                       LocalElement="MsgData" DestinationTag="MsgData"
                       LargePacketUsage="false"/>
                    </Data>
                  </Tag>
                  <Tag Name="MsgData" TagType="Base" DataType="DINT"/>
                </Tags>
                <Routines>
                  <Routine Name="Main" Type="RLL">
                    <RLLContent>
                      <Rung Number="3" Type="N">
                        <Text><![CDATA[
                          Dvc_PF525(
                            Instance,DriveModule,DriveModule:I.Data,Cmd,
                            ReadMsg,MsgData,SysDevices
                          );
                        ]]></Text>
                      </Rung>
                    </RLLContent>
                  </Routine>
                </Routines>
              </Program>
            </Programs>
            <Tags>
              <Tag Name="SysDevices" TagType="Base" DataType="ST_Class"/>
            </Tags>
          </Controller>
        </RSLogix5000Content>
        """,
        encoding="utf-8",
    )
    module.write_text(
        """
        <RSLogix5000Content TargetType="Module" TargetName="DriveModule">
          <Controller Use="Context" Name="PLC">
            <Modules Use="Context">
              <Module Use="Target" Name="DriveModule"
               CatalogNumber="ETHERNET-MODULE" Vendor="1"
               ProductType="0" ProductCode="1" Major="1" Minor="1"
               ParentModule="Local" ParentModPortId="1"
               Inhibited="false" MajorFault="false">
                <Communications>
                  <Connections>
                    <Connection Name="Standard" Type="Output" RPI="10000"
                     InputCxnPoint="1" OutputCxnPoint="2"
                     InputSize="8" OutputSize="4" Unicast="true"/>
                  </Connections>
                </Communications>
              </Module>
            </Modules>
          </Controller>
        </RSLogix5000Content>
        """,
        encoding="utf-8",
    )

    corpus = L5XCorpusParser().parse_files([program, aoi, module])

    resolved = corpus.resolved_calls[0]
    assert resolved.instance_tag is not None
    assert resolved.instance_tag.name == "Instance"
    assert [
        (
            binding.role,
            binding.parameter.name if binding.parameter else None,
            binding.target_tag.name if binding.target_tag else None,
            binding.target_tag_scope,
            binding.target_module.name if binding.target_module else None,
            (
                binding.target_connection.name
                if binding.target_connection
                else None
            ),
            binding.module_data_path,
            binding.module_data_direction,
            binding.flow,
        )
        for binding in resolved.argument_bindings
    ] == [
        (
            SoftwareCallBindingRole.INSTANCE,
            None,
            "Instance",
            SoftwareTagScope.PROGRAM,
            None,
            None,
            None,
            None,
            SoftwareParameterFlow.UNKNOWN,
        ),
        (
            SoftwareCallBindingRole.PARAMETER,
            "Ref_Module",
            None,
            None,
            "DriveModule",
            "Standard",
            None,
            ModuleDataDirection.UNKNOWN,
            SoftwareParameterFlow.IN_OUT,
        ),
        (
            SoftwareCallBindingRole.PARAMETER,
            "Ref_IO",
            None,
            None,
            "DriveModule",
            "Standard",
            "I.Data",
            ModuleDataDirection.INPUT,
            SoftwareParameterFlow.IN_OUT,
        ),
        (
            SoftwareCallBindingRole.PARAMETER,
            "Command",
            "Cmd",
            SoftwareTagScope.PROGRAM,
            None,
            None,
            None,
            None,
            SoftwareParameterFlow.INPUT,
        ),
        (
            SoftwareCallBindingRole.PARAMETER,
            "Ref_ReadMsg",
            "ReadMsg",
            SoftwareTagScope.PROGRAM,
            None,
            None,
            None,
            None,
            SoftwareParameterFlow.IN_OUT,
        ),
        (
            SoftwareCallBindingRole.PARAMETER,
            "Ref_MsgData",
            "MsgData",
            SoftwareTagScope.PROGRAM,
            None,
            None,
            None,
            None,
            SoftwareParameterFlow.IN_OUT,
        ),
        (
            SoftwareCallBindingRole.PARAMETER,
            "Ref_Class",
            "SysDevices",
            SoftwareTagScope.CONTROLLER_CONTEXT,
            None,
            None,
            None,
            None,
            SoftwareParameterFlow.IN_OUT,
        ),
    ]
    assert corpus.diagnostics == ()
    assembly = corpus.software_module_assemblies[0]
    assert assembly.workspace_key == corpus.workspaces[0].key
    assert assembly.definition is resolved.definition
    assert assembly.instance_tag is resolved.instance_tag
    assert [item.name for item in assembly.modules] == ["DriveModule"]
    assert any(
        "parameter Ref_IO references DriveModule:I.Data" in evidence
        for evidence in assembly.evidence
    )
    assembled = assemble_corpus_devices(corpus)
    assert len(assembled) == 1
    device = assembled[0].device
    assert device.name == "Instance"
    assert device.model == "PowerFlex 525"
    assert device.module_bindings[0].module is assembly.modules[0]
    assert device.metadata["workspace_key"] == assembly.workspace_key
    interface = device.communication_interfaces[0]
    assert [
        (service.name, service.service_type)
        for service in interface.services
    ] == [("ReadMsg", "explicit_message_read")]
    service = interface.services[0]
    assert service.requested_length == 32
    assert service.connection_path == "DriveModule"
    assert service.local_element == "MsgData"
    assert service.destination_tag == "MsgData"
    assert service.configuration_source == "l5x_message_tag"
    assert service.runtime_mutable is True
    assert device.metadata["explicit_message_payload_tags"] == ("MsgData",)
    assert device.metadata[
        "observed_bulk_read_parameter_candidates"
    ] == (38,)
    assert device.metadata["observed_write_parameter_candidates"] == (34,)
    assert [
        (
            parameter.number,
            parameter.label,
            parameter.code,
            parameter.group_prefix,
            parameter.group_name,
            parameter.display_name,
            parameter.observed_read,
            parameter.observed_write,
            parameter.read_buffer_indices,
        )
        for parameter in device.observed_parameters
    ] == [
        (
            34,
            None,
            "P034",
            "P",
            "Basic Program",
            "Motor NP FLA",
            False,
            True,
            (),
        ),
        (
            38,
            "P038 [VoltageClass]",
            "P038",
            "P",
            "Basic Program",
            "Voltage Class",
            True,
            False,
            (0,),
        ),
    ]
    assert device.observed_parameters[0].definition is not None
    assert device.observed_parameters[0].definition.engineering_unit == "A"
    assert device.observed_parameters[1].definition is not None
    assert device.observed_parameters[1].definition.change_requires_stop
