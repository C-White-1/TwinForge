from datetime import datetime, timezone
import xml.etree.ElementTree as ET

from twinforge.exporters import (
    PLCOPEN_CODESYS_NAMESPACE,
    CodesysIRPLCopenExporter,
    build_codesys_sys_module_binding_unit,
    build_powerflex525_iec_unit,
    emit_iec_st_unit,
    powerflex525_codesys_application_integration,
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


def test_codesys_export_can_package_multiple_reusable_units():
    result = CodesysIRPLCopenExporter().export(
        build_powerflex525_iec_unit(),
        additional_units=(build_codesys_sys_module_binding_unit(),),
        project_name="PowerFlexApplication",
        creation_time=FIXED_TIME,
        integration=powerflex525_codesys_integration(),
    )
    root = ET.fromstring(result.xml)

    assert result.complete
    assert root.find(
        ".//p:pou[@name='TF_PowerFlex525_Core']",
        NS,
    ) is not None


def test_composed_application_calls_core_and_module_binding():
    result = CodesysIRPLCopenExporter().export(
        build_powerflex525_iec_unit(),
        additional_units=(build_codesys_sys_module_binding_unit(),),
        project_name="PowerFlexApplication",
        creation_time=FIXED_TIME,
        integration=powerflex525_codesys_application_integration(
            "Dev_Drive01"
        ),
    )
    root = ET.fromstring(result.xml)
    program = root.find(".//p:pou[@name='PLC_PRG']", NS)
    assert program is not None
    body = program.findtext("./p:body/p:ST/x:xhtml", namespaces=NS)
    assert body is not None

    assert body.count("fbPowerFlex525(") == 1
    assert body.count("fbModuleBinding(") == 1
    assert body.count("fbReconfigure(") == 1
    assert "Dev_Drive01.GetDeviceState()" in body
    assert body.index("Dev_Drive01.GetDeviceState()") < body.index(
        "fbPowerFlex525("
    )
    assert body.index("fbPowerFlex525(") < body.index(
        "fbModuleBinding("
    )
    assert body.index("fbModuleBinding(") < body.index(
        "fbReconfigure("
    )
    assert program.find(
        "./p:interface/p:localVars/"
        "p:variable[@name='fbModuleBinding']/"
        "p:type/p:derived[@name='TF_Codesys_ENIP_ModuleBinding']",
        NS,
    ) is not None
    assert root.find(
        ".//p:pou[@name='TF_Codesys_ENIP_ModuleBinding']",
        NS,
    ) is not None
    assert root.find(
        ".//p:ProjectStructure/p:Object[@Name='Application']/"
        "p:Object[@Name='TF_PowerFlex525_Core']",
        NS,
    ) is not None
    assert root.find(
        ".//p:ProjectStructure/p:Object[@Name='Application']/"
        "p:Object[@Name='TF_Codesys_ENIP_ModuleBinding']",
        NS,
    ) is not None
