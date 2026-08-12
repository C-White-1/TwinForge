"""Native ProSoft PLX50 Configuration Utility PSJ container parsing."""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass, field
from pathlib import Path
import xml.etree.ElementTree as ET

from twinforge.converters import ConversionDiagnostic, DiagnosticSeverity
from twinforge.model import SourceExtension, SourceNode

_XOR_KEY = 0x5A
_XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"


@dataclass(frozen=True)
class Plx50DeviceConfiguration:
    """One configured PLX50 device with all native XML evidence retained."""

    device_type: str | None
    device_name: str | None
    connection_path: str | None
    instance_name: str | None
    description: str | None
    ip_address: str | None
    mode: str | None
    primary_interface: str | None
    device_attributes: tuple[tuple[str, str], ...] = field(repr=False)
    config_attributes: tuple[tuple[str, str], ...] = field(repr=False)
    profibus_devices: tuple["Plx50ProfibusDevice", ...]
    source_extension: SourceExtension = field(repr=False)

    def config_value(self, name: str) -> str | None:
        """Return one native configuration attribute without hiding the rest."""

        return dict(self.config_attributes).get(name)


@dataclass(frozen=True)
class Plx50ProfibusDataPoint:
    """One native cyclic data-point declaration within a configured slot."""

    data_point_type: str | None
    data_format: str | None
    byte_length: int | None
    local_offset: int | None
    description: str | None
    modbus_register_type: str | None
    interface_connection_offset: int | None
    attributes: tuple[tuple[str, str], ...] = field(repr=False)
    source_extension: SourceExtension = field(repr=False)


@dataclass(frozen=True)
class Plx50ProfibusSlot:
    """One configured PROFIBUS slot and its ordered cyclic data points."""

    slot_id: int | None
    module_id: int | None
    data_points: tuple[Plx50ProfibusDataPoint, ...]
    attributes: tuple[tuple[str, str], ...] = field(repr=False)
    source_extension: SourceExtension = field(repr=False)


@dataclass(frozen=True)
class Plx50ProfibusDevice:
    """One downstream PROFIBUS device configured in a PLX50 project."""

    vendor_name: str | None
    model_name: str | None
    instance_name: str | None
    station_address: int | None
    ident_number: int | None
    gsd_revision: int | None
    gsd_filename: str | None
    slots: tuple[Plx50ProfibusSlot, ...]
    attributes: tuple[tuple[str, str], ...] = field(repr=False)
    source_extension: SourceExtension = field(repr=False)


@dataclass(frozen=True)
class Plx50ProjectDocument:
    """Decoded PSJ project, including its original encoded payload."""

    source_path: Path
    devices: tuple[Plx50DeviceConfiguration, ...]
    encoded_text: str = field(repr=False)
    decoded_xml: str | None = field(default=None, repr=False)
    source_extension: SourceExtension | None = field(default=None, repr=False)
    diagnostics: tuple[ConversionDiagnostic, ...] = ()


class PLX50PSJParser:
    """Decode Base64/XOR PSJ containers and parse their native XML payload."""

    def parse(self, filename: str | Path) -> Plx50ProjectDocument:
        """Parse a native PSJ file while preserving its container and XML tree."""

        path = Path(filename)
        encoded = path.read_text(encoding="ascii").strip()
        diagnostics: list[ConversionDiagnostic] = []
        try:
            payload = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as error:
            diagnostics.append(_error("invalid_plx50_psj_base64", str(error)))
            return Plx50ProjectDocument(
                source_path=path,
                devices=(),
                encoded_text=encoded,
                diagnostics=tuple(diagnostics),
            )
        decoded = bytes(value ^ _XOR_KEY for value in payload)
        try:
            xml = decoded.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            diagnostics.append(_error("invalid_plx50_psj_text", str(error)))
            return Plx50ProjectDocument(
                source_path=path,
                devices=(),
                encoded_text=encoded,
                diagnostics=tuple(diagnostics),
            )
        try:
            root = ET.fromstring(xml)
        except ET.ParseError as error:
            diagnostics.append(_error("invalid_plx50_psj_xml", str(error)))
            return Plx50ProjectDocument(
                source_path=path,
                devices=(),
                encoded_text=encoded,
                decoded_xml=xml,
                diagnostics=tuple(diagnostics),
            )
        devices = tuple(
            _device(element, diagnostics)
            for element in root.findall("./Devices/GenericDevice")
        )
        return Plx50ProjectDocument(
            source_path=path,
            devices=devices,
            encoded_text=encoded,
            decoded_xml=xml,
            source_extension=SourceExtension(
                format="PLX50-PSJ",
                root=_source_node(root),
                metadata={
                    "container_encoding": "Base64",
                    "container_obfuscation": "XOR-0x5A",
                },
            ),
            diagnostics=tuple(diagnostics),
        )


