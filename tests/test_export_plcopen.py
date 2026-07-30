from datetime import datetime, timezone
import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path

from twinforge.exporters import (
    PLCOPEN_201_NAMESPACE,
    PLCOPEN_CODESYS_NAMESPACE,
    PLCopenExporter,
    PLCopenProfile,
)
from twinforge.model import (
    Controller,
    Identity,
    LadderRung,
    Program,
    Routine,
    Tag,
    Task,
)
from twinforge.parsers import L5XParser


FIXED_TIME = datetime(2026, 7, 23, tzinfo=timezone.utc)
SAMPLE_L5X = Path(__file__).parent / "data/basic/BoosterCompressor_20260128.L5X"


def _find(
    parent: ET.Element,
    path: str,
    namespaces: dict[str, str],
) -> ET.Element:
    """Find a required XML element and narrow its optional return type."""

    element = parent.find(path, namespaces)
    assert element is not None, f"missing XML element: {path}"
    return element


def _main_routine(program: Program) -> Routine:
    """Return the required main routine used by exporter test fixtures."""

    routine = program.main_routine
    assert routine is not None
    return routine


def _controller() -> Controller:
    controller = Controller(name="TestPLC", identity=Identity())
    controller.add_tag(Tag(name="gEnable", data_type="BOOL", description="Enable"))
    controller.add_tag(Tag(name="gCount", data_type="DINT"))

    program = Program(name="PLC_PRG")
    program.add_tag(
        Tag(name="xRunning", data_type="BOOL", description="Running Coil")
    )
    routine = Routine(name="MainRoutine", language="RLL")
    routine.ladder_rungs.append(
        LadderRung(
            number=0,
            comment="Start motor",
            text="XIC(gEnable)XIO(Stop)OTE(xRunning);",
        )
    )
    program.add_routine(routine)
    controller.add_program(program)

    task = Task(
        name="MainTask",
        task_type="Periodic",
        rate=20,
        priority=1,
        scheduled_program_names=[program.name],
        scheduled_programs=[program],
    )
    controller.add_task(task)
    return controller


def _export(profile: PLCopenProfile):
    return PLCopenExporter(profile).export(
        _controller(), project_name="TestProject", creation_time=FIXED_TIME
    )


def test_fixed_time_profile_exports_are_byte_stable() -> None:
    """Protect the public façade and deterministic serialization contract."""

    expected_hashes = {
        PLCopenProfile.STANDARD_201: (
            "bde3a3888a947a95119e4afd29941266bd9595f50d23f3067fcb6e13050dc346"
        ),
        PLCopenProfile.CODESYS: (
            "ab7ea8f042138bfb9bfee62b15ce7f0061309b52ccd5627ec0fd5a48a3927a0f"
        ),
    }

    for profile, expected_hash in expected_hashes.items():
        xml = _export(profile).xml.encode("utf-8")
        assert hashlib.sha256(xml).hexdigest() == expected_hash


def test_standard_profile_exports_program_variables_task_and_ld() -> None:
    result = _export(PLCopenProfile.STANDARD_201)
    ns = {"p": PLCOPEN_201_NAMESPACE, "x": "http://www.w3.org/1999/xhtml"}
    root = ET.fromstring(result.xml)

    assert root.tag == f"{{{PLCOPEN_201_NAMESPACE}}}project"
    assert root.find("p:types/p:pous/p:pou[@name='PLC_PRG']", ns) is not None
    assert (
        root.findtext(
            "p:types/p:pous/p:pou/p:interface/p:localVars/"
            "p:variable[@name='xRunning']/p:documentation/x:xhtml",
            namespaces=ns,
        )
        == "Running Coil"
    )
    task = root.find(
        "p:instances/p:configurations/p:configuration/p:resource/"
        "p:task[@name='MainTask']",
        ns,
    )
    assert task is not None
    assert task.attrib["interval"] == "PT0.02S"
    assert _find(
        task,
        "p:pouInstance[@name='PLC_PRG']",
        ns,
    ).attrib["typeName"] == "PLC_PRG"

    contact = root.find(".//p:contact[p:variable='gEnable']", ns)
    negated_contact = root.find(".//p:contact[p:variable='Stop']", ns)
    coil = root.find(".//p:coil[p:variable='xRunning']", ns)
    assert contact is not None
    assert negated_contact is not None and negated_contact.attrib["negated"] == "true"
    assert coil is not None
    assert result.diagnostics == []


