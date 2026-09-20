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


def test_hardware_layout_keeps_special_positions_and_cpu_evidence():
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
    assert [m.catalog for m in chassis.modules.values()] == ["CPU", "ETH"]
    assert controller.unplaced_modules[0].catalog == "PSU"
    assert controller.unplaced_modules[0].slot is None
    assert chassis.modules[1].parent is chassis
    assert chassis.parent is controller
    assert controller.identity.source_extensions[0].root.attributes["version"] == "03.00"


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
