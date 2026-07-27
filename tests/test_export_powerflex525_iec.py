from datetime import datetime, timezone
import xml.etree.ElementTree as ET

from twinforge.exporters import (
    PLCOPEN_CODESYS_NAMESPACE,
    CodesysIRPLCopenExporter,
    build_powerflex525_iec_unit,
    emit_iec_st_unit,
    powerflex525_codesys_integration,
)


NS = {
    "p": PLCOPEN_CODESYS_NAMESPACE,
    "x": "http://www.w3.org/1999/xhtml",
}
FIXED_TIME = datetime(2026, 7, 27, tzinfo=timezone.utc)


def test_powerflex_core_lowers_to_complete_target_neutral_iec():
    result = emit_iec_st_unit(build_powerflex525_iec_unit())

    assert result.complete
    assert result.requirements == ()
    assert result.diagnostics == ()
    assert result.text.startswith("FUNCTION_BLOCK TF_PowerFlex525_Core")
    assert "RunFwd := " in result.text
    assert "Out_LogicCommand := (Out_LogicCommand + 64);" in result.text
    assert (
        "Out_SpeedCommand := REAL_TO_INT((SpeedRef * 100.0));"
        in result.text
    )


def test_codesys_export_contains_function_block_program_and_task():
    result = CodesysIRPLCopenExporter().export(
        build_powerflex525_iec_unit(),
        project_name="PowerFlexCore",
        creation_time=FIXED_TIME,
        integration=powerflex525_codesys_integration(),
    )
    root = ET.fromstring(result.xml)

    assert result.complete
    assert result.requirements == ()
    assert root.find(
        ".//p:pou[@name='TF_PowerFlex525_Core']",
        NS,
    ) is not None
    assert root.find(".//p:pou[@name='PLC_PRG']", NS) is not None
    assert root.find(".//p:task[@name='MainTask']", NS) is not None
    body = root.findtext(
        ".//p:pou[@name='TF_PowerFlex525_Core']/p:body/p:ST/x:xhtml",
        namespaces=NS,
    )
    assert body is not None
    assert "PF525" not in body
    assert "MESSAGE" not in body
    assert "GSV" not in body


def test_integration_binds_every_function_block_parameter():
    unit = build_powerflex525_iec_unit()
    integration = powerflex525_codesys_integration()

    assert {item.parameter_name for item in integration.bindings} == {
        item.name for item in unit.parameters
    }
    assert integration.instance_name == "fbPowerFlex525"
    assert integration.interval_ms == 20
