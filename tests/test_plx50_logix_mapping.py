import json
from pathlib import Path

from twinforge.assembly import (
    apply_plx50_logix_mapping,
    plx50_logix_mapping_data,
    plx50_logix_mapping_json,
)
from twinforge.model import (
    CommunicationInterface,
    CommunicationRole,
    GatewayDevice,
    SourceExtension,
    SourceNode,
)
from twinforge.parsers import L5XParser
from twinforge.parsers.plx50 import (
    Plx50DeviceConfiguration,
    Plx50ProfibusDataPoint,
    Plx50ProfibusDevice,
    Plx50ProfibusSlot,
)


def _controller(tmp_path: Path):
    source = tmp_path / "mapping.L5X"
    source.write_text(
        """
<RSLogix5000Content TargetType="Routine" TargetName="GatewayMap">
  <Controller Use="Context" Name="Controller">
    <DataTypes>
      <DataType Name="DeviceInput"><Members>
        <Member Name="Input4Bytes" DataType="REAL" Dimension="0" />
      </Members></DataType>
      <DataType Name="DeviceOutput"><Members>
        <Member Name="Output2Bytes" DataType="SINT" Dimension="2" />
      </Members></DataType>
      <DataType Name="Device"><Members>
        <Member Name="Input" DataType="DeviceInput" Dimension="0" />
        <Member Name="Output" DataType="DeviceOutput" Dimension="0" />
      </Members></DataType>
    </DataTypes>
    <Tags>
      <Tag Name="Gateway_Device03" TagType="Base" DataType="Device" />
    </Tags>
    <Programs><Program Use="Context" ProgramName="MainProgram">
      <Routines><Routine Use="Target" Name="GatewayMap" Type="RLL">
        <RLLContent><Rung Number="0" Type="N"><Text>
          MOV(3,Gateway_Device03.Output.Control.StationNumber)
          CPS(Gateway:I1.Data[72],Gateway_Device03.Input,1)
          CPS(Gateway_Device03.Output,Gateway:O1.Data[20],8);
        </Text></Rung></RLLContent>
      </Routine></Routines>
    </Program></Programs>
  </Controller>
</RSLogix5000Content>
        """,
        encoding="utf-8",
    )
    plant = L5XParser().parse(source, report_mode=None)
    return next(plant.iter_controllers())


def _extension() -> SourceExtension:
    return SourceExtension(
        format="PLX50-PSJ",
        root=SourceNode(name="PSPBConfigSlotDataPoint"),
    )


def _configuration() -> Plx50DeviceConfiguration:
    input_point = Plx50ProfibusDataPoint(
        data_point_type="Input",
        data_format="REAL",
        byte_length=4,
        local_offset=0,
        description="Input4Bytes",
        modbus_register_type="HR",
        interface_connection_offset=301,
        attributes=(),
        source_extension=_extension(),
    )
    output_point = Plx50ProfibusDataPoint(
        data_point_type="Output",
        data_format="SINT",
        byte_length=2,
        local_offset=0,
        description="Output2Bytes",
        modbus_register_type="HR",
        interface_connection_offset=401,
        attributes=(),
        source_extension=_extension(),
    )
    device = Plx50ProfibusDevice(
        vendor_name="ProSoft",
        model_name="PLX51-PBM",
        instance_name="Device03",
        station_address=3,
        ident_number=4350,
        gsd_revision=5,
        gsd_filename="PSFT10FE.GSD",
        slots=(
            Plx50ProfibusSlot(
                slot_id=1,
                module_id=3,
                data_points=(input_point,),
                attributes=(),
                source_extension=_extension(),
            ),
            Plx50ProfibusSlot(
                slot_id=2,
                module_id=7,
                data_points=(output_point,),
                attributes=(),
                source_extension=_extension(),
            ),
        ),
        attributes=(),
        source_extension=_extension(),
    )
    return Plx50DeviceConfiguration(
        device_type="PSPBDevicePLX51PBM",
        device_name="Gateway",
        connection_path="192.0.2.50",
        instance_name="Gateway",
        description="Fixture",
        ip_address="192.0.2.50",
        mode="StandaloneMaster",
        primary_interface="EtherNetIP",
        device_attributes=(),
        config_attributes=(),
        profibus_devices=(device,),
        source_extension=_extension(),
    )


def _gateway() -> GatewayDevice:
    gateway = GatewayDevice(name="Gateway")
    gateway.add_communication_interface(
        CommunicationInterface(
            name="EtherNet/IP",
            protocol="EtherNet/IP",
            role=CommunicationRole.ADAPTER,
        )
    )
    gateway.add_communication_interface(
        CommunicationInterface(
            name="PROFIBUS DP",
            protocol="PROFIBUS DP",
            role=CommunicationRole.MASTER,
        )
    )
    return gateway


def test_correlates_bidirectional_points_with_generated_logix_evidence(
    tmp_path: Path,
) -> None:
    gateway = _gateway()

    result = apply_plx50_logix_mapping(
        gateway,
        _configuration(),
        _controller(tmp_path),
    )

    assert result.diagnostics == ()
    assert result.unresolved_points == ()
    assert len(result.transfers) == 2
    assert len(result.correlations) == 2
    input_point, output_point = result.correlations
    assert input_point.controller_tag_path == "Gateway_Device03.Input.Input4Bytes"
    assert input_point.assembly_reference == "Gateway:I1.Data[72]"
    assert input_point.copy_length == 1
    assert output_point.controller_tag_path == "Gateway_Device03.Output.Output2Bytes"
    assert output_point.assembly_reference == "Gateway:O1.Data[20]"
    assert output_point.copy_length == 8
    assert gateway.protocol_mappings[0].source_interface == "PROFIBUS DP"
    assert gateway.protocol_mappings[0].target_interface == "EtherNet/IP"
    assert gateway.protocol_mappings[1].source_interface == "EtherNet/IP"
    assert gateway.protocol_mappings[1].target_interface == "PROFIBUS DP"


def test_retains_point_when_generated_station_assignment_is_missing(
    tmp_path: Path,
) -> None:
    controller = _controller(tmp_path)
    routine = next(controller.iter_programs()).get_routine("GatewayMap")
    assert routine is not None
    assert routine.ladder_rungs[0].text is not None
    routine.ladder_rungs[0].text = routine.ladder_rungs[0].text.replace(
        "MOV(3,Gateway_Device03.Output.Control.StationNumber)",
        "",
    )

    result = apply_plx50_logix_mapping(
        _gateway(),
        _configuration(),
        controller,
    )

    assert result.correlations == ()
    assert len(result.unresolved_points) == 2
    assert {item.code for item in result.diagnostics} == {
        "plx50_logix_point_mapping_unresolved"
    }


def test_serializes_versioned_machine_readable_mapping(tmp_path: Path) -> None:
    result = apply_plx50_logix_mapping(
        _gateway(),
        _configuration(),
        _controller(tmp_path),
    )

    data = plx50_logix_mapping_data(result)
    serialized = plx50_logix_mapping_json(result)

    assert data["schema_version"] == "1.0"
    assert data["transfers"][0]["assembly_reference"] == "Gateway:I1.Data[72]"
    assert data["correlations"][1]["controller_tag_path"] == (
        "Gateway_Device03.Output.Output2Bytes"
    )
    assert data["unresolved_points"] == []
    assert data["diagnostics"] == []
    assert json.loads(serialized) == data
    assert serialized.endswith("\n")
