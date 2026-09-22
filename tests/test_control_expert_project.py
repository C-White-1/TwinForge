"""Neutral mapping contracts using independently authored exchange fixtures."""
from pathlib import Path

import pytest

from twinforge.parsers.control_expert import capture_bytes, capture_file, parse_project, parse_projects


def project(body: str):
    return parse_project(capture_bytes(
        (f'<ZEFExchangeFile><contentHeader name="Example"/>{body}</ZEFExchangeFile>').encode(),
        name="project.xef",
    ))


def test_sections_follow_task_order_not_document_order_and_preserve_st():
    result = project('''
      <logicConf><resource><taskDesc task="MAST" taskType="cyclic" maxExecTime="250">
        <sectionDesc name="second"/><sectionDesc name="FIRST"/>
      </taskDesc></resource></logicConf>
      <program><identProgram name="first" task="MAST"/><STSource>  x := 1;

(* keep *)
</STSource></program>
      <program><identProgram name="second" task="MAST"/><FBDSource><Future/></FBDSource></program>
    ''')
    controller = result.controller
    task = controller.tasks["MAST"]
    assert [p.name for p in task.scheduled_programs] == ["second", "first"]
    assert task.scheduled_program_names == ["second", "FIRST"]
    assert task.watchdog is None
    assert task.metadata["source_task_attributes"]["maxExecTime"] == "250"
    routine = controller.programs["first"].main_routine
    assert routine is not None
    assert routine.structured_text == "  x := 1;\n\n(* keep *)\n"
    assert routine.parent is controller.programs["first"]
    assert controller.programs["first"].parent is controller
    graphical = controller.programs["second"].main_routine
    assert graphical is not None and graphical.language == "FBD"
    assert graphical.ladder_rungs == []
    assert graphical.metadata["task_schedule"] == [{
        "task_name": "MAST", "task_type": "cyclic", "section_index": 0,
        "eligibility": "each_active_task_cycle", "execution_conditions": "not_evaluated",
    }]
    assert routine.metadata["task_schedule"][0]["section_index"] == 1
    assert task.metadata["cycle_policy"] == "successive_cycles_while_active"
    assert any(d.code == "uninterpreted_graphical_logic" for d in result.diagnostics)


def test_variables_preserve_bounds_addresses_initializers_and_unresolved_types():
    result = project('''<dataBlock>
      <variables name="data" typeName="ARRAY[1..4] OF INT" topologicalAddress="%MW200">
        <comment>Four values</comment><instanceElementDesc name="[1]"><value>7</value></instanceElementDesc>
      </variables>
      <variables name="timer" typeName="TIME"><variableInit value="t#10s"/></variables>
      <variables name="custom" typeName="MyType" extra="retain"/>
    </dataBlock>''')
    tags = result.controller.tags
    assert tags["data"].data_type == "ARRAY[1..4] OF INT"
    assert tags["data"].dimensions is None
    assert tags["data"].metadata["source_array_bounds"] == [[1, 4]]
    assert tags["data"].metadata["source_memory_address"] == "%MW200"
    assert tags["data"].alias_for is None
    assert tags["data"].description == "Four values"
    assert tags["timer"].initial_value is None
    assert tags["timer"].metadata["source_initial_values"] == [{"value": "t#10s"}]
    assert tags["custom"].data_type_definition is None
    assert tags["custom"].source_extensions[0].root.attributes["extra"] == "retain"
    assert any(d.code == "unresolved_type" for d in result.diagnostics)
    assert tags["data"].parent is result.controller


def test_conflicting_or_duplicate_names_do_not_silently_bind():
    result = project('''
      <dataBlock><variables name="x" typeName="INT"/><variables name="X" typeName="WORD"/></dataBlock>
      <logicConf><resource><taskDesc task="MAST"><sectionDesc name="dup"/>
        <sectionDesc name="wrong"/><sectionDesc name="absent"/>
      </taskDesc></resource></logicConf>
      <program><identProgram name="dup" task="MAST"/><STSource>a;</STSource></program>
      <program><identProgram name="DUP" task="MAST"/><STSource>b;</STSource></program>
      <program><identProgram name="wrong" task="OTHER"/><STSource>c;</STSource></program>
    ''')
    assert list(result.controller.tags) == ["x"]
    assert result.controller.tasks["MAST"].scheduled_programs == []
    assert sum(d.code == "unresolved_section_reference" for d in result.diagnostics) == 3
    evidence = result.controller.source_extensions[0].root
    assert sum(n.name == "program" for n in evidence.children) == 3


