from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

from twinforge.analysis import analyze_structured_text_semantics
from twinforge.exporters import (
    PLCOPEN_CODESYS_NAMESPACE,
    CodesysArgumentBinding,
    CodesysIRPLCopenExporter,
    CodesysProjectIntegration,
)
from twinforge.ir import (
    IRNormalizationPolicy,
    lower_add_on_instruction,
    normalize_reusable_unit,
)
from twinforge.parsers import L5XParser


DATA = Path(__file__).parent / "data/aoi"
FIXED_TIME = datetime(2026, 7, 26, tzinfo=timezone.utc)
NS = {
    "p": PLCOPEN_CODESYS_NAMESPACE,
    "x": "http://www.w3.org/1999/xhtml",
}


def _normalized_str_capacity():
    controller = next(
        L5XParser()
        .parse(DATA / "Str_Capacity_AOI.L5X", report_mode=None)
        .iter_controllers()
    )
    instruction = controller.add_on_instructions["Str_Capacity"]
    report = analyze_structured_text_semantics(controller)
    lowered = lower_add_on_instruction(
        instruction,
        {
            finding.routine: finding.semantics
            for finding in report.routines
            if finding.owner == "AOI:Str_Capacity"
        },
    )
    return normalize_reusable_unit(
        lowered,
        IRNormalizationPolicy.PROMOTE_WRITTEN_INPUTS,
    ).unit


def _export():
    return CodesysIRPLCopenExporter().export(
        _normalized_str_capacity(),
        project_name="StrCapacity",
        creation_time=FIXED_TIME,
    )


def test_exports_codesys_function_block_with_st_body():
    result = _export()
    root = ET.fromstring(result.xml)
    pou = root.find(".//p:pou[@name='Str_Capacity']", NS)

    assert pou is not None
    assert pou.attrib["pouType"] == "functionBlock"
    assert (
        pou.findtext("p:body/p:ST/x:xhtml", namespaces=NS)
        == "Val := ((UPPER_BOUND(Ref_Data, (0 + 1)) - "
        "LOWER_BOUND(Ref_Data, (0 + 1))) + 1);"
    )
    assert result.requirements == ()
    assert result.complete


def test_matches_native_codesys_variable_length_inout_encoding():
    root = ET.fromstring(_export().xml)
    variable = root.find(
        ".//p:pou[@name='Str_Capacity']/p:interface/"
        "p:inputVars/p:variable[@name='Ref_Data']",
        NS,
    )

    assert variable is not None
    assert variable.find("p:type/p:pointer/p:baseType/p:SINT", NS) is not None
    values = {
        item.attrib["Name"]: item.attrib["Value"]
        for item in variable.findall(
            "p:addData/p:data/p:Attributes/p:Attribute",
            NS,
        )
    }
    assert values == {
        "variable_length_array_original_scope": "Inout",
        "variable_length_array": "ARRAY[*] OF SINT",
        "Dimensions": "1",
    }


def test_exports_interface_and_deterministic_project_structure():
    first = _export()
    second = _export()
    root = ET.fromstring(first.xml)

    assert first.xml == second.xml
    assert root.find(
        ".//p:pou/p:interface/p:inputVars/"
        "p:variable[@name='EnableIn']/p:type/p:BOOL",
        NS,
    ) is not None
    assert root.find(
        ".//p:pou/p:interface/p:outputVars/"
        "p:variable[@name='EnableOut']/p:type/p:BOOL",
        NS,
    ) is not None
    assert root.find(
        ".//p:pou/p:interface/p:outputVars/"
        "p:variable[@name='Val']/p:type/p:DINT",
        NS,
    ) is not None
    assert root.find(
        ".//p:ProjectStructure/p:Object[@Name='Application']/"
        "p:Object[@Name='Str_Capacity']",
        NS,
    ) is not None


def test_exports_explicit_program_call_and_scheduled_task():
    integration = CodesysProjectIntegration(
        instance_name="fbStrCapacity",
        bindings=(
            CodesysArgumentBinding(
                "EnableIn",
                "xEnable",
                initial_value="TRUE",
            ),
            CodesysArgumentBinding("EnableOut", "xEnableOut"),
            CodesysArgumentBinding(
                "Ref_Data",
                "aData",
                dimensions="10",
            ),
            CodesysArgumentBinding("Val", "diCapacity"),
        ),
    )
    result = CodesysIRPLCopenExporter().export(
        _normalized_str_capacity(),
        project_name="Integrated",
        creation_time=FIXED_TIME,
        integration=integration,
    )
    root = ET.fromstring(result.xml)

    task = root.find(".//p:task[@name='MainTask']", NS)
    assert task is not None
    assert task.attrib == {
        "name": "MainTask",
        "interval": "PT0.02S",
        "priority": "1",
    }
    assert task.find("p:pouInstance[@name='PLC_PRG']", NS) is not None
    assert task.find(
        "p:addData/p:data/p:TaskSettings/p:Watchdog",
        NS,
    ) is not None

    program = root.find(".//p:pou[@name='PLC_PRG']", NS)
    assert program is not None
    assert program.find(
        "p:interface/p:localVars/p:variable[@name='fbStrCapacity']/"
        "p:type/p:derived[@name='Str_Capacity']",
        NS,
    ) is not None
    assert program.find(
        "p:interface/p:localVars/p:variable[@name='aData']/"
        "p:type/p:array/p:dimension[@lower='0'][@upper='9']",
        NS,
    ) is not None
    assert program.find(
        "p:interface/p:localVars/p:variable[@name='xEnable']/"
        "p:initialValue/p:simpleValue[@value='TRUE']",
        NS,
    ) is not None
    assert program.findtext("p:body/p:ST/x:xhtml", namespaces=NS) == """\
fbStrCapacity(
    EnableIn := xEnable,
    EnableOut => xEnableOut,
    Ref_Data := aData,
    Val => diCapacity
);"""
    assert root.find(
        ".//p:ProjectStructure/p:Object[@Name='Application']/"
        "p:Object[@Name='PLC_PRG']",
        NS,
    ) is not None
    assert root.find(
        ".//p:ProjectStructure/p:Object[@Name='Application']/"
        "p:Object[@Name='MainTask']",
        NS,
    ) is not None
