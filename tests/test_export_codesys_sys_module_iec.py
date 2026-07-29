from datetime import datetime, timezone
import xml.etree.ElementTree as ET

from twinforge.exporters import (
    PLCOPEN_CODESYS_NAMESPACE,
    CodesysIRPLCopenExporter,
    build_codesys_sys_module_binding_unit,
    codesys_sys_module_binding_integration,
    emit_iec_st_unit,
)


NS = {
    "p": PLCOPEN_CODESYS_NAMESPACE,
    "x": "http://www.w3.org/1999/xhtml",
}
FIXED_TIME = datetime(2026, 7, 28, tzinfo=timezone.utc)


def test_binding_lowers_to_complete_iec_without_rockwell_module_services():
    result = emit_iec_st_unit(build_codesys_sys_module_binding_unit())

    assert result.complete
    assert result.requirements == ()
    assert result.diagnostics == ()
    assert result.text.startswith(
        "FUNCTION_BLOCK TF_Codesys_ENIP_ModuleBinding"
    )
    assert "Out_RequestReconfigure := TRUE;" in result.text
    assert (
        "Inp_CanReconfigure AND NOT (Inp_ReconfigureBusy)" in result.text
    )
    assert "MODULE" not in result.text
    assert "GSV" not in result.text
    assert "SSV" not in result.text
    assert "EntryStatus" not in result.text


def test_codesys_export_contains_binding_program_and_main_task():
    result = CodesysIRPLCopenExporter().export(
        build_codesys_sys_module_binding_unit(),
        project_name="CodesysSysModuleBinding",
        creation_time=FIXED_TIME,
        integration=codesys_sys_module_binding_integration(),
    )
    root = ET.fromstring(result.xml)

    assert result.complete
    assert result.requirements == ()
    assert root.find(
        ".//p:pou[@name='TF_Codesys_ENIP_ModuleBinding']",
        NS,
    ) is not None
    assert root.find(".//p:pou[@name='PLC_PRG']", NS) is not None
    assert root.find(".//p:task[@name='MainTask']", NS) is not None


def test_integration_binds_every_parameter_and_uses_cyclic_task():
    unit = build_codesys_sys_module_binding_unit()
    integration = codesys_sys_module_binding_integration()

    assert {binding.parameter_name for binding in integration.bindings} == {
        parameter.name for parameter in unit.parameters
    }
    assert integration.instance_name == "fbModuleBinding"
    assert integration.interval_ms == 20


def test_device_integration_emits_verified_diagnostic_handshake_once():
    result = CodesysIRPLCopenExporter().export(
        build_codesys_sys_module_binding_unit(),
        project_name="CodesysEnipModuleAdapter",
        creation_time=FIXED_TIME,
        integration=codesys_sys_module_binding_integration("Dev_TestModule"),
    )
    root = ET.fromstring(result.xml)
    program = root.find(".//p:pou[@name='PLC_PRG']", NS)
    assert program is not None
    body = program.findtext("./p:body/p:ST/x:xhtml", namespaces=NS)
    assert body is not None

    assert body.count("fbReconfigure(") == 1
    assert "Dev_TestModule.GetDeviceState()" in body
    assert "DED.CanReconfigure(" in body
    assert "Dev_TestModule.Enable := xOut_RequestedEnable;" in body
    assert body.index("xInp_ReconfigureBusy :=") < body.index(
        "fbModuleBinding("
    )
    assert body.index("fbModuleBinding(") < body.index(
        "Dev_TestModule.Enable :="
    )
    assert body.index("Dev_TestModule.Enable :=") < body.index(
        "fbReconfigure("
    )
    assert "PF525" not in body

    variables = {
        variable.attrib["name"]: variable
        for variable in program.findall(
            "./p:interface/p:localVars/p:variable",
            NS,
        )
    }
    assert variables["fbReconfigure"].find(
        "./p:type/p:derived[@name='DED.Reconfigure']",
        NS,
    ) is not None
    assert variables["sObservedDiagnostic"].find(
        "./p:type/p:string[@length='255']",
        NS,
    ) is not None


def test_device_integration_rejects_unstructured_iec_expression():
    try:
        codesys_sys_module_binding_integration("Dev.One")
    except ValueError as error:
        assert "simple IEC 61131-3 identifier" in str(error)
    else:
        raise AssertionError("invalid device variable was accepted")
