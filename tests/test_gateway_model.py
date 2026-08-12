import pytest

from twinforge.model import (
    CommunicationInterface,
    CommunicationRole,
    DeviceType,
    GatewayDevice,
    GatewayProtocolMapping,
    GatewayTagBinding,
    GatewayTagBindingRole,
    Tag,
)


def _gateway() -> GatewayDevice:
    gateway = GatewayDevice(
        name="Multi-protocol gateway",
        manufacturer="Example Vendor",
        model="Gateway",
    )
    gateway.add_communication_interface(
        CommunicationInterface(
            name="controller-network",
            protocol="EtherNet/IP",
            role=CommunicationRole.ADAPTER,
        )
    )
    gateway.add_communication_interface(
        CommunicationInterface(
            name="fieldbus",
            protocol="PROFIBUS DP",
            role=CommunicationRole.SLAVE,
        )
    )
    gateway.add_communication_interface(
        CommunicationInterface(
            name="register-network",
            protocol="Modbus TCP",
            role=CommunicationRole.SERVER,
        )
    )
    return gateway


def test_gateway_endpoints_do_not_imply_protocol_mappings():
    gateway = _gateway()

    assert gateway.device_type is DeviceType.COMMUNICATION_DEVICE
    assert [item.protocol for item in gateway.communication_interfaces] == [
        "EtherNet/IP",
        "PROFIBUS DP",
        "Modbus TCP",
    ]
    assert gateway.protocol_mappings == []
    assert all(item.parent is gateway for item in gateway.communication_interfaces)


def test_gateway_accepts_only_explicit_mappings_between_known_endpoints():
    gateway = _gateway()
    mapping = GatewayProtocolMapping(
        source_interface="fieldbus",
        target_interface="controller-network",
        source_reference="station 3/input byte 0",
        target_reference="input assembly/offset 12",
        evidence="configuration export row 17",
    )

    gateway.add_protocol_mapping(mapping)

    assert gateway.protocol_mappings == [mapping]

    with pytest.raises(ValueError, match="unknown interfaces"):
        gateway.add_protocol_mapping(
            GatewayProtocolMapping(
                source_interface="unknown",
                target_interface="fieldbus",
                evidence="fixture",
            )
        )


def test_gateway_rejects_duplicate_endpoint_names():
    gateway = _gateway()

    with pytest.raises(ValueError, match="duplicate gateway interface"):
        gateway.add_communication_interface(
            CommunicationInterface(
                name="fieldbus",
                protocol="Another protocol",
            )
        )


def test_gateway_accepts_only_evidenced_tag_bindings_for_known_endpoints():
    gateway = _gateway()
    tag = Tag(name="GatewayInput", data_type="GatewayInputData")
    binding = GatewayTagBinding(
        interface_name="controller-network",
        endpoint_reference="Gateway:I1.Data[0]",
        tag=tag,
        tag_path="GatewayInput.Channel0",
        role=GatewayTagBindingRole.TARGET,
        evidence="generated CPS instruction",
    )

    gateway.add_tag_binding(binding)

    assert gateway.tag_bindings == [binding]

    with pytest.raises(ValueError, match="duplicate gateway tag binding"):
        gateway.add_tag_binding(binding)
    with pytest.raises(ValueError, match="unknown interface"):
        gateway.add_tag_binding(
            GatewayTagBinding(
                interface_name="unknown",
                endpoint_reference="Gateway:I1.Data[0]",
                tag=tag,
                tag_path="GatewayInput.Channel0",
                role=GatewayTagBindingRole.TARGET,
                evidence="fixture",
            )
        )


def test_gateway_tag_binding_path_must_reference_the_bound_tag():
    gateway = _gateway()

    with pytest.raises(ValueError, match="does not reference tag"):
        gateway.add_tag_binding(
            GatewayTagBinding(
                interface_name="controller-network",
                endpoint_reference="Gateway:I1.Data[0]",
                tag=Tag(name="GatewayInput"),
                tag_path="DifferentTag.Channel0",
                role=GatewayTagBindingRole.TARGET,
                evidence="fixture",
            )
        )