def test_standard_profile_does_not_emit_codesys_extensions() -> None:
    """Target-neutral output must not inherit CODESYS project conventions."""

    result = _export(PLCopenProfile.STANDARD_201)

    assert "www.3s-software.com" not in result.xml
    assert "ProjectStructure" not in result.xml
    assert "TaskSettings" not in result.xml
    assert "Standard." not in result.xml


def test_codesys_profile_wraps_application_content_in_add_data() -> None:
    result = _export(PLCopenProfile.CODESYS)
    ns = {"p": PLCOPEN_CODESYS_NAMESPACE}
    root = ET.fromstring(result.xml)

    assert root.find("p:types/p:pous", ns) is not None
    assert list(_find(root, "p:types/p:pous", ns)) == []
    application = root.find(
        "p:addData/p:data[@name='http://www.3s-software.com/plcopenxml/application']",
        ns,
    )
    assert application is not None
    task = application.find("p:resource/p:task[@name='MainTask']", ns)
    assert task is not None
    assert task.find(
        "p:pouInstance[@name='PLC_PRG']/p:documentation", ns
    ) is not None
    assert task.find(
        "p:addData/p:data/p:TaskSettings/p:Watchdog", ns
    ) is not None
    assert application.find(
        "p:resource/p:globalVars[@name='ControllerTags']/p:variable[@name='gEnable']",
        ns,
    ) is not None
    assert application.find(
        "p:resource/p:addData/p:data/p:pou[@name='PLC_PRG']", ns
    ) is not None
    structure = root.find(
        "p:addData/p:data[@name="
        "'http://www.3s-software.com/plcopenxml/projectstructure']/"
        "p:ProjectStructure/p:Object[@Name='Application']",
        ns,
    )
    assert structure is not None
    assert structure.find("p:Object[@Name='MainTask']", ns) is not None
    assert structure.find("p:Object[@Name='ControllerTags']", ns) is not None


def test_codesys_profile_exports_routines_as_actions_and_jsr_as_action_call() -> None:
    controller = _controller()
    program = controller.programs["PLC_PRG"]
    _main_routine(program).ladder_rungs = [
        LadderRung(number=0, text="JSR(ReadInputs,0);")
    ]
    action_routine = Routine(name="ReadInputs", language="RLL")
    action_routine.ladder_rungs.append(
        LadderRung(number=0, text="XIC(gEnable)OTE(xRunning);")
    )
    program.add_routine(action_routine)

    result = PLCopenExporter(PLCopenProfile.CODESYS).export(
        controller, creation_time=FIXED_TIME
    )
    ns = {"p": PLCOPEN_CODESYS_NAMESPACE}
    root = ET.fromstring(result.xml)
    pou = root.find(".//p:pou[@name='PLC_PRG']", ns)
    assert pou is not None
    action = pou.find("p:actions/p:action[@name='ReadInputs']", ns)
    assert action is not None
    assert action.find(".//p:contact[p:variable='gEnable']", ns) is not None
    assert action.find(".//p:coil[p:variable='xRunning']", ns) is not None

    block = pou.find("p:body/p:LD/p:block[@typeName='ReadInputs']", ns)
    assert block is not None
    assert block.find(
        "p:inputVariables/p:variable[@formalParameter='EN']/"
        "p:connectionPointIn/p:connection",
        ns,
    ) is not None
    assert block.find(
        "p:outputVariables/p:variable[@formalParameter='ENO']", ns
    ) is not None
    call_type = block.find(
        "p:addData/p:data[@name="
        "'http://www.3s-software.com/plcopenxml/fbdcalltype']/CallType",
        ns,
    )
    assert call_type is not None and call_type.text == "action"

    action_object_id = action.findtext(
        "p:addData/p:data[@name="
        "'http://www.3s-software.com/plcopenxml/objectid']/p:ObjectId",
        namespaces=ns,
    )
    structure_action = root.find(
        ".//p:ProjectStructure/p:Object[@Name='Application']/"
        "p:Object[@Name='PLC_PRG']/p:Object[@Name='ReadInputs']",
        ns,
    )
    assert structure_action is not None
    assert structure_action.attrib["ObjectId"] == action_object_id
    assert result.diagnostics == []


