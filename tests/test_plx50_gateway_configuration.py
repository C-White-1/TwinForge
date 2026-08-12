from twinforge.assembly import apply_plx50_gateway_configuration
from twinforge.model import (
    CommunicationInterface,
    CommunicationRole,
    GatewayDevice,
    ModbusAddressingConvention,
    ModbusEndpointConfiguration,
    ModbusArea,
    SourceExtension,
    SourceNode,
)
from twinforge.parsers.plx50 import Plx50DeviceConfiguration


def _configuration(
    primary_interface: str,
    *,
    mode: str = "StandaloneMaster",
    extra: dict[str, str] | None = None,
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
        profibus_devices=(),
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
