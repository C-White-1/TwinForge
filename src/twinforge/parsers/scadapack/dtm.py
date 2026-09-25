"""Map a captured `.prj` `FdtDtmProject` tree into `DeviceTypeManager` objects.

Milestone 2 of docs/roadmaps/scadapack-rcz-capture-roadmap.md. `.prj`'s
`<DTM Id="...">` elements each hold a `CustomAttributes` block (plain,
directly readable XML with a `DTMDisplayName` custom item) and an
`InstanceData` block whose `InstanceDataRecord` children are individually
keyed (`Key="AddressInfo-<protocol-guid>"`, `Key="ActiveProtocol-<protocol-
guid>"`, ...). Each record's own text is a base64-encoded .NET
`BinaryFormatter` blob; `System.UnitySerializationHolder` embeds the real
object as a self-contained DataContract XML fragment inside it (no real
BinaryFormatter deserializer needed -- see
docs/architecture/scadapack-rcz-format.md), extracted with the same
generic regex this project's investigation already proved reliable.

Only the record kinds confirmed by direct byte-level inspection are
mapped: the DTM's own protocol catalog (`EngineeringData`'s `DeviceTypeInfo`
fragment), per-protocol addressing (`AddressInfo-<guid>`), and which
protocol is active (`ActiveProtocol-<guid>`, present only for the selected
one). Every other `InstanceDataRecord` key observed in the real corpus
(`Dnp3LayerSettingsControlGroup`, `Modbus Settings`,
`SerialPortModemSettingsPageControlGroup`, ...) is real, readable-looking
data too, but its content has not been decoded -- not attempted here.
"""
from __future__ import annotations

import base64
import binascii
import re
import xml.etree.ElementTree as ET

from twinforge.model import ConfiguredProtocolAddress, DeviceTypeManager, ProtocolVariant

from .capture import CapturedSection, Diagnostic, SourceLocation
from .evidence import source_extension as _extension

_FRAGMENT_PATTERN = re.compile(rb"<([A-Za-z][\w.]*)(?: [^>]*)?>.*?</\1>", re.DOTALL)
_CUSTOM_NAME_ESCAPE = re.compile(r"_x([0-9A-Fa-f]{4})_")
_ADDRESS_INFO_KEY = "AddressInfo-"
_ACTIVE_PROTOCOL_KEY = "ActiveProtocol-"