def test_unresolved_jsr_is_preserved_and_diagnosed() -> None:
    controller = _controller()
    _main_routine(controller.programs["PLC_PRG"]).ladder_rungs = [
        LadderRung(number=0, text="JSR(MissingRoutine,0);")
    ]
    result = PLCopenExporter(PLCopenProfile.CODESYS).export(
        controller, creation_time=FIXED_TIME
    )

    assert "Unresolved Rockwell RLL: JSR(MissingRoutine,0);" in result.xml
    assert [item.code for item in result.diagnostics] == [
        "unresolved_jsr_target"
    ]


def test_unsupported_rung_is_preserved_as_non_executable_text() -> None:
    controller = _controller()
    _main_routine(controller.programs["PLC_PRG"]).ladder_rungs = [
        LadderRung(number=0, text="CPT(Destination,Value);")
    ]
    result = PLCopenExporter().export(controller, creation_time=FIXED_TIME)

    assert "Unsupported Rockwell RLL: CPT(Destination,Value);" in result.xml
    assert "CPT(Destination,Value);" in result.xml
    assert [item.code for item in result.diagnostics] == ["unsupported_rll_rung"]


def test_aliases_are_portable_and_unsupported_types_are_diagnosed() -> None:
    controller = _controller()
    controller.add_tag(Tag(name="Motor", data_type="MOTOR_UDT"))
    controller.add_tag(Tag(name="Alias", alias_for="Local:1:I.Data.0"))
    _main_routine(controller.programs["PLC_PRG"]).ladder_rungs = [
        LadderRung(number=0, text="XIC(Local:1:I.Data.0)OTE(xRunning);")
    ]
    result = PLCopenExporter().export(controller, creation_time=FIXED_TIME)

    codes = {item.code for item in result.diagnostics}
    assert "unsupported_variable_type" in codes
    assert "alias_exported_as_surrogate" in codes
    assert 'name="Motor"' not in result.xml
    assert 'name="Alias"' in result.xml
    assert "<AliasFor" in result.xml
    assert "Local:1:I.Data.0" in result.xml
    assert "<variable>Alias</variable>" in result.xml


def test_raw_logix_operand_gets_deterministic_portable_variable() -> None:
    controller = _controller()
    _main_routine(controller.programs["PLC_PRG"]).ladder_rungs = [
        LadderRung(number=0, text="XIC(Local:2:I.Data.7)OTE(xRunning);")
    ]
    result = PLCopenExporter().export(controller, creation_time=FIXED_TIME)

    assert 'name="TF_Local_2_I_Data_7"' in result.xml
    assert "<variable>TF_Local_2_I_Data_7</variable>" in result.xml
    assert "Local:2:I.Data.7" in result.xml
    assert "raw_operand_rewritten" in {
        diagnostic.code for diagnostic in result.diagnostics
    }


