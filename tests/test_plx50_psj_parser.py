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


def test_invalid_container_is_retained_and_diagnosed(tmp_path: Path):
    source = tmp_path / "invalid.psj"
    source.write_text("not base64!", encoding="ascii")

    document = PLX50PSJParser().parse(source)

    assert document.encoded_text == "not base64!"
    assert document.devices == ()
    assert document.decoded_xml is None
    assert document.diagnostics[0].code == "invalid_plx50_psj_base64"
    assert document.diagnostics[0].severity is DiagnosticSeverity.ERROR
