"""Application of native PLX50 project configuration to neutral gateways."""

from __future__ import annotations

from dataclasses import dataclass

from twinforge.converters import ConversionDiagnostic, DiagnosticSeverity
from twinforge.model import (
    CommunicationInterface,
    CommunicationRole,
    GatewayDevice,
    GatewayProtocolMapping,
    ModbusAddressingConvention,
    ModbusAccess,
    ModbusAddress,
    ModbusArea,
    ModbusEndpointConfiguration,
    ModbusPoint,
    ModbusRegisterMap,
)
from twinforge.parsers.plx50 import Plx50DeviceConfiguration


@dataclass(frozen=True)
class Plx50GatewayConfigurationResult:
    """The configured endpoint and any unresolved native values."""

    primary_interface: CommunicationInterface | None
    modbus_register_map: ModbusRegisterMap | None = None
    diagnostics: tuple[ConversionDiagnostic, ...] = ()


def apply_plx50_gateway_configuration(
    gateway: GatewayDevice,
    configuration: Plx50DeviceConfiguration,
) -> Plx50GatewayConfigurationResult:
    """Apply evidenced endpoint selection without creating point mappings."""

    diagnostics: list[ConversionDiagnostic] = []
    gateway.metadata["plx50_configuration"] = {
        "device_type": configuration.device_type,
        "device_name": configuration.device_name,
        "instance_name": configuration.instance_name,
        "description": configuration.description,
        "mode": configuration.mode,
        "primary_interface": configuration.primary_interface,
    }
    profibus = _interface(gateway, "PROFIBUS DP")
    if profibus is not None:
        configured_role = {
            "StandaloneMaster": CommunicationRole.MASTER,
            "Slave": CommunicationRole.SLAVE,
        }.get(configuration.mode or "")
        if configured_role is not None:
            profibus.metadata["description_role"] = profibus.role.value
            profibus.role = configured_role
            profibus.metadata["configured_mode"] = configuration.mode
        elif configuration.mode not in (None, "Quiet"):
            diagnostics.append(
                _warning(
                    "plx50_mode_unresolved",
                    f"unrecognized PLX50 operating mode: {configuration.mode!r}",
                    configuration.mode,
                )
            )

    endpoint_definition = {
        "EtherNetIP": ("EtherNet/IP", "EtherNet/IP", CommunicationRole.ADAPTER),
        "ModbusTCPSlave": (
            "Modbus TCP",
            "Modbus TCP",
            CommunicationRole.SERVER,
        ),
    }.get(configuration.primary_interface or "")
    if endpoint_definition is None:
        diagnostics.append(
            _warning(
                "plx50_primary_interface_unresolved",
                (
                    "unrecognized PLX50 primary interface: "
                    f"{configuration.primary_interface!r}"
                ),
                configuration.primary_interface,
            )
        )
        return Plx50GatewayConfigurationResult(
            primary_interface=None,
            modbus_register_map=None,
            diagnostics=tuple(diagnostics),
        )

    name, protocol, role = endpoint_definition
    endpoint = _interface(gateway, name)
    if endpoint is None:
        endpoint = CommunicationInterface(
            name=name,
            protocol=protocol,
            role=role,
        )
        gateway.add_communication_interface(endpoint)
    else:
        endpoint.role = role
    endpoint.address = configuration.ip_address
    endpoint.metadata.update(
        {
            "source_format": "PLX50-PSJ",
            "configured_primary": True,
            "native_primary_interface": configuration.primary_interface,
        }
    )
    register_map: ModbusRegisterMap | None = None
    if protocol == "Modbus TCP":
        modbus_configuration = _modbus_configuration(configuration, diagnostics)
        endpoint.metadata["modbus_configuration"] = modbus_configuration
        endpoint.metadata["native_modbus_configuration"] = {
            "local_node_number": configuration.config_value(
                "ModbusLocalNodeNumber"
            ),
            "tcp_port": configuration.config_value("ModbusTCPPort"),
            "address_offset": configuration.config_value(
                "ModbusAddressOffset"
            ),
        }
        register_map = _modbus_register_map(
            configuration,
            endpoint.name,
            modbus_configuration,
            diagnostics,
        )
        _lower_profibus_modbus_mappings(
            gateway,
            configuration,
            register_map,
            modbus_configuration,
            diagnostics,
        )
    return Plx50GatewayConfigurationResult(
        primary_interface=endpoint,
        modbus_register_map=register_map,
        diagnostics=tuple(diagnostics),
    )