def test_hardware_layout_separates_power_supply_from_the_numbered_slot_scheme():
    result = project(r'''
      <IOConf><PLC><partItem partNumber="CPU" vendorName="Vendor" version="03.00"/>
        <configATS><busATS><rackATS><partItem partNumber="RACK"/>
          <equipInfo topoAddress="\0.0\0"/>
          <moduleATS><partItem partNumber="CPU"/><equipInfo position="1"/></moduleATS>
          <moduleATS><partItem partNumber="ETH"/><equipInfo position="3"/></moduleATS>
          <powerSupply><partItem partNumber="PSU"/><equipInfo position="-1"/></powerSupply>
        </rackATS></busATS></configATS>
      </PLC></IOConf>
    ''')
    controller = result.controller
    assert controller.identity.product_name == "CPU"
    assert controller.identity.vendor is None  # No invented numeric vendor ID.
    chassis = next(iter(controller.chassis.values()))
    # A power supply mounts separately from the numbered slot scheme -- it is
    # neither a slotted module nor "unplaced" (that status is for hardware
    # TwinForge could not resolve at all; this is fully resolved evidence).
    assert [m.catalog for m in chassis.modules.values()] == ["CPU", "ETH"]
    assert [m.catalog for m in chassis.power_supplies] == ["PSU"]
    assert chassis.power_supplies[0].slot is None
    assert chassis.power_supplies[0].parent is chassis
    assert controller.unplaced_modules == []
    assert chassis.modules[1].parent is chassis
    assert chassis.parent is controller
    assert controller.identity.source_extensions[0].root.attributes["version"] == "03.00"


def test_power_supply_missing_identity_is_still_diagnosed():
    result = project(r'''
      <IOConf><PLC><partItem partNumber="CPU"/>
        <configATS><busATS><rackATS><partItem partNumber="RACK"/>
          <equipInfo topoAddress="\0.0\0"/>
          <moduleATS><partItem partNumber="CPU"/><equipInfo position="1"/></moduleATS>
          <powerSupply><equipInfo position="-1"/></powerSupply>
        </rackATS></busATS></configATS>
      </PLC></IOConf>
    ''')
    controller = result.controller
    chassis = next(iter(controller.chassis.values()))
    assert chassis.power_supplies == []
    assert controller.unplaced_modules[0].catalog == ""
    assert any(d.code == "unplaced_hardware" for d in result.diagnostics)


def test_ld_contact_binds_step_state_declared_in_a_different_sfc_section():
    result = project('''
      <logicConf><resource><taskDesc task="MAST" taskType="cyclic">
        <sectionDesc name="Init"/><sectionDesc name="G1"/>
      </taskDesc></resource></logicConf>
      <program><identProgram name="Init" task="MAST"/><LDSource><networkLD>
        <typeLine><contact typeContact="openContact" contactVariableName="G1_0.X"/></typeLine>
        <typeLine><contact typeContact="openContact" contactVariableName="G1_0.X"/></typeLine>
      </networkLD></LDSource></program>
      <SFCProgram><identProgram name="G1" task="MAST"/><chartSource><networkSFC>
        <step stepName="G1_0" stepType="initialStep"/>
        <step stepName="G1_0" stepType="step"/>
      </networkSFC></chartSource></SFCProgram>
    ''')
    ld = result.controller.programs["Init"].main_routine
    assert ld is not None
    first, second = ld.graphical_diagrams[0].objects
    # Both G1_0 declarations make the step name ambiguous project-wide.
    assert first.operand_binding_kind == "ambiguous_step_state"
    assert second.operand_binding_kind == "ambiguous_step_state"
    assert first.target_step_name is None
    assert any(d.code == "ambiguous_contact_step_state" for d in result.diagnostics)


def test_ld_contact_binds_unique_step_state_across_sections():
    result = project('''
      <logicConf><resource><taskDesc task="MAST" taskType="cyclic">
        <sectionDesc name="Init"/><sectionDesc name="G1"/>
      </taskDesc></resource></logicConf>
      <program><identProgram name="Init" task="MAST"/><LDSource><networkLD>
        <typeLine><contact typeContact="openContact" contactVariableName="G1_0.X"/></typeLine>
      </networkLD></LDSource></program>
      <SFCProgram><identProgram name="G1" task="MAST"/><chartSource><networkSFC>
        <step stepName="G1_0" stepType="initialStep"/>
      </networkSFC></chartSource></SFCProgram>
    ''')
    ld = result.controller.programs["Init"].main_routine
    assert ld is not None
    contact = ld.graphical_diagrams[0].objects[0]
    assert contact.operand_binding_kind == "declared_step_state"
    assert contact.target_step_name == "G1_0"
    assert not any(d.code.startswith("unresolved_contact") or d.code.startswith("ambiguous_contact")
                   for d in result.diagnostics)


