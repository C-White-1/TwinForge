from twinforge.assembly import apply_plx50_gateway_configuration
from twinforge.model import (
    CommunicationInterface,
    CommunicationRole,
    GatewayDevice,
    ModbusAccess,
    ModbusAddressingConvention,
    ModbusEndpointConfiguration,
    ModbusArea,
    SourceExtension,
    SourceNode,
)
from twinforge.parsers.plx50 import Plx50DeviceConfiguration
from twinforge.parsers.plx50 import (
    Plx50ProfibusDataPoint,
    Plx50ProfibusDevice,
    Plx50ProfibusSlot,
)


def _configuration(
    primary_interface: str,
    *,
    mode: str = "StandaloneMaster",
    extra: dict[str, str] | None = None,
    profibus_devices: tuple[Plx50ProfibusDevice, ...] = (),
) -> Plx50DeviceConfiguration:
    attributes = {
        "InstanceName": "TF_PLX51_PBM_Tes",
        "Description": "TwinForge native format fixture",
        "IPAddress": "192.0.2.10",
        "Mode": mode,
        "PrimaryInterface": primary_interface,
    }
    attributes.update(extra or {})
    return Plx50DeviceConfiguration(
        device_type="PSPBDevicePLX51PBM",
        device_name="TF_PLX51_PBM_Tes",
        connection_path="192.0.2.10",
        instance_name=attributes["InstanceName"],
        description=attributes["Description"],
        ip_address=attributes["IPAddress"],
        mode=mode,
        primary_interface=primary_interface,
        device_attributes=(("DeviceName", "TF_PLX51_PBM_Tes"),),
        config_attributes=tuple(attributes.items()),
        profibus_devices=profibus_devices,
        source_extension=SourceExtension(
            format="PLX50-PSJ",
            root=SourceNode(name="GenericDevice"),
        ),
    )


def _gateway() -> GatewayDevice:
    gateway = GatewayDevice(name="PLX51-PBM")
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
            role=CommunicationRole.SLAVE,
        )
    )
    return gateway


def test_applies_modbus_tcp_slave_and_configured_profibus_master_role():
    gateway = _gateway()

    result = apply_plx50_gateway_configuration(
        gateway,
        _configuration(
            "ModbusTCPSlave",
            extra={
                "ModbusLocalNodeNumber": "7",
                "ModbusTCPPort": "1502",
                "ModbusAddressOffset": "PLC",
                "ModbusMasterControlEnable": "true",
                "ModbusMasterControlHROffset": "101",
                "ModbusStatusRegisterType": "HR",
                "ModbusStatusOffset": "201",
            },
        ),
    )

    assert result.primary_interface is not None
    assert result.primary_interface.name == "Modbus TCP"
    assert result.primary_interface.role is CommunicationRole.SERVER
    assert result.primary_interface.address == "192.0.2.10"
    assert result.primary_interface.metadata["configured_primary"] is True
    assert result.primary_interface.metadata["modbus_configuration"] == (
        ModbusEndpointConfiguration(
            unit_id=7,
            tcp_port=1502,
            addressing_convention=ModbusAddressingConvention.ONE_BASED,
        )
    )
    assert result.primary_interface.metadata["native_modbus_configuration"] == {
        "local_node_number": "7",
        "tcp_port": "1502",
        "address_offset": "PLC",
    }
    register_map = result.modbus_register_map
    assert register_map is not None
    assert register_map.interface_name == "Modbus TCP"
    assert [point.name for point in register_map.points] == [
        "PROFIBUS Master Control",
        "PROFIBUS Status Base",
    ]
    control, status = register_map.points
    assert control.address.area is ModbusArea.HOLDING_REGISTERS
    assert control.address.source_reference == "101"
    assert control.address.offset == 100
    assert control.address.quantity == 1
    assert status.address.area is ModbusArea.HOLDING_REGISTERS
    assert status.address.source_reference == "201"
    assert status.address.offset == 200
    assert status.address.quantity is None
    assert status.metadata["extent_status"] == "not_derived"
    profibus = gateway.communication_interfaces[1]
    assert profibus.role is CommunicationRole.MASTER
    assert profibus.metadata["description_role"] == "slave"
    assert profibus.metadata["configured_mode"] == "StandaloneMaster"
    assert gateway.protocol_mappings == []
    assert result.diagnostics == ()