def _device(
    element: ET.Element,
    diagnostics: list[ConversionDiagnostic],
) -> Plx50DeviceConfiguration:
    config = element.find("./Config")
    config_attributes = tuple(config.attrib.items()) if config is not None else ()
    values = dict(config_attributes)
    return Plx50DeviceConfiguration(
        device_type=element.attrib.get(_XSI_TYPE),
        device_name=element.attrib.get("DeviceName"),
        connection_path=element.attrib.get("ConnectionPath"),
        instance_name=values.get("InstanceName"),
        description=values.get("Description"),
        ip_address=values.get("IPAddress"),
        mode=values.get("Mode"),
        primary_interface=values.get("PrimaryInterface"),
        device_attributes=tuple(element.attrib.items()),
        config_attributes=config_attributes,
        profibus_devices=(
            tuple(
                _profibus_device(item, diagnostics)
                for item in config.findall("./DeviceConfig/PSPBConfigDevice")
            )
            if config is not None
            else ()
        ),
        source_extension=SourceExtension(
            format="PLX50-PSJ",
            root=_source_node(element),
        ),
    )


def _profibus_device(
    element: ET.Element,
    diagnostics: list[ConversionDiagnostic],
) -> Plx50ProfibusDevice:
    values = element.attrib
    return Plx50ProfibusDevice(
        vendor_name=values.get("VendorName"),
        model_name=values.get("ModelName"),
        instance_name=values.get("InstanceName"),
        station_address=_xml_integer(values.get("StationAddress"), "StationAddress", diagnostics),
        ident_number=_xml_integer(values.get("Ident"), "Ident", diagnostics),
        gsd_revision=_xml_integer(values.get("GSDRevision"), "GSDRevision", diagnostics),
        gsd_filename=values.get("GSDFileName"),
        slots=tuple(
            _profibus_slot(item, diagnostics)
            for item in element.findall("./Slots/PSPBConfigSlot")
        ),
        attributes=tuple(values.items()),
        source_extension=SourceExtension(format="PLX50-PSJ", root=_source_node(element)),
    )


def _profibus_slot(
    element: ET.Element,
    diagnostics: list[ConversionDiagnostic],
) -> Plx50ProfibusSlot:
    values = element.attrib
    return Plx50ProfibusSlot(
        slot_id=_xml_integer(values.get("SlotID"), "SlotID", diagnostics),
        module_id=_xml_integer(values.get("ModuleID"), "ModuleID", diagnostics),
        data_points=tuple(
            _profibus_data_point(item, diagnostics)
            for item in element.findall("./DataPoints/PSPBConfigSlotDataPoint")
        ),
        attributes=tuple(values.items()),
        source_extension=SourceExtension(format="PLX50-PSJ", root=_source_node(element)),
    )


def _profibus_data_point(
    element: ET.Element,
    diagnostics: list[ConversionDiagnostic],
) -> Plx50ProfibusDataPoint:
    values = element.attrib
    return Plx50ProfibusDataPoint(
        data_point_type=values.get("DataPointType"),
        data_format=values.get("DataFormat"),
        byte_length=_xml_integer(values.get("ByteLength"), "ByteLength", diagnostics),
        local_offset=_xml_integer(values.get("LocalOffset"), "LocalOffset", diagnostics),
        description=values.get("Description"),
        modbus_register_type=values.get("ModbusRegisterType"),
        interface_connection_offset=_xml_integer(
            values.get("InterfaceConnectionOffset"), "InterfaceConnectionOffset", diagnostics
        ),
        attributes=tuple(values.items()),
        source_extension=SourceExtension(format="PLX50-PSJ", root=_source_node(element)),
    )


def _xml_integer(
    value: str | None,
    field_name: str,
    diagnostics: list[ConversionDiagnostic],
) -> int | None:
    if value is None:
        return None
    try:
        return int(value, 10)
    except ValueError:
        diagnostics.append(
            ConversionDiagnostic(
                severity=DiagnosticSeverity.WARNING,
                code="invalid_plx50_psj_integer",
                message=f"PLX50 {field_name} must be an integer, got {value!r}",
                object_name="PLX50 project",
                field=field_name,
                raw_value=value,
            )
        )
        return None


def _source_node(element: ET.Element) -> SourceNode:
    return SourceNode(
        name=element.tag,
        attributes=dict(element.attrib),
        text=element.text,
        tail=element.tail,
        children=[_source_node(child) for child in element],
    )


def _error(code: str, message: str) -> ConversionDiagnostic:
    return ConversionDiagnostic(
        severity=DiagnosticSeverity.ERROR,
        code=code,
        message=message,
        object_name="PLX50 project",
    )
