from twinforge.converters import assemble_device_from_module
from twinforge.model import (
    CommunicationInterface,
    CommunicationService,
    Connection,
    Device,
    DeviceModuleBinding,
    DeviceModuleRole,
    DeviceType,
    Identity,
    Module,
)


def test_device_keeps_asset_identity_separate_from_controller_module():
    module = Module(
        name="Dev_PF525",
        catalog="ETHERNET-MODULE",
        identity=Identity(product_code=18),
        address="192.168.1.80",
    )
    device = Device(
        name="PowerFlex 525",
        device_type=DeviceType.DRIVE,
        manufacturer="Rockwell Automation",
        model="PowerFlex 525",
    )

    device.bind_module(
        DeviceModuleBinding(
            module=module,
            role=DeviceModuleRole.CYCLIC_IO,
            evidence="explicit PowerFlex reference bundle",
        )
    )

    assert device.module_bindings[0].module is module
    assert device.module_bindings[0].parent is device
    assert module.parent is None
    assert device.identity is not module.identity
    assert module.controller_representation_identity is module.identity
    assert device.module_bindings[0].identity_scopes_are_distinct


def test_device_interface_owns_connections_and_services():
    device = Device(name="Drive", device_type=DeviceType.DRIVE)
    interface = CommunicationInterface(
        name="Embedded EtherNet/IP",
        protocol="EtherNet/IP",
        address="192.168.1.80",
    )
    connection = Connection(
        name="Standard",
        protocol="EtherNet/IP",
        connection_type="Output",
        metadata={
            "input_assembly": 1,
            "output_assembly": 2,
            "input_size_bytes": 8,
            "output_size_bytes": 4,
            "rpi_microseconds": 10_000,
        },
    )
    service = CommunicationService(
        name="Drive parameter access",
        service_type="explicit_message",
        object_class="0x93",
    )

    interface.add_connection(connection)
    interface.add_service(service)
    device.add_communication_interface(interface)

    assert interface.parent is device
    assert connection.parent is interface
    assert interface.services == [service]
    assert device.communication_interfaces == [interface]


def test_explicit_evidence_assembles_device_without_copying_module_identity():
    module_identity = Identity(product_code=18)
    module = Module(
        name="Dev_PF525",
        catalog="ETHERNET-MODULE",
        identity=module_identity,
        address="192.168.1.80",
    )
    module.add_connection(
        Connection(
            name="Standard",
            protocol="EtherNet/IP",
            connection_type="Output",
            requested_packet_interval_microseconds=10_000,
            input_connection_point=1,
            output_connection_point=2,
            input_size_bytes=8,
            output_size_bytes=4,
            unicast=True,
        )
    )

    device = assemble_device_from_module(
        module,
        name="PowerFlex 525",
        device_type=DeviceType.DRIVE,
        manufacturer="Rockwell Automation",
        model="PowerFlex 525",
        evidence="module, program, AOI, and manual reference bundle",
    )

    connection = device.communication_interfaces[0].connections[0]
    assert device.identity is None
    assert module.identity is module_identity
    assert device.module_bindings[0].module is module
    assert connection.input_connection_point == 1
    assert connection.output_connection_point == 2
    assert connection.input_size_bytes == 8
    assert connection.output_size_bytes == 4
    assert connection.parent is device.communication_interfaces[0]
    assert module.connections[0].parent is module
    binding = device.module_bindings[0]
    assert binding.metadata == {
        "module_identity_scope": "controller_representation",
        "device_identity_scope": "represented_device",
    }
    assert binding.identity_scopes_are_distinct


def test_device_assembly_rejects_implicit_identity():
    module = Module(
        name="Unknown",
        catalog="ETHERNET-MODULE",
        identity=Identity(),
    )

    try:
        assemble_device_from_module(
            module,
            name="PowerFlex 525",
            device_type=DeviceType.DRIVE,
            evidence="",
        )
    except ValueError as error:
        assert "evidence" in str(error)
    else:
        raise AssertionError("missing evidence should reject device assembly")