def test_reuses_eds_ethernet_endpoint_for_ethernet_ip_primary():
    gateway = _gateway()

    result = apply_plx50_gateway_configuration(
        gateway,
        _configuration("EtherNetIP"),
    )

    endpoint = result.primary_interface
    assert endpoint is not None
    assert endpoint is gateway.communication_interfaces[0]
    assert len(gateway.communication_interfaces) == 2
    assert endpoint.metadata["source_format"] == "PLX50-PSJ"


def test_unknown_native_values_are_diagnosed_without_guessed_endpoints():
    gateway = _gateway()

    result = apply_plx50_gateway_configuration(
        gateway,
        _configuration("FutureInterface", mode="FutureMode"),
    )

    assert result.primary_interface is None
    assert len(gateway.communication_interfaces) == 2
    assert [item.code for item in result.diagnostics] == [
        "plx50_mode_unresolved",
        "plx50_primary_interface_unresolved",
    ]


def test_lowers_bidirectional_profibus_modbus_mappings():
    extension = SourceExtension(
        format="PLX50-PSJ",
        root=SourceNode(name="PSPBConfigSlotDataPoint"),
    )
    data_point = Plx50ProfibusDataPoint(
        data_point_type="Input",
        data_format="REAL",
        byte_length=4,
        local_offset=0,
        description="Input4Bytes",
        modbus_register_type="HR",
        interface_connection_offset=301,
        attributes=(),
        source_extension=extension,
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
        source_extension=extension,
    )
    slot = Plx50ProfibusSlot(
        slot_id=1,
        module_id=3,
        data_points=(data_point,),
        attributes=(),
        source_extension=extension,
    )
    output_slot = Plx50ProfibusSlot(
        slot_id=2,
        module_id=7,
        data_points=(output_point,),
        attributes=(),
        source_extension=extension,
    )
    device = Plx50ProfibusDevice(
        vendor_name="ProSoft",
        model_name="PLX51-PBM",
        instance_name="TF_DP_SLAVE_01",
        station_address=3,
        ident_number=0x10FE,
        gsd_revision=5,
        gsd_filename="PSFT10FE.GSD",
        slots=(slot, output_slot),
        attributes=(),
        source_extension=extension,
    )
    gateway = _gateway()

    result = apply_plx50_gateway_configuration(
        gateway,
        _configuration(
            "ModbusTCPSlave",
            extra={
                "ModbusLocalNodeNumber": "7",
                "ModbusTCPPort": "1502",
                "ModbusAddressOffset": "PLC",
                "ModbusMasterControlEnable": "false",
                "ModbusStatusRegisterType": "HR",
                "ModbusStatusOffset": "201",
            },
            profibus_devices=(device,),
        ),
    )

    register_map = result.modbus_register_map
    assert register_map is not None
    mapped = register_map.points[-2]
    assert mapped.name == "Input4Bytes"
    assert mapped.address.source_reference == "301"
    assert mapped.address.offset == 300
    assert mapped.address.quantity == 2
    assert mapped.data_type == "REAL"
    output = register_map.points[-1]
    assert output.name == "Output2Bytes"
    assert output.address.source_reference == "401"
    assert output.address.offset == 400
    assert output.address.quantity == 1
    assert output.access is ModbusAccess.READ_WRITE
    assert output.data_type == "SINT"
    assert len(gateway.protocol_mappings) == 2
    mapping = gateway.protocol_mappings[0]
    assert mapping.source_interface == "PROFIBUS DP"
    assert mapping.target_interface == "Modbus TCP"
    assert mapping.source_reference == "station 3/slot 1/Input offset 0"
    assert mapping.target_reference == "holding_registers 301 quantity 2"
    assert mapping.source_extensions == (extension,)
    output_mapping = gateway.protocol_mappings[1]
    assert output_mapping.source_interface == "Modbus TCP"
    assert output_mapping.target_interface == "PROFIBUS DP"
    assert output_mapping.source_reference == "holding_registers 401 quantity 1"
    assert output_mapping.target_reference == "station 3/slot 2/Output offset 0"
    assert gateway.metadata["protocol_mapping_status"] == "partially_evidenced"
