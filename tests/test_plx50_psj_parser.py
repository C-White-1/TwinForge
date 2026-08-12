import base64
from pathlib import Path

from twinforge.converters import DiagnosticSeverity
from twinforge.parsers import PLX50PSJParser


def _write_psj(path: Path, xml: str) -> None:
    encoded = base64.b64encode(
        bytes(value ^ 0x5A for value in xml.encode("utf-8"))
    ).decode("ascii")
    path.write_text(encoded, encoding="ascii")


def test_decodes_native_container_and_preserves_unknown_xml(tmp_path: Path):
    source = tmp_path / "project.psj"
    _write_psj(
        source,
        """<?xml version="1.0" encoding="utf-16"?>
<ProjectConfig xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Devices>
    <GenericDevice xsi:type="PSPBDevicePLX51PBM" DeviceName="Gateway" ConnectionPath="0.0.0.0" FutureDevice="keep">
      <Config InstanceName="Gateway" Description="Fixture" IPAddress="192.0.2.10" Mode="StandaloneMaster" PrimaryInterface="EtherNetIP" FutureConfig="retain">
        <DeviceConfig><FutureNode Value="evidence" /></DeviceConfig>
      </Config>
    </GenericDevice>
  </Devices>
</ProjectConfig>""",
    )

    document = PLX50PSJParser().parse(source)

    assert len(document.devices) == 1
    device = document.devices[0]
    assert device.device_type == "PSPBDevicePLX51PBM"
    assert device.device_name == "Gateway"
    assert device.instance_name == "Gateway"
    assert device.description == "Fixture"
    assert device.ip_address == "192.0.2.10"
    assert device.mode == "StandaloneMaster"
    assert device.primary_interface == "EtherNetIP"
    assert device.config_value("FutureConfig") == "retain"
    assert device.profibus_devices == ()
    assert dict(device.device_attributes)["FutureDevice"] == "keep"
    future_node = (
        device.source_extension.root.children[0].children[0].children[0]
    )
    assert future_node.name == "FutureNode"
    assert document.source_extension is not None
    assert document.source_extension.metadata == {
        "container_encoding": "Base64",
        "container_obfuscation": "XOR-0x5A",
    }
    assert document.encoded_text == source.read_text(encoding="ascii")
    assert document.diagnostics == ()


def test_promotes_configured_profibus_slots_and_data_points(tmp_path: Path):
    source = tmp_path / "profibus.psj"
    _write_psj(
        source,
        """<ProjectConfig xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<Devices><GenericDevice xsi:type="PSPBDevicePLX51PBM" DeviceName="Gateway">
<Config InstanceName="Gateway">
<DeviceConfig><PSPBConfigDevice VendorName="ProSoft" ModelName="PLX51-PBM" InstanceName="TF_DP_SLAVE_01" StationAddress="3" Ident="4350" GSDRevision="5" GSDFileName="PSFT10FE.GSD" FutureDevice="keep">
<Slots>
<PSPBConfigSlot SlotID="1" ModuleID="3"><DataPoints>
<PSPBConfigSlotDataPoint DataPointType="Input" DataFormat="REAL" ByteLength="4" LocalOffset="0" Description="Input4Bytes" ModbusRegisterType="HR" InterfaceConnectionOffset="0" FuturePoint="retain" />
</DataPoints></PSPBConfigSlot>
</Slots></PSPBConfigDevice></DeviceConfig>
</Config></GenericDevice></Devices></ProjectConfig>""",
    )

    document = PLX50PSJParser().parse(source)

    device = document.devices[0].profibus_devices[0]
    assert device.instance_name == "TF_DP_SLAVE_01"
    assert device.station_address == 3
    assert device.ident_number == 4350
    assert device.gsd_revision == 5
    assert device.gsd_filename == "PSFT10FE.GSD"
    assert dict(device.attributes)["FutureDevice"] == "keep"
    slot = device.slots[0]
    assert (slot.slot_id, slot.module_id) == (1, 3)
    point = slot.data_points[0]
    assert point.data_point_type == "Input"
    assert point.data_format == "REAL"
    assert point.byte_length == 4
    assert point.local_offset == 0
    assert point.description == "Input4Bytes"
    assert point.modbus_register_type == "HR"
    assert point.interface_connection_offset == 0
    assert dict(point.attributes)["FuturePoint"] == "retain"
    assert document.diagnostics == ()


def test_invalid_container_is_retained_and_diagnosed(tmp_path: Path):
    source = tmp_path / "invalid.psj"
    source.write_text("not base64!", encoding="ascii")

    document = PLX50PSJParser().parse(source)

    assert document.encoded_text == "not base64!"
    assert document.devices == ()
    assert document.decoded_xml is None
    assert document.diagnostics[0].code == "invalid_plx50_psj_base64"
    assert document.diagnostics[0].severity is DiagnosticSeverity.ERROR