def test_invalid_input_rejected_and_unrecognized_xml_not_promoted():
    artifact = capture_bytes(b"<Other/>", name="other.xml")
    with pytest.raises(ValueError, match="exchange XML"):
        parse_project(artifact)
    assert parse_projects(artifact) == []
    assert artifact.diagnostics


def test_local_sample_mappings_when_available():
    folder = Path(__file__).resolve().parents[1] / "reference" / "control-expert"
    expected = {
        "cread_reg.zip": (11, 2, 1, 3),
        "cwrite_reg.zip": (13, 2, 1, 3),
        "function15.zip": (22, 4, 1, 3),
        "function2.zip": (21, 3, 1, 3),
        "readvar.zip": (7, 2, 1, 2),
    }
    if not all((folder / name).exists() for name in expected):
        pytest.skip("Five local Control Expert references are not installed")
    for name, counts in expected.items():
        captured = capture_file(folder / name)
        zef = next(m for m in captured.members if m.name.endswith(".zef"))
        results = parse_projects(zef)
        assert len(results) == 1
        result = results[0]
        c = result.controller
        assert (len(c.tags), len(c.programs), len(c.chassis),
                sum(len(r.modules) for r in c.chassis.values())) == counts
        assert len(c.tasks["MAST"].scheduled_programs) == counts[1]
        assert not any(d.code in {"ambiguous_identity", "unresolved_section_reference"}
                       for d in result.diagnostics)
        assert result.artifact.raw_bytes is not None
    # The two independently exported projects in this ZIP must stay separate.
    differing = parse_projects(capture_file(folder / "cwrite_reg.zip"))
    assert sorted(len(p.controller.tags) for p in differing) == [11, 13]


def _section_conditions(body: str, variables: str = ""):
    result = project(f'''{variables}
      <logicConf><resource><taskDesc task="MAST" taskType="cyclic" maxExecTime="250">
        {body}
      </taskDesc></resource></logicConf>
      <program><identProgram name="s" task="MAST"/><STSource>x := 1;</STSource></program>''')
    routine = result.controller.programs["s"].main_routine
    assert routine is not None
    return routine.metadata["task_schedule"][0], result


def test_section_conditions_are_lexical_evidence_not_evaluated():
    entry, result = _section_conditions(
        '<sectionDesc name="s" activationCondition="sim" logicCondition="standard"/>',
        '<dataBlock><variables name="SIM" typeName="BOOL"/></dataBlock>')
    assert entry["section_conditions"] == {
        "activation": {"text": "sim", "binding_kind": "declared_symbol"},
        "logic": {"text": "standard"},
    }
    assert entry["execution_conditions"] == "not_evaluated"
    assert not any(d.code == "unresolved_section_activation_condition" for d in result.diagnostics)


def test_section_activation_direct_address_is_shape_only():
    entry, result = _section_conditions('<sectionDesc name="s" activationCondition="%S13"/>')
    assert entry["section_conditions"]["activation"]["binding_kind"] == "direct_address"
    assert not any(d.code == "unresolved_section_activation_condition" for d in result.diagnostics)


@pytest.mark.parametrize(("text", "variables", "kind"), [
    ("ghost", "", "missing_symbol"),
    ("dup", '<dataBlock><variables name="dup" typeName="BOOL"/><variables name="DUP" typeName="BOOL"/></dataBlock>',
     "ambiguous_symbol"),
    ("a AND b", "", "unresolved_expression"),
])
def test_unresolvable_section_activation_is_diagnosed(text, variables, kind):
    entry, result = _section_conditions(f'<sectionDesc name="s" activationCondition="{text}"/>', variables)
    assert entry["section_conditions"]["activation"] == {"text": text, "binding_kind": kind}
    assert any(d.code == "unresolved_section_activation_condition" and kind in d.message
               for d in result.diagnostics)


def test_real_safety_project_section_conditions_when_available():
    path = Path("reference/control-expert/estradege_m580-safety.xef")
    if not path.exists():
        pytest.skip("reference fixture absent")
    result = parse_project(capture_file(path))
    found = {}
    for program in result.controller.programs.values():
        for routine in program.routines.values():
            for entry in routine.metadata.get("task_schedule", []):
                if "section_conditions" in entry:
                    found[program.name] = entry["section_conditions"]
    activation = {k: v["activation"] for k, v in found.items()}
    # "SIM" exists in this export only as Function Block input parameters, never
    # as a global variable, so it must not bind: the section condition is
    # evidence, and an unresolvable one is diagnosed rather than guessed.
    assert activation["Sim_FBD"] == activation["Sim_ST"] == {"text": "SIM", "binding_kind": "missing_symbol"}
    unresolved = [d for d in result.diagnostics if d.code == "unresolved_section_activation_condition"]
    assert len(unresolved) == 2


