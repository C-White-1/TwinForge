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
    source_extension: SourceExtension = field(repr=False)

    def config_value(self, name: str) -> str | None:
        """Return one native configuration attribute without hiding the rest."""

        return dict(self.config_attributes).get(name)


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
            _device(element)
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


def _device(element: ET.Element) -> Plx50DeviceConfiguration:
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
        source_extension=SourceExtension(
            format="PLX50-PSJ",
            root=_source_node(element),
        ),
    )


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