def _local_tag(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _decode_custom_name_escapes(text: str) -> str:
    """Reverse .NET `XmlConvert.EncodeName`'s `_xHHHH_` escaping, e.g. the

    literal `_x0020_` this project's real `DTMDisplayName` values use for
    a plain space.
    """
    return _CUSTOM_NAME_ESCAPE.sub(lambda m: chr(int(m.group(1), 16)), text)


def _fragments(base64_text: str | None) -> list[bytes] | None:
    """Return every complete DataContract XML fragment found inside one

    base64-decoded `.NET BinaryFormatter` blob, or None if the text isn't
    valid base64 at all (retained as evidence upstream, not guessed at).
    """
    if not base64_text:
        return []
    try:
        raw = base64.b64decode(base64_text, validate=False)
    except binascii.Error:
        return None
    return [match.group(0) for match in _FRAGMENT_PATTERN.finditer(raw)]


def _dtm_display_name(dtm: CapturedSection) -> str | None:
    custom_attributes = next((c for c in dtm.ordered_children if c.tag == "CustomAttributes"), None)
    if custom_attributes is None or not custom_attributes.text:
        return None
    try:
        root = ET.fromstring(custom_attributes.text)
    except ET.ParseError:
        return None
    for item in root.findall("CustomItem"):
        if item.get("name") == "DTMDisplayName":
            value = item.get("value")
            return _decode_custom_name_escapes(value) if value is not None else None
    return None


def _device_type_info(fragment: bytes) -> tuple[str | None, str | None, list[ProtocolVariant]]:
    root = ET.fromstring(fragment)
    if _local_tag(root.tag) != "DeviceTypeInfo":
        return None, None, []
    product_name = None
    manufacturer = None
    variants: list[ProtocolVariant] = []
    for child in root:
        tag = _local_tag(child.tag)
        if tag == "ProductName":
            product_name = child.text
        elif tag == "ProductManufacturerName":
            manufacturer = child.text
        elif tag == "BusCategories":
            for category in child:
                protocol_id = None
                protocol_name = None
                communication_type = None
                for field_element in category:
                    field_tag = _local_tag(field_element.tag)
                    if field_tag == "ProtocolId":
                        protocol_id = field_element.text
                    elif field_tag == "ProtocolName":
                        protocol_name = field_element.text
                    elif field_tag == "CommunicationType":
                        communication_type = field_element.text
                if protocol_id and protocol_name and communication_type == "Supported":
                    variants.append(ProtocolVariant(protocol_id=protocol_id, protocol_name=protocol_name))
    return product_name, manufacturer, variants


def _bus_category(fragment: bytes) -> tuple[str, str] | None:
    root = ET.fromstring(fragment)
    if _local_tag(root.tag) != "BusCategory":
        return None
    protocol_id = None
    protocol_name = None
    for child in root:
        tag = _local_tag(child.tag)
        if tag == "ProtocolId":
            protocol_id = child.text
        elif tag == "ProtocolName":
            protocol_name = child.text
    if protocol_id is None:
        return None
    return protocol_id, protocol_name or ""


_ADDRESS_FIELDS = ("AddressingModeSelection", "TargetAddress", "IPAddressOrHostName",
                   "Port", "DeviceSerialNumber", "LocalConnection")


def _address_info(fragment: bytes) -> tuple[str, dict[str, str]] | None:
    root = ET.fromstring(fragment)
    if _local_tag(root.tag) != "AddressInfo":
        return None
    protocol_id = None
    fields: dict[str, str] = {}
    for child in root.iter():
        tag = _local_tag(child.tag)
        if tag == "ProtocolId" and child is not root:
            protocol_id = child.text
        elif tag in _ADDRESS_FIELDS and child.text is not None:
            fields[tag] = child.text
    if protocol_id is None:
        return None
    return protocol_id, fields


def _configured_address(protocol_id: str, fields: dict[str, str], *, active: bool,
                        protocol_name: str | None) -> ConfiguredProtocolAddress:
    port = fields.get("Port")
    return ConfiguredProtocolAddress(
        protocol_id=protocol_id, protocol_name=protocol_name, active=active,
        addressing_mode=fields.get("AddressingModeSelection"),
        target_address=fields.get("TargetAddress"),
        ip_address=fields.get("IPAddressOrHostName"),
        port=int(port) if port is not None and port.isdigit() else None,
        device_serial_number=fields.get("DeviceSerialNumber") or None,
        local_connection=(fields.get("LocalConnection") == "true"
                          if "LocalConnection" in fields else None),
    )


def parse_dtms(
    section: CapturedSection, source: SourceLocation,
) -> tuple[list[DeviceTypeManager], list[Diagnostic]]:
    """Map every `<DTM>` under a captured `FdtDtmProject` tree.

    Two passes: a protocol's catalog entry (name, GUID) and its configured
    address can live on *different* DTMs -- real evidence, not a
    hypothetical: `leadLagPumpCtrl_v02.RCZ`'s comm DTM declares the DNP3
    protocol catalog, while its device DTM holds the actual configured
    addresses, cross-referenced only by the shared, project-wide protocol
    GUID. A single pass over one DTM at a time cannot resolve an inactive
    variant's own name (no `ActiveProtocol` record exists for it to name
    it), so names are collected from every DTM's catalog first.
    """
    diagnostics: list[Diagnostic] = []
    managers: list[DeviceTypeManager] = []
    raw_addresses: list[tuple[DeviceTypeManager, dict[str, dict[str, str]], dict[str, str]]] = []
    dtms_element = next((c for c in section.ordered_children if c.tag == "DTMs"), None)
    if dtms_element is None:
        return managers, diagnostics
    for dtm in dtms_element.ordered_children:
        if dtm.tag != "DTM":
            continue
        dtm_id = dtm.raw_attributes.get("Id", "")
        manager = DeviceTypeManager(id=dtm_id, name=_dtm_display_name(dtm) or dtm_id,
                                    source_extensions=[_extension(dtm, source)])
        engineering_data = next((c for c in dtm.ordered_children if c.tag == "EngineeringData"), None)
        engineering_fragments = _fragments(engineering_data.text if engineering_data else None)
        if engineering_fragments is None:
            diagnostics.append(Diagnostic("unresolved_dtm_blob",
                                          f"DTM {dtm_id}: EngineeringData is not valid base64", source))
        else:
            for fragment in engineering_fragments:
                try:
                    product_name, manufacturer, variants = _device_type_info(fragment)
                except ET.ParseError:
                    continue
                if variants or product_name or manufacturer:
                    manager.product_name = product_name
                    manager.product_manufacturer = manufacturer
                    manager.supported_protocols = variants
        instance_data = next((c for c in dtm.ordered_children if c.tag == "InstanceData"), None)
        addresses: dict[str, dict[str, str]] = {}
        active_names: dict[str, str] = {}
        for record in (instance_data.ordered_children if instance_data else []):
            if record.tag != "InstanceDataRecord":
                continue
            key = record.raw_attributes.get("Key", "")
            if key.startswith(_ADDRESS_INFO_KEY):
                fragments = _fragments(record.text)
                if fragments is None:
                    diagnostics.append(Diagnostic(
                        "unresolved_dtm_blob", f"DTM {dtm_id}: {key} is not valid base64", source))
                    continue
                for fragment in fragments:
                    try:
                        parsed = _address_info(fragment)
                    except ET.ParseError:
                        parsed = None
                    if parsed is not None:
                        addresses[parsed[0]] = parsed[1]
            elif key.startswith(_ACTIVE_PROTOCOL_KEY):
                fragments = _fragments(record.text)
                if fragments is None:
                    diagnostics.append(Diagnostic(
                        "unresolved_dtm_blob", f"DTM {dtm_id}: {key} is not valid base64", source))
                    continue
                for fragment in fragments:
                    try:
                        parsed = _bus_category(fragment)
                    except ET.ParseError:
                        parsed = None
                    if parsed is not None:
                        active_names[parsed[0]] = parsed[1]
        managers.append(manager)
        raw_addresses.append((manager, addresses, active_names))
    protocol_names: dict[str, str] = {}
    for manager, _addresses, active_names in raw_addresses:
        for variant in manager.supported_protocols:
            protocol_names.setdefault(variant.protocol_id, variant.protocol_name)
        for protocol_id, name in active_names.items():
            if name:
                protocol_names.setdefault(protocol_id, name)
    for manager, addresses, active_names in raw_addresses:
        for protocol_id, fields in addresses.items():
            active = protocol_id in active_names
            name = active_names.get(protocol_id) or protocol_names.get(protocol_id)
            manager.configured_protocols.append(
                _configured_address(protocol_id, fields, active=active, protocol_name=name))
    return managers, diagnostics