def test_function_block_body_condition_never_binds_to_project_tags():
    result = project('''<dataBlock><variables name="run" typeName="BOOL"/></dataBlock>
      <FBSource nameOfFBType="FB1"><FBProgram name="INIT" activationCondition="%S13" logicCondition="standard">
        <STSource>x := 1;</STSource></FBProgram></FBSource>
      <FBSource nameOfFBType="FB2"><FBProgram name="MAIN" activationCondition="run">
        <STSource>x := 1;</STSource></FBProgram></FBSource>''')
    fb1, fb2 = (result.controller.add_on_instructions[n].routines for n in ("FB1", "FB2"))
    assert fb1["FB1"].metadata["section_conditions"] == {
        "activation": {"text": "%S13", "binding_kind": "direct_address"}, "logic": {"text": "standard"}}
    # A same-named global is a different namespace from the block's own.
    assert fb2["FB2"].metadata["section_conditions"]["activation"]["binding_kind"] ==         "function_block_scope_unresolved"


_TWO_RESOURCES = '''
  <dataBlock><variables name="Shared" typeName="BOOL"/><variables name="Both" typeName="INT"/></dataBlock>
  <logicConf>
    <resource resName="process" resIdent="P1">
      <taskDesc task="MAST" taskType="cyclic"><sectionDesc name="a"/></taskDesc>
      <inputParameters><variables name="In1" typeName="BOOL"/></inputParameters>
      <privateLocalVariables><variables name="Both" typeName="INT"/><variables name="Twice" typeName="INT"/>
        <variables name="TWICE" typeName="INT"/></privateLocalVariables>
    </resource>
    <resource resName="safe" resIdent="S1">
      <taskDesc task="SAFE" taskType="periodic"><sectionDesc name="b"/></taskDesc>
      <privateLocalVariables><variables name="In1" typeName="WORD"/></privateLocalVariables>
    </resource>
  </logicConf>
  <program><identProgram name="a" task="MAST"/><FBDSource><networkFBD>
    <FFBBlock instanceName="B" typeName="X"><descriptionFFB>
      <inputVariable formalParameter="P0" effectiveParameter="In1"/>
      <inputVariable formalParameter="P1" effectiveParameter="Shared"/>
      <inputVariable formalParameter="P2" effectiveParameter="Both"/>
      <inputVariable formalParameter="P3" effectiveParameter="Twice"/>
    </descriptionFFB></FFBBlock></networkFBD></FBDSource></program>
  <program><identProgram name="b" task="SAFE"/><FBDSource><networkFBD>
    <FFBBlock instanceName="B" typeName="X"><descriptionFFB>
      <inputVariable formalParameter="P0" effectiveParameter="In1"/>
      <inputVariable formalParameter="P1" effectiveParameter="Both"/>
    </descriptionFFB></FFBBlock></networkFBD></FBDSource></program>
'''


def test_resource_variables_form_separate_namespaces_and_never_join_controller_tags():
    result = project(_TWO_RESOURCES)
    controller = result.controller
    assert set(controller.tags) == {"Shared", "Both"}  # resource variables are not merged in
    process, safe = controller.resources["process"], controller.resources["safe"]
    assert process.identifier == "P1" and process.task_names == ["MAST"]
    assert set(process.tags) == {"In1", "Both", "Twice"} and safe.task_names == ["SAFE"]
    assert process.tags["In1"].data_type == "BOOL" and safe.tags["In1"].data_type == "WORD"
    assert process.tags["In1"].metadata["declaration_scope"] == "resource"
    assert controller.tasks["MAST"].metadata["resource"] == "process"
    assert process.ambiguous_names == {"twice"}  # declared twice in one resource: never bound to either


def _pin_bindings(result, program):
    diagram = result.controller.programs[program].main_routine.graphical_diagrams[0]
    return {pin.name: (pin.binding_kind, pin.target_tag) for pin in diagram.objects[0].pins}