def _lower_profibus_modbus_mappings(
    gateway: GatewayDevice,
    configuration: Plx50DeviceConfiguration,
    register_map: ModbusRegisterMap,
    endpoint: ModbusEndpointConfiguration,
    diagnostics: list[ConversionDiagnostic],
) -> None:
    for device in configuration.profibus_devices:
        for slot in device.slots:
            for point in slot.data_points:
                entered = point.interface_connection_offset
                if entered is None or entered == 0:
                    continue
                if endpoint.addressing_convention is ModbusAddressingConvention.UNKNOWN:
                    continue
                area = {
                    "HR": ModbusArea.HOLDING_REGISTERS,
                    "IR": ModbusArea.INPUT_REGISTERS,
                    "CS": ModbusArea.COILS,
                    "IS": ModbusArea.DISCRETE_INPUTS,
                }.get(point.modbus_register_type or "")
                if area is None:
                    diagnostics.append(
                        _warning(
                            "plx50_data_point_modbus_area_unresolved",
                            "unrecognized PLX50 data-point Modbus register type",
                            point.modbus_register_type,
                        )
                    )
                    continue
                quantity = _modbus_quantity(point.byte_length, area, diagnostics)
                if quantity is None:
                    continue
                offset = (
                    entered - 1
                    if endpoint.addressing_convention
                    is ModbusAddressingConvention.ONE_BASED
                    else entered
                )
                if offset < 0:
                    continue
                point_name = point.description or (
                    f"station {device.station_address} slot {slot.slot_id}"
                )
                modbus_point = ModbusPoint(
                    name=point_name,
                    address=ModbusAddress(
                        area=area,
                        source_reference=str(entered),
                        offset=offset,
                        convention=endpoint.addressing_convention,
                        unit_id=endpoint.unit_id,
                        quantity=quantity,
                    ),
                    access=(
                        ModbusAccess.READ_ONLY
                        if point.data_point_type == "Input"
                        else ModbusAccess.READ_WRITE
                    ),
                    data_type=point.data_format,
                    metadata={
                        "source_format": "PLX50-PSJ",
                        "profibus_station": device.station_address,
                        "profibus_slot": slot.slot_id,
                        "profibus_local_offset": point.local_offset,
                        "byte_length": point.byte_length,
                    },
                    source_extensions=[point.source_extension],
                )
                register_map.add_point(modbus_point)
                profibus_reference = (
                    f"station {device.station_address}/slot {slot.slot_id}/"
                    f"{point.data_point_type or 'data'} offset "
                    f"{point.local_offset}"
                )
                modbus_reference = (
                    f"{area.value} {entered} quantity {quantity}"
                )
                if point.data_point_type == "Input":
                    source_interface = "PROFIBUS DP"
                    source_reference = profibus_reference
                    target_interface = "Modbus TCP"
                    target_reference = modbus_reference
                else:
                    source_interface = "Modbus TCP"
                    source_reference = modbus_reference
                    target_interface = "PROFIBUS DP"
                    target_reference = profibus_reference
                gateway.add_protocol_mapping(
                    GatewayProtocolMapping(
                        source_interface=source_interface,
                        source_reference=source_reference,
                        target_interface=target_interface,
                        target_reference=target_reference,
                        evidence=(
                            "PLX50 PSJ configured PROFIBUS data-point "
                            "InterfaceConnectionOffset"
                        ),
                        metadata={
                            "profibus_device": device.instance_name,
                            "profibus_station": device.station_address,
                            "profibus_slot": slot.slot_id,
                            "data_point": point_name,
                            "native_interface_connection_offset": entered,
                        },
                        source_extensions=(point.source_extension,),
                    )
                )
    if gateway.protocol_mappings:
        gateway.metadata["protocol_mapping_status"] = "partially_evidenced"


def _modbus_quantity(
    byte_length: int | None,
    area: ModbusArea,
    diagnostics: list[ConversionDiagnostic],
) -> int | None:
    if byte_length is None or byte_length < 1:
        return None
    if area in (ModbusArea.COILS, ModbusArea.DISCRETE_INPUTS):
        return byte_length * 8
    if byte_length % 2:
        diagnostics.append(
            _warning(
                "plx50_data_point_register_alignment_invalid",
                "PLX50 register data-point byte length must be even",
                str(byte_length),
            )
        )
        return None
    return byte_length // 2