def test_otl_and_otu_export_as_set_and_reset_coils() -> None:
    controller = _controller()
    program = controller.programs["PLC_PRG"]
    program.add_tag(Tag(name="Latch", data_type="BOOL"))
    _main_routine(program).ladder_rungs = [
        LadderRung(number=0, text="XIC(gEnable)OTL(Latch);"),
        LadderRung(number=1, text="XIO(gEnable)OTU(Latch);"),
    ]
    result = PLCopenExporter().export(controller, creation_time=FIXED_TIME)
    ns = {"p": PLCOPEN_201_NAMESPACE}
    root = ET.fromstring(result.xml)

    set_coil = root.find(".//p:coil[@storage='set'][p:variable='Latch']", ns)
    reset_coil = root.find(
        ".//p:coil[@storage='reset'][p:variable='Latch']", ns
    )
    assert set_coil is not None
    assert reset_coil is not None
    assert "unsupported_rll_rung" not in {
        diagnostic.code for diagnostic in result.diagnostics
    }


def test_multiple_output_coils_share_condition_instead_of_chaining() -> None:
    controller = _controller()
    program = controller.programs["PLC_PRG"]
    program.add_tag(Tag(name="First", data_type="BOOL"))
    program.add_tag(Tag(name="Second", data_type="BOOL"))
    _main_routine(program).ladder_rungs = [
        LadderRung(number=0, text="XIC(gEnable)OTU(First)OTU(Second);")
    ]
    result = PLCopenExporter().export(controller, creation_time=FIXED_TIME)
    ns = {"p": PLCOPEN_201_NAMESPACE}
    root = ET.fromstring(result.xml)
    contact = root.find(".//p:contact[p:variable='gEnable']", ns)
    first = root.find(".//p:coil[p:variable='First']", ns)
    second = root.find(".//p:coil[p:variable='Second']", ns)

    assert contact is not None
    assert first is not None
    assert second is not None
    expected = contact.attrib["localId"]
    assert _find(
        first,
        "p:connectionPointIn/p:connection", ns
    ).attrib["refLocalId"] == expected
    assert _find(
        second,
        "p:connectionPointIn/p:connection", ns
    ).attrib["refLocalId"] == expected


def test_parallel_paths_merge_before_serial_tail_and_outputs() -> None:
    controller = _controller()
    program = controller.programs["PLC_PRG"]
    for name in ("Start", "Remote", "Stop", "Permissive", "Run", "Latched"):
        program.add_tag(Tag(name=name, data_type="BOOL"))
    _main_routine(program).ladder_rungs = [
        LadderRung(
            number=0,
            text=(
                "[XIC(Start) ,XIC(Remote) XIO(Stop) ]"
                "XIC(Permissive)OTE(Run)OTL(Latched);"
            ),
        )
    ]
    result = PLCopenExporter().export(controller, creation_time=FIXED_TIME)
    ns = {"p": PLCOPEN_201_NAMESPACE}
    root = ET.fromstring(result.xml)
    rail = _find(root, ".//p:leftPowerRail", ns)
    start = _find(root, ".//p:contact[p:variable='Start']", ns)
    remote = _find(root, ".//p:contact[p:variable='Remote']", ns)
    stop = _find(root, ".//p:contact[p:variable='Stop']", ns)
    permissive = _find(
        root,
        ".//p:contact[p:variable='Permissive']",
        ns,
    )
    run = _find(root, ".//p:coil[p:variable='Run']", ns)
    latched = _find(root, ".//p:coil[p:variable='Latched']", ns)
    rail_id = rail.attrib["localId"]
    assert _find(
        start,
        "p:connectionPointIn/p:connection", ns
    ).attrib["refLocalId"] == rail_id
    assert _find(
        remote,
        "p:connectionPointIn/p:connection", ns
    ).attrib["refLocalId"] == rail_id
    assert _find(
        stop,
        "p:connectionPointIn/p:connection", ns
    ).attrib["refLocalId"] == remote.attrib["localId"]
    merge_refs = {
        connection.attrib["refLocalId"]
        for connection in permissive.findall(
            "p:connectionPointIn/p:connection", ns
        )
    }
    assert merge_refs == {start.attrib["localId"], stop.attrib["localId"]}
    for coil in (run, latched):
        assert _find(
            coil,
            "p:connectionPointIn/p:connection", ns
        ).attrib["refLocalId"] == permissive.attrib["localId"]