def test_programs_bind_to_their_own_resource_and_ambiguous_scopes_are_never_guessed():
    result = project(_TWO_RESOURCES)
    a = _pin_bindings(result, "a")
    b = _pin_bindings(result, "b")
    process, safe = result.controller.resources["process"], result.controller.resources["safe"]
    assert a["P0"] == ("declared_symbol", process.tags["In1"])  # not safe's same-named WORD
    assert b["P0"] == ("declared_symbol", safe.tags["In1"])
    assert a["P1"] == ("declared_symbol", result.controller.tags["Shared"])  # controller scope still visible
    assert a["P2"][0] == "ambiguous_symbol"  # declared in the controller scope and in this resource
    assert a["P3"][0] == "ambiguous_symbol"  # declared twice within the resource
    assert b["P1"] == ("declared_symbol", result.controller.tags["Both"])  # safe never sees process's "Both"


def test_real_safety_project_resources_when_available():
    path = Path("reference/control-expert/estradege_m580-safety.xef")
    if not path.exists():
        pytest.skip("reference fixture absent")
    controller = parse_project(capture_file(path)).controller
    assert {name: len(r.tags) for name, r in controller.resources.items()} == {"process": 731, "safe": 150}
    assert all(not r.ambiguous_names for r in controller.resources.values())
    assert {t.name: t.metadata["resource"] for t in controller.tasks.values()} == {"MAST": "process", "SAFE": "safe"}
    assert controller.tags == {}  # this export has no controller-level variables


@pytest.mark.parametrize(("type_name", "lexical", "expected"), [
    ("BOOL", "TRUE", True),
    ("BOOL", "false", False),
    ("BOOL", "1", True),
    ("BOOL", "0", False),
    ("EBOOL", "TRUE", True),
    ("INT", "89", 89),
    ("INT", "-5", -5),
    ("UDINT", "16#0000_0001", 1),
    ("WORD", "2#0000_0100", 4),
    ("REAL", "123.4", 123.4),
    ("REAL", "-5.0", -5.0),
])
def test_scalar_initial_values_promote_by_declared_type(type_name, lexical, expected):
    result = project(f'''<dataBlock>
      <variables name="v" typeName="{type_name}"><variableInit value="{lexical}"/></variables>
    </dataBlock>''')
    tag = result.controller.tags["v"]
    assert tag.initial_value is not None
    assert tag.initial_value.value == expected
    assert tag.initial_value.data_type == type_name
    assert tag.initial_value.lexical_value == lexical
    assert not any(d.code == "uninterpreted_initial_value" for d in result.diagnostics)


@pytest.mark.parametrize(("type_name", "lexical"), [
    ("TIME", "t#10s"),  # no duration conversion factor is invented
    ("BOOL", "2"),  # not TRUE/FALSE/0/1
    ("INT", "1.5"),  # not an integer literal shape
    ("INT", "abc"),  # not a literal at all
    ("REAL", "16#FF"),  # a based literal is not a REAL shape
    ("STRING", "'hi'"),  # not a promotable type family
]) 
def test_scalar_initial_values_that_do_not_promote_stay_lexical(type_name, lexical):
    result = project(f'''<dataBlock>
      <variables name="v" typeName="{type_name}"><variableInit value="{lexical}"/></variables>
    </dataBlock>''')
    tag = result.controller.tags["v"]
    assert tag.initial_value is None
    assert tag.metadata["source_initial_values"] == [{"value": lexical}]
    assert any(d.code == "uninterpreted_initial_value" for d in result.diagnostics)


def test_multiple_initializers_on_one_tag_are_never_guessed_at():
    # Not evidenced in the real corpus (always exactly one), but stays
    # unpromoted rather than picking either value if it ever occurs.
    result = project('''<dataBlock>
      <variables name="v" typeName="INT"><variableInit value="1"/><variableInit value="2"/></variables>
    </dataBlock>''')
    tag = result.controller.tags["v"]
    assert tag.initial_value is None
    assert tag.metadata["source_initial_values"] == [{"value": "1"}, {"value": "2"}]
    assert any(d.code == "uninterpreted_initial_value" for d in result.diagnostics)


def test_real_fixtures_promote_scalar_initial_values_when_available():
    import glob
    paths = glob.glob("reference/control-expert/*")
    if not any(Path(p).exists() for p in paths):
        pytest.skip("reference fixtures absent")
    promoted, unpromoted = [], []
    for path in paths:
        if not path.lower().endswith((".xef", ".zef", ".zip")):
            continue
        for result in parse_projects(capture_file(Path(path))):
            controller = result.controller
            tags = list(controller.tags.values())
            for resource in controller.resources.values():
                tags += list(resource.tags.values())
            for tag in tags:
                if not tag.metadata.get("source_initial_values"):
                    continue
                (promoted if tag.initial_value is not None else unpromoted).append(tag.data_type)
    assert len(promoted) == 21
    assert set(promoted) == {"REAL", "INT", "BOOL"}
    assert set(unpromoted) == {"TIME"}
