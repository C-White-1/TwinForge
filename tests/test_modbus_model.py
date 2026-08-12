import pytest

from twinforge.model import (
    ModbusAccess,
    ModbusAddress,
    ModbusAddressingConvention,
    ModbusArea,
    ModbusEndpointConfiguration,
    ModbusPoint,
    ModbusRegisterMap,
)


def test_register_map_preserves_source_notation_and_normalized_offset():
    register_map = ModbusRegisterMap(
        name="Gateway registers",
        interface_name="Modbus TCP",
    )
    point = ModbusPoint(
        name="Pressure",
        address=ModbusAddress(
            area=ModbusArea.HOLDING_REGISTERS,
            source_reference="40001",
            offset=0,
            convention=ModbusAddressingConvention.ONE_BASED,
            unit_id=7,
            quantity=2,
        ),
        access=ModbusAccess.READ_ONLY,
        data_type="REAL32",
        engineering_unit="bar",
    )

    register_map.add_point(point)

    assert point.parent is register_map
    assert point.address.source_reference == "40001"
    assert point.address.offset == 0
    assert point.address.quantity == 2
    assert register_map.overlaps() == ()


def test_endpoint_configuration_validates_unit_and_tcp_port():
    configuration = ModbusEndpointConfiguration(
        unit_id=7,
        tcp_port=1502,
        addressing_convention=ModbusAddressingConvention.ONE_BASED,
    )

    assert configuration.unit_id == 7
    assert configuration.tcp_port == 1502

    with pytest.raises(ValueError, match="TCP port"):
        ModbusEndpointConfiguration(tcp_port=65536)


def test_unknown_address_convention_retains_reference_without_offset():
    address = ModbusAddress(
        area=ModbusArea.HOLDING_REGISTERS,
        source_reference="HR-17",
    )

    assert address.offset is None
    assert address.convention is ModbusAddressingConvention.UNKNOWN

    region = ModbusAddress(
        area=ModbusArea.COILS,
        source_reference="status base",
        offset=0,
        convention=ModbusAddressingConvention.ZERO_BASED,
        quantity=None,
    )
    assert region.quantity is None

    with pytest.raises(ValueError, match="explicit addressing convention"):
        ModbusAddress(
            area=ModbusArea.HOLDING_REGISTERS,
            source_reference="ambiguous 17",
            offset=17,
        )


def test_overlaps_are_reported_but_not_discarded():
    register_map = ModbusRegisterMap(
        name="Aliases",
        interface_name="Modbus RTU",
    )
    first = ModbusPoint(
        name="Float value",
        address=ModbusAddress(
            area=ModbusArea.INPUT_REGISTERS,
            source_reference="30001",
            offset=0,
            convention=ModbusAddressingConvention.ONE_BASED,
            unit_id=1,
            quantity=2,
        ),
    )
    alias = ModbusPoint(
        name="Low word alias",
        address=ModbusAddress(
            area=ModbusArea.INPUT_REGISTERS,
            source_reference="30002",
            offset=1,
            convention=ModbusAddressingConvention.ONE_BASED,
            unit_id=1,
        ),
    )
    other_unit = ModbusPoint(
        name="Other slave",
        address=ModbusAddress(
            area=ModbusArea.INPUT_REGISTERS,
            source_reference="30002",
            offset=1,
            convention=ModbusAddressingConvention.ONE_BASED,
            unit_id=2,
        ),
    )
    for point in (first, alias, other_unit):
        register_map.add_point(point)

    assert register_map.points == [first, alias, other_unit]
    assert register_map.overlaps() == ((first, alias),)


@pytest.mark.parametrize(
    ("unit_id", "quantity", "message"),
    [(-1, 1, "unit ID"), (256, 1, "unit ID"), (1, 0, "quantity")],
)
def test_invalid_address_ranges_are_rejected(
    unit_id: int,
    quantity: int,
    message: str,
):
    with pytest.raises(ValueError, match=message):
        ModbusAddress(
            area=ModbusArea.COILS,
            source_reference="coil",
            convention=ModbusAddressingConvention.ZERO_BASED,
            unit_id=unit_id,
            quantity=quantity,
        )