def test_comparison_operator_drives_downstream_ladder_condition() -> None:
    controller = _controller()
    program = controller.programs["PLC_PRG"]
    program.add_tag(Tag(name="Pressure", data_type="REAL"))
    program.add_tag(Tag(name="Limit", data_type="REAL"))
    program.add_tag(Tag(name="Enable", data_type="BOOL"))
    program.add_tag(Tag(name="Alarm", data_type="BOOL"))
    _main_routine(program).ladder_rungs = [
        LadderRung(
            number=0,
            text="GRT(Pressure,Limit)XIC(Enable)OTE(Alarm);",
        )
    ]
    result = PLCopenExporter(PLCopenProfile.CODESYS).export(
        controller, creation_time=FIXED_TIME
    )
    ns = {"p": PLCOPEN_CODESYS_NAMESPACE}
    root = ET.fromstring(result.xml)
    block = root.find(".//p:block[@typeName='GT']", ns)
    enable_contact = root.find(".//p:contact[p:variable='Enable']", ns)

    assert block is not None
    assert enable_contact is not None
    assert {
        element.text for element in root.findall(".//p:inVariable/p:expression", ns)
    } >= {"Pressure", "Limit"}
    input_parameters = [
        variable.attrib["formalParameter"]
        for variable in block.findall("p:inputVariables/p:variable", ns)
    ]
    assert input_parameters == ["EN", "", ""]
    output_parameters = [
        variable.attrib["formalParameter"]
        for variable in block.findall("p:outputVariables/p:variable", ns)
    ]
    assert output_parameters == ["ENO", ""]
    result_name = block.findtext(
        "p:outputVariables/p:variable[@formalParameter='']/"
        "p:connectionPointOut/p:expression",
        namespaces=ns,
    )
    assert result_name is not None and result_name.startswith("TF_Cmp_")
    assert root.find(
        f".//p:localVars/p:variable[@name='{result_name}']", ns
    ) is not None
    result_contact = root.find(
        f".//p:contact[p:variable='{result_name}']", ns
    )
    assert result_contact is not None
    connection = result_contact.find(
        "p:connectionPointIn/p:connection", ns
    )
    assert connection is not None
    rail = root.find(".//p:leftPowerRail", ns)
    assert rail is not None
    assert connection.attrib == {"refLocalId": rail.attrib["localId"]}
    enable_connection = enable_contact.find(
        "p:connectionPointIn/p:connection", ns
    )
    assert enable_connection is not None
    assert enable_connection.attrib == {
        "refLocalId": result_contact.attrib["localId"]
    }
    assert block.find("p:addData", ns) is None


