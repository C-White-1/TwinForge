import pytest

from twinforge.model import (
    CommunicationInterface,
    CommunicationRole,
    DeviceType,
    GatewayDevice,
    GatewayProtocolMapping,
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