def _modbus_register_map(
    configuration: Plx50DeviceConfiguration,
    interface_name: str,
    endpoint: ModbusEndpointConfiguration,
    diagnostics: list[ConversionDiagnostic],
) -> ModbusRegisterMap:
    register_map = ModbusRegisterMap(
        name="PLX50 built-in Modbus registers",
        interface_name=interface_name,
    )
    if configuration.config_value("ModbusMasterControlEnable") == "true":
        point = _configured_modbus_point(
            configuration,
            native_field="ModbusMasterControlHROffset",
            name="PROFIBUS Master Control",
            area=ModbusArea.HOLDING_REGISTERS,
            convention=endpoint.addressing_convention,
            unit_id=endpoint.unit_id,
            quantity=1,
            access=ModbusAccess.UNKNOWN,
            diagnostics=diagnostics,
        )
        if point is not None:
            register_map.add_point(point)
    status_area = {
        "CS": ModbusArea.COILS,
        "HR": ModbusArea.HOLDING_REGISTERS,
    }.get(configuration.config_value("ModbusStatusRegisterType") or "")
    if status_area is None:
        diagnostics.append(
            _warning(
                "plx50_modbus_status_area_unresolved",
                "unrecognized PLX50 Modbus status register type",
                configuration.config_value("ModbusStatusRegisterType"),
            )
        )
    else:
        point = _configured_modbus_point(
            configuration,
            native_field="ModbusStatusOffset",
            name="PROFIBUS Status Base",
            area=status_area,
            convention=endpoint.addressing_convention,
            unit_id=endpoint.unit_id,
            quantity=None,
            access=ModbusAccess.READ_ONLY,
            diagnostics=diagnostics,
        )
        if point is not None:
            register_map.add_point(point)
    return register_map


def _configured_modbus_point(
    configuration: Plx50DeviceConfiguration,
    *,
    native_field: str,
    name: str,
    area: ModbusArea,
    convention: ModbusAddressingConvention,
    unit_id: int | None,
    quantity: int | None,
    access: ModbusAccess,
    diagnostics: list[ConversionDiagnostic],
) -> ModbusPoint | None:
    source_reference = configuration.config_value(native_field)
    if source_reference is None:
        return None
    entered = _native_integer(configuration, native_field, diagnostics)
    if entered is None or convention is ModbusAddressingConvention.UNKNOWN:
        return None
    offset = (
        entered - 1
        if convention is ModbusAddressingConvention.ONE_BASED
        else entered
    )
    if offset < 0:
        diagnostics.append(
            _warning(
                "plx50_modbus_address_out_of_range",
                f"PLX50 {native_field} does not resolve to a valid offset",
                source_reference,
            )
        )
        return None
    return ModbusPoint(
        name=name,
        address=ModbusAddress(
            area=area,
            source_reference=source_reference,
            offset=offset,
            convention=convention,
            unit_id=unit_id,
            quantity=quantity,
        ),
        access=access,
        metadata={
            "source_format": "PLX50-PSJ",
            "native_field": native_field,
            "extent_status": (
                "documented" if quantity is not None else "not_derived"
            ),
        },
    )


def _modbus_configuration(
    configuration: Plx50DeviceConfiguration,
    diagnostics: list[ConversionDiagnostic],
) -> ModbusEndpointConfiguration:
    unit_id = _native_integer(
        configuration,
        "ModbusLocalNodeNumber",
        diagnostics,
    )
    tcp_port = _native_integer(configuration, "ModbusTCPPort", diagnostics)
    native_convention = configuration.config_value("ModbusAddressOffset")
    convention = {
        "Normal": ModbusAddressingConvention.ZERO_BASED,
        "PLC": ModbusAddressingConvention.ONE_BASED,
    }.get(native_convention or "", ModbusAddressingConvention.UNKNOWN)
    if native_convention not in (None, "Normal", "PLC"):
        diagnostics.append(
            _warning(
                "plx50_modbus_addressing_unresolved",
                f"unrecognized PLX50 Modbus addressing: {native_convention!r}",
                native_convention,
            )
        )
    try:
        return ModbusEndpointConfiguration(
            unit_id=unit_id,
            tcp_port=tcp_port,
            addressing_convention=convention,
        )
    except ValueError as error:
        diagnostics.append(
            _warning(
                "plx50_modbus_endpoint_value_out_of_range",
                str(error),
                None,
            )
        )
        return ModbusEndpointConfiguration(addressing_convention=convention)


def _native_integer(
    configuration: Plx50DeviceConfiguration,
    name: str,
    diagnostics: list[ConversionDiagnostic],
) -> int | None:
    value = configuration.config_value(name)
    if value is None:
        return None
    try:
        return int(value, 10)
    except ValueError:
        diagnostics.append(
            _warning(
                "invalid_plx50_configuration_integer",
                f"PLX50 {name} must be an integer, got {value!r}",
                value,
            )
        )
        return None


def _interface(
    gateway: GatewayDevice,
    name: str,
) -> CommunicationInterface | None:
    return next(
        (item for item in gateway.communication_interfaces if item.name == name),
        None,
    )


def _warning(
    code: str,
    message: str,
    raw_value: str | None,
) -> ConversionDiagnostic:
    return ConversionDiagnostic(
        severity=DiagnosticSeverity.WARNING,
        code=code,
        message=message,
        object_name="PLX50 gateway",
        raw_value=raw_value,
    )