def test_codesys_profile_exports_logix_ton_instances_and_presets() -> None:
    plant = L5XParser().parse(SAMPLE_L5X, report_mode=None)
    controller = next(plant.iter_controllers())

    result = PLCopenExporter(PLCopenProfile.CODESYS).export(
        controller, creation_time=FIXED_TIME
    )
    ns = {"p": PLCOPEN_CODESYS_NAMESPACE}
    root = ET.fromstring(result.xml)
    blocks = root.findall(".//p:block[@typeName='TON']", ns)

    assert len(blocks) == 21
    prelube = root.find(".//p:block[@instanceName='TMR_Prelube']", ns)
    assert prelube is not None
    assert root.find(
        ".//p:variable[@name='TMR_Prelube']/p:type/"
        "p:derived[@name='Standard.TON']",
        ns,
    ) is not None
    assert root.find(
        ".//p:data[@name='http://www.3s-software.com/plcopenxml/libraries']/"
        "p:Libraries/p:Library[@Name='#Standard']",
        ns,
    ) is not None
    assert root.find(
        ".//p:variable[@name='CFG_PT102_HH']/p:initialValue/"
        "p:simpleValue[@value='120.0']",
        ns,
    ) is not None
    assert root.find(
        ".//p:variable[@name='CFG_TripDelay']/p:initialValue/"
        "p:simpleValue[@value='2000']",
        ns,
    ) is not None
    process_unit = root.find(
        ".//p:variable[@name='PT102_PV']/p:addData/"
        "p:data[@name='https://twinforge.dev/plcopenxml/engineering-unit']/"
        "EngineeringUnit",
        ns,
    )
    assert process_unit is not None
    assert process_unit.attrib == {
        "Symbol": "barg",
        "Source": "l5x_module_channel",
        "Confidence": "explicit",
        "SourceOperand": "Local:4:I.CH2DATA",
    }
    threshold_unit = root.find(
        ".//p:variable[@name='CFG_PT102_HH']/p:addData/"
        "p:data[@name='https://twinforge.dev/plcopenxml/engineering-unit']/"
        "EngineeringUnit",
        ns,
    )
    assert threshold_unit is not None
    assert threshold_unit.attrib["Symbol"] == "barg"
    assert threshold_unit.attrib["Source"] == "rll_comparison"
    assert threshold_unit.attrib["Confidence"] == "derived"
    assert threshold_unit.attrib["InheritedFrom"] == "PT102_PV"
    assert root.find(
        ".//p:variable[@name='PT102_HH_Alm']/p:addData/"
        "p:data[@name='https://twinforge.dev/plcopenxml/engineering-unit']",
        ns,
    ) is None
    assert root.find(
        ".//p:ProjectStructure/p:Object[@Name='Application']/"
        "p:Object[@Name='Library Manager']",
        ns,
    ) is not None
    assert [
        variable.attrib["formalParameter"]
        for variable in prelube.findall("p:inputVariables/p:variable", ns)
    ] == ["EN", "IN", "PT"]
    assert [
        variable.attrib["formalParameter"]
        for variable in prelube.findall("p:outputVariables/p:variable", ns)
    ] == ["ENO", "Q", "ET"]
    preset_reference = _find(
        prelube,
        "p:inputVariables/p:variable[@formalParameter='PT']/"
        "p:connectionPointIn/p:connection",
        ns,
    ).attrib["refLocalId"]
    assert root.findtext(
        f".//p:inVariable[@localId='{preset_reference}']/p:expression",
        namespaces=ns,
    ) == "TIME#100000ms"
    assert prelube.findtext(
        "p:addData/p:data/CallType", namespaces=ns
    ) == "functionblock"
    expressions = {
        expression.text
        for expression in root.findall(".//p:inVariable/p:expression", ns)
    }
    assert "DINT_TO_TIME(CFG_TripDelay)" in expressions
    assert any(
        expression is not None and expression.endswith("_ET")
        for expression in expressions
    )


def test_codesys_profile_exports_standalone_res_as_false_ton_call() -> None:
    controller = _controller()
    controller.add_tag(Tag(name="ResettableTimer", data_type="TIMER"))
    program = controller.programs["PLC_PRG"]
    _main_routine(program).ladder_rungs = [
        LadderRung(number=0, text="XIC(gEnable)RES(ResettableTimer);")
    ]

    result = PLCopenExporter(PLCopenProfile.CODESYS).export(
        controller, creation_time=FIXED_TIME
    )
    ns = {"p": PLCOPEN_CODESYS_NAMESPACE}
    root = ET.fromstring(result.xml)
    block = root.find(".//p:block[@instanceName='ResettableTimer']", ns)

    assert block is not None
    input_reference = _find(
        block,
        "p:inputVariables/p:variable[@formalParameter='IN']/"
        "p:connectionPointIn/p:connection",
        ns,
    ).attrib["refLocalId"]
    assert root.findtext(
        f".//p:inVariable[@localId='{input_reference}']/p:expression",
        namespaces=ns,
    ) == "FALSE"


