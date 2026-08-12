"""Application of native PLX50 project configuration to neutral gateways."""

from __future__ import annotations

from dataclasses import dataclass

from twinforge.converters import ConversionDiagnostic, DiagnosticSeverity
from twinforge.model import (
    CommunicationInterface,
    CommunicationRole,
    GatewayDevice,
    ModbusAddressingConvention,
    ModbusEndpointConfiguration,
)
from twinforge.parsers.plx50 import Plx50DeviceConfiguration


@dataclass(frozen=True)
class Plx50GatewayConfigurationResult:
    """The configured endpoint and any unresolved native values."""

    primary_interface: CommunicationInterface | None
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
    return Plx50GatewayConfigurationResult(
        primary_interface=endpoint,
        diagnostics=tuple(diagnostics),
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
