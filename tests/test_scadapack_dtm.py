"""SCADAPack `.prj` FdtDtmProject -> DeviceTypeManager mapping."""
import base64
from io import BytesIO
import zipfile

from twinforge.parsers.scadapack.capture import capture_bytes
from twinforge.parsers.scadapack.station import parse_station


def _b64(xml_fragment: str) -> str:
    return base64.b64encode(xml_fragment.encode()).decode()


def _device_type_info(product_name: str, manufacturer: str, variants: list[tuple[str, str]]) -> str:
    categories = "".join(
        "<BusCategory><CommunicationType>Supported</CommunicationType>"
        f"<ProtocolId>{pid}</ProtocolId><ProtocolName>{name}</ProtocolName></BusCategory>"
        for pid, name in variants
    )
    return _b64(
        f'<DeviceTypeInfo xmlns="x"><ProductName>{product_name}</ProductName>'
        f"<ProductManufacturerName>{manufacturer}</ProductManufacturerName>"
        f"<BusCategories>{categories}</BusCategories></DeviceTypeInfo>"
    )


def _active_protocol(protocol_id: str, protocol_name: str) -> str:
    return _b64(
        "<BusCategory><CommunicationType>Required</CommunicationType>"
        f"<ProtocolId>{protocol_id}</ProtocolId><ProtocolName>{protocol_name}</ProtocolName></BusCategory>"
    )


def _address_info(protocol_id: str, **fields: str) -> str:
    field_xml = "".join(f"<a:{name}>{value}</a:{name}>" for name, value in fields.items())
    return _b64(
        '<AddressInfo xmlns="http://schemas.datacontract.org/2004/07/Fdt.Dtm.Network">'
        '<DeviceAddresses><DeviceAddress i:type="y" xmlns:i="z"><Id>0</Id>'
        f'<ProtocolSpecificDeviceAddress xmlns:a="p">{field_xml}</ProtocolSpecificDeviceAddress>'
        f"</DeviceAddress></DeviceAddresses><ProtocolId>{protocol_id}</ProtocolId></AddressInfo>"
    )


def _dtm(dtm_id: str, display_name: str, *, engineering_data: str = "", records: tuple = ()) -> str:
    records_xml = "".join(
        f'<InstanceDataRecord Key="{key}">{value}</InstanceDataRecord>' for key, value in records
    )
    custom_items = (
        f'&lt;CustomItems&gt;&lt;CustomItem name="DTMDisplayName" '
        f'value="{display_name}" persist="True" /&gt;&lt;/CustomItems&gt;'
    )
    return (
        f'<DTM Id="{dtm_id}"><EngineeringData>{engineering_data}</EngineeringData>'
        f"<CustomAttributes>{custom_items}</CustomAttributes>"
        f'<InstanceData FormatId="x">{records_xml}</InstanceData></DTM>'
    )


def _prj(*dtms: str) -> bytes:
    return f'<?xml version="1.0"?><FdtDtmProject ProjectId="p"><DTMs>{"".join(dtms)}</DTMs></FdtDtmProject>'.encode()


def _sta(members: dict[str, bytes]) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    return buf.getvalue()


def station(members: dict[str, bytes]):
    return parse_station(capture_bytes(_sta(members), name="demo.STA"))


def test_active_protocol_resolves_with_full_address_and_catalog_name():
    prj = _prj(_dtm(
        "comm-dtm", "PC Communication Settings -DNP3 CommDTM",
        engineering_data=_device_type_info("Comm Product", "Schneider Electric", [
            ("guid-tcp", "DNP3 TCP"), ("guid-usb", "DNP3 USB"),
        ]),
    ), _dtm(
        "device-dtm", "SCADAPack x70 Controller Settings -DeviceDTM",
        records=(
            ("AddressInfo-guid-tcp", _address_info("guid-tcp", AddressingModeSelection="Dnp3Ip",
                                                    TargetAddress="1", IPAddressOrHostName="172.16.1.200",
                                                    Port="20000")),
            ("AddressInfo-guid-usb", _address_info("guid-usb", AddressingModeSelection="Dnp3Usb",
                                                    TargetAddress="0", LocalConnection="true")),
            ("ActiveProtocol-guid-tcp", _active_protocol("guid-tcp", "DNP3 TCP")),
        ),
    ))
    result = station({"demo.PRJ": prj})

    assert len(result.device_type_managers) == 2
    comm, device = result.device_type_managers
    assert comm.name == "PC Communication Settings -DNP3 CommDTM"
    assert [v.protocol_name for v in comm.supported_protocols] == ["DNP3 TCP", "DNP3 USB"]
    active = next(cp for cp in device.configured_protocols if cp.active)
    assert active.protocol_id == "guid-tcp"
    assert active.protocol_name == "DNP3 TCP"
    assert active.ip_address == "172.16.1.200"
    assert active.port == 20000
    inactive = next(cp for cp in device.configured_protocols if not cp.active)
    assert inactive.protocol_id == "guid-usb"
    assert inactive.protocol_name == "DNP3 USB"  # resolved from the OTHER DTM's catalog
    assert inactive.local_connection is True


def test_display_name_decodes_xml_name_escapes():
    prj = _prj(_dtm("d1", "SCADAPack_x0020_x70"))
    result = station({"demo.PRJ": prj})

    assert result.device_type_managers[0].name == "SCADAPack x70"


def test_dtm_with_no_configured_protocols_has_an_empty_list_not_a_guess():
    prj = _prj(_dtm("d1", "Bare DTM"))
    result = station({"demo.PRJ": prj})

    assert result.device_type_managers[0].configured_protocols == []
    assert result.device_type_managers[0].supported_protocols == []


def test_invalid_base64_instance_record_is_diagnosed_not_silently_dropped():
    prj = _prj(_dtm("d1", "Broken DTM", records=(
        ("AddressInfo-guid-x", "not valid base64!!"),
    )))
    result = station({"demo.PRJ": prj})

    assert result.device_type_managers[0].configured_protocols == []
    assert any(d.code == "unresolved_dtm_blob" for d in result.diagnostics)


def test_non_fdt_dtm_project_xml_is_ignored_by_dtm_mapping():
    result = station({"demo.PRJ": b'<?xml version="1.0"?><SomethingElse/>'})

    assert result.device_type_managers == []


def test_dtm_mapping_is_deterministic():
    prj = _prj(_dtm(
        "comm-dtm", "Comm",
        engineering_data=_device_type_info("P", "M", [("g1", "DNP3 TCP")]),
    ), _dtm("device-dtm", "Device", records=(
        ("AddressInfo-g1", _address_info("g1", TargetAddress="1")),
        ("ActiveProtocol-g1", _active_protocol("g1", "DNP3 TCP")),
    )))
    data = _sta({"demo.PRJ": prj})

    first = parse_station(capture_bytes(data, name="demo.STA"))
    second = parse_station(capture_bytes(data, name="demo.STA"))

    assert [dtm.configured_protocols for dtm in first.device_type_managers] == \
        [dtm.configured_protocols for dtm in second.device_type_managers]