def test_value_blocks_preserve_left_to_right_execution_order() -> None:
    controller = _controller()
    program = controller.programs["PLC_PRG"]
    _main_routine(program).ladder_rungs = [
        LadderRung(
            number=0,
            text=(
                "XIC(gEnable)MOV(5,gCount)"
                "ADD(gCount,1,gCount)"
                "SUB(gCount,1,gCount)"
                "MUL(gCount,2,gCount)"
                "DIV(gCount,2,gCount)"
                "OTE(xRunning);"
            ),
        )
    ]

    result = PLCopenExporter(PLCopenProfile.CODESYS).export(
        controller, creation_time=FIXED_TIME
    )
    ns = {"p": PLCOPEN_CODESYS_NAMESPACE}
    root = ET.fromstring(result.xml)
    move = _find(root, ".//p:block[@typeName='MOVE']", ns)
    add = _find(root, ".//p:block[@typeName='ADD']", ns)
    subtract = _find(root, ".//p:block[@typeName='SUB']", ns)
    multiply = _find(root, ".//p:block[@typeName='MUL']", ns)
    divide = _find(root, ".//p:block[@typeName='DIV']", ns)
    coil = _find(root, ".//p:coil[p:variable='xRunning']", ns)
    assert [
        variable.attrib["formalParameter"]
        for variable in move.findall("p:inputVariables/p:variable", ns)
    ] == ["EN", ""]
    assert [
        variable.attrib["formalParameter"]
        for variable in add.findall("p:inputVariables/p:variable", ns)
    ] == ["EN", "", ""]
    add_enable = add.find(
        "p:inputVariables/p:variable[@formalParameter='EN']/"
        "p:connectionPointIn/p:connection",
        ns,
    )
    assert add_enable is not None
    assert add_enable.attrib == {
        "refLocalId": move.attrib["localId"],
        "formalParameter": "ENO",
    }
    preceding = move
    for current in (add, subtract, multiply, divide):
        enable_connection = current.find(
            "p:inputVariables/p:variable[@formalParameter='EN']/"
            "p:connectionPointIn/p:connection",
            ns,
        )
        assert enable_connection is not None
        assert enable_connection.attrib == {
            "refLocalId": preceding.attrib["localId"],
            "formalParameter": "ENO",
        }
        preceding = current
    coil_connection = coil.find(
        "p:connectionPointIn/p:connection", ns
    )
    assert coil_connection is not None
    assert coil_connection.attrib == {
        "refLocalId": divide.attrib["localId"],
        "formalParameter": "ENO",
    }


def test_ons_uses_native_r_trig_and_nop_is_intentional() -> None:
    controller = _controller()
    controller.add_tag(Tag(name="OneShotStorage", data_type="BOOL"))
    program = controller.programs["PLC_PRG"]
    _main_routine(program).ladder_rungs = [
        LadderRung(
            number=0,
            text="XIC(gEnable)ONS(OneShotStorage)ADD(gCount,1,gCount);",
        ),
        LadderRung(number=1, text="NOP();"),
    ]

    result = PLCopenExporter(PLCopenProfile.CODESYS).export(
        controller, creation_time=FIXED_TIME
    )
    ns = {"p": PLCOPEN_CODESYS_NAMESPACE}
    root = ET.fromstring(result.xml)
    trigger = root.find(".//p:block[@typeName='R_TRIG']", ns)

    assert trigger is not None
    assert [
        variable.attrib["formalParameter"]
        for variable in trigger.findall("p:inputVariables/p:variable", ns)
    ] == ["EN", "CLK"]
    assert [
        variable.attrib["formalParameter"]
        for variable in trigger.findall("p:outputVariables/p:variable", ns)
    ] == ["ENO", "Q"]
    assert root.find(
        ".//p:variable/p:type/p:derived[@name='Standard.R_TRIG']", ns
    ) is not None
    assert root.findtext(
        ".//p:data[@name='https://twinforge.dev/plcopenxml/rockwell-ons']/"
        "StorageOperand",
        namespaces=ns,
    ) == "OneShotStorage"
    assert "Rockwell NOP (intentional no operation)" in result.xml
    assert not any(
        diagnostic.code == "unsupported_rll_rung"
        for diagnostic in result.diagnostics
    )
