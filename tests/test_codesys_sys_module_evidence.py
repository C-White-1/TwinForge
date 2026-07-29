from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).parents[1]
PLCOPEN = (
    ROOT
    / "examples"
    / "PLCOpenXML"
    / "12_enip_remote_adapter_diagnostics.xml"
)
NATIVE = (
    ROOT
    / "examples"
    / "CODESYS"
    / "33_sys_module_enip_diagnostics.export"
)
NS = {
    "p": "http://www.plcopen.org/xml/tc6_0200",
    "x": "http://www.w3.org/1999/xhtml",
}


def _program_body() -> str:
    root = ET.parse(PLCOPEN).getroot()
    body = root.find(
        ".//p:pou[@name='PLC_PRG']/p:body/p:ST/x:xhtml",
        NS,
    )
    assert body is not None
    return body.text or ""


def _native_value(visible_name: str) -> str:
    root = ET.parse(NATIVE).getroot()
    for data in root.findall(".//Single"):
        name = data.find(
            "./Single[@Name='VisibleName']/Single[@Name='Default']"
        )
        value = data.find("./Single[@Name='Value']")
        if (
            name is not None
            and name.text == visible_name
            and value is not None
            and value.text is not None
        ):
            return value.text
    raise AssertionError(f"native value not found: {visible_name}")


def test_plcopen_evidence_contains_program_binding_and_task() -> None:
    root = ET.parse(PLCOPEN).getroot()

    assert root.find(
        ".//p:pou[@name='TF_Codesys_ENIP_ModuleBinding']",
        NS,
    ) is not None
    assert root.find(".//p:pou[@name='PLC_PRG']", NS) is not None
    task = root.find(".//p:task[@name='MainTask']", NS)
    assert task is not None
    assert task.attrib["interval"] == "PT0.02S"


def test_reconfigure_is_called_once_after_binding_with_feedback() -> None:
    body = _program_body()

    assert body.count("fbReconfigure(") == 1
    assert "xExecute := FALSE" not in body
    feedback = body.index(
        "xInp_ReconfigureBusy :=\n    fbReconfigure.xBusy;"
    )
    binding = body.index("fbModuleBinding(")
    enable = body.index(
        "Dev_PF525.Enable := xOut_RequestedEnable;"
    )
    reconfigure = body.index("fbReconfigure(")
    assert feedback < binding < enable < reconfigure
    assert "xInp_ReconfigureDone :=\n    fbReconfigure.xDone;" in body
    assert "xInp_ReconfigureFailed :=\n    fbReconfigure.xError;" in body


def test_program_uses_verified_diagnostic_interfaces() -> None:
    body = _program_body()

    assert (
        "eObservedDeviceState := Dev_PF525.GetDeviceState();" in body
    )
    assert "DED.CanReconfigure(itfNode := Dev_PF525)" in body
    assert "IoDrvEtherNetIP.AdapterState.RUNNING" in body
    assert "IoDrvEtherNetIP.AdapterState.BUS_ERROR" in body
    assert "DED.DEVICE_STATE.RUNNING" in body
    assert "DED.DEVICE_STATE.ERROR" in body


def test_native_evidence_preserves_source_connection_configuration() -> None:
    assert _native_value("IP address of Target") == (
        "[16#C0,16#A8,16#01,16#50]"
    )
    assert _native_value("Requested packet interval") == "10000"
    assert _native_value("Connection Path") == (
        "[16#20,16#04,16#24,16#06,16#2C,16#02,16#2C,16#01]"
    )


def test_native_evidence_preserves_images_and_generated_diagnostics() -> None:
    text = NATIVE.read_text(encoding="utf-8-sig")

    for index in range(4):
        assert f">Output_Param{index}<" in text
    for index in range(8):
        assert f">Input_Param{index}<" in text
    assert ">Dev_PF525<" in text
    assert ">RemoteAdapter_diag<" in text
    assert "CAA Device Diagnosis, 3.5.22.0" in text
    assert "IoDrvEtherNetIP, 4.9.0.0" in text
