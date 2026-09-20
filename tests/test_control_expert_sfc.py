"""Independently authored sequential-chart evidence fixtures."""
from pathlib import Path

import pytest

from twinforge.parsers.control_expert import capture_bytes, capture_file, parse_project, parse_projects


def test_chart_schedule_lexical_values_unknowns_and_local_sources():
    data = b'''<FEFExchangeFile>
    <logicConf><resource><taskDesc task="MAST" taskType="cyclic">
    <sectionDesc name="sequence"/></taskDesc></resource></logicConf>
    <SFCProgram><identProgram name="Sequence" task="MAST"/>
    <chartSource name="Main"><networkSFC>
    <step stepName="Idle" stepType="initialStep"><action qualifier="N">
    <actionName><variableName>ready</variableName></actionName></action>
    <literals min=""/></step>
    <transition><transitionCondition invertLogic="false"><sectionName>Advance</sectionName>
    </transitionCondition></transition>
    <linkSFC><gridObjPosition posX="0.5" posY="2.50"/></linkSFC>
    <Future custom="keep"><Payload>opaque</Payload></Future>
    </networkSFC></chartSource>
    <transitionSource name="Advance"><STSource>  go AND ready\n</STSource></transitionSource>
    <transitionSource name="Advance"><STSource>different</STSource></transitionSource>
    </SFCProgram></FEFExchangeFile>'''
    result = parse_project(capture_bytes(data, name="test.xef"))
    controller = result.controller
    routine = controller.programs["Sequence"].main_routine
    assert routine is not None and routine.language == "SFC"
    assert [p.name for p in controller.tasks["MAST"].scheduled_programs] == ["Sequence"]
    assert list(controller.programs) == ["Sequence"]
    chart = routine.sequential_charts[0]
    assert not chart.connectivity_resolved and not chart.execution_resolved
    step, transition, link, unknown = chart.elements[0].children
    assert step.properties == {"name": "Idle", "source_step_type": "initialStep"}
    assert step.children[1].properties == {"minimum": ""}
    assert transition.children[0].children[0].text == "Advance"
    assert link.children[0].properties == {"x": "0.5", "y": "2.50"}
    assert unknown.kind == "unknown"
    assert unknown.source_extensions[0].root.attributes == {"custom": "keep"}
    assert unknown.children[0].text == "opaque"
    assert len(chart.transition_definitions) == 2  # No silent duplicate-name overwrite.
    assert chart.transition_definitions[0].children[0].text == "  go AND ready\n"
    assert not any(d.code == "unresolved_section_reference" for d in result.diagnostics)
    assert any(d.code == "uninterpreted_sfc_execution" for d in result.diagnostics)


@pytest.mark.parametrize("filename", ["Escalier_Mecanique.XEF", "escalier_mecanique.zef"])
def test_optional_real_sfc_sections(filename):
    path = Path("reference/control-expert") / filename
    if not path.exists():
        pytest.skip("Local SFC reference unavailable")
    result, = parse_projects(capture_file(path))
    assert len(result.controller.programs) == 6
    assert not any(d.code == "unresolved_section_reference" for d in result.diagnostics)
    charts = [chart for program in result.controller.programs.values()
              for routine in program.routines.values() for chart in routine.sequential_charts]
    assert len(charts) == 2
    objects = [e for chart in charts for network in chart.elements for e in network.children]
    assert sum(e.kind == "step" for e in objects) == 5
    assert sum(e.kind == "transition" for e in objects) == 6
    assert sum(e.kind == "action" for e in objects for e in e.children) == 10


def test_transition_references_are_local_and_duplicates_never_choose_first():
    sections = ""
    for name, definitions in [("A", '<transitionSource name="Go"><STSource>TRUE</STSource></transitionSource>'),
                              ("B", ""),
                              ("C", '<transitionSource name="Go"/><transitionSource name="GO"/>')]:
        sections += (f'<SFCProgram><identProgram name="{name}"/>'
                     '<chartSource><networkSFC><transition><transitionCondition>'
                     '<sectionName>go</sectionName></transitionCondition></transition>'
                     '</networkSFC></chartSource>' + definitions + '</SFCProgram>')
    result = parse_project(capture_bytes(('<FEFExchangeFile>' + sections + '</FEFExchangeFile>').encode(), name="local.xef"))
    references = []
    for program in result.controller.programs.values():
        routine = program.main_routine
        assert routine is not None
        chart = routine.sequential_charts[0]
        references.append(chart.elements[0].children[0].children[0].children[0])
        assert not chart.execution_resolved and not chart.connectivity_resolved
    assert [r.reference_status for r in references] == ["resolved", "missing", "ambiguous"]
    assert [r.target_definition_index for r in references] == [0, None, None]
    assert sum(d.code == "unresolved_sfc_transition_reference" for d in result.diagnostics) == 2
    assert sum(d.code == "duplicate_sfc_definition" for d in result.diagnostics) == 2


@pytest.mark.parametrize("filename", ["MultiGrafcet_Coordination_V1_2026.XEF", "tsaii_multigrafcet_final_v1.zef"])
def test_optional_multigrafcet_preserves_member_expressions_and_none_qualifier(filename):
    path = Path("reference/control-expert") / filename
    if not path.exists():
        pytest.skip("Local multi-Grafcet reference unavailable")
    result, = parse_projects(capture_file(path))
    assert len(result.controller.programs) == 8
    assert result.controller.tasks["MAST"].task_type == "periodic"
    elements = []

    def visit(element):
        elements.append(element)
        for child in element.children:
            visit(child)

    for program in result.controller.programs.values():
        for routine in program.routines.values():
            for chart in routine.sequential_charts:
                for element in chart.elements:
                    visit(element)
    assert sum(e.kind == "step" for e in elements) == 10
    assert sum(e.kind == "transition" for e in elements) == 10
    assert any(e.kind == "action" and e.properties.get("qualifier") == "NONE" for e in elements)
    assert any(e.kind == "variable_reference" and e.text == "Tempo1.Q" and e.reference_status is None for e in elements)
    assert not any(d.code == "unresolved_sfc_transition_reference" for d in result.diagnostics)


@pytest.mark.parametrize("extra,object_type,x,status", [
    ("", "step", "1", "resolved"),
    ('<step><objPosition posX="1" posY="2"/></step>', "step", "1", "ambiguous"),
    ("", "step", "9", "missing"),
    ("", "future", "1", "unsupported_type"),
    ("", "step", "", "invalid_position"),
])
def test_explicit_link_endpoints_use_type_and_network_local_position(extra, object_type, x, status):
    data = f'''<FEFExchangeFile><SFCProgram><identProgram name="S"/>
    <chartSource><networkSFC>
    <step><objPosition posX="1" posY="2"/></step>
    <transition><objPosition posX="1" posY="2"/></transition>{extra}
    <linkSFC>
    <directedLinkSource objectType="transition"><objPosition posX="1" posY="2"/></directedLinkSource>
    <directedLinkDestination objectType="{object_type}"><objPosition posX="{x}" posY="2"/></directedLinkDestination>
    <gridObjPosition posX="0.5" posY="7.50"/>
    </linkSFC></networkSFC>
    <networkSFC><step><objPosition posX="9" posY="2"/></step></networkSFC>
    </chartSource></SFCProgram></FEFExchangeFile>'''
    result = parse_project(capture_bytes(data.encode(), name="links.xef"))
    routine = result.controller.programs["S"].main_routine
    assert routine is not None
    chart = routine.sequential_charts[0]
    link = chart.elements[0].children[-1]
    source, destination, route = link.children
    assert source.target_element_path == [0, 1]
    assert destination.reference_status == status
    assert destination.target_element_path == ([0, 0] if status == "resolved" else None)
    assert route.properties == {"x": "0.5", "y": "7.50"}
    assert not chart.connectivity_resolved and not chart.execution_resolved
    assert any(d.code == "unresolved_sfc_link_endpoint" for d in result.diagnostics) == (status != "resolved")


def test_missing_and_duplicate_endpoint_roles_are_diagnosed():
    data = b'''<FEFExchangeFile><SFCProgram><identProgram name="S"/>
    <chartSource><networkSFC><linkSFC><directedLinkSource/><directedLinkSource/>
    </linkSFC></networkSFC></chartSource></SFCProgram></FEFExchangeFile>'''
    result = parse_project(capture_bytes(data, name="roles.xef"))
    assert sum(d.code == "invalid_sfc_link_endpoint_count" for d in result.diagnostics) == 2


def test_variable_binding_preserves_expressions_and_rejects_ambiguous_declarations():
    from twinforge.analysis.sequential_bindings import resolve_sequential_bindings
    from twinforge.schema.control_expert.expressions import EXPRESSION_SPEC

    expressions = [" ready ", "dup", "missing", "timer.Q", ""]
    actions = "".join('<action qualifier="NONE"><actionName><variableName>' + value +
                      '</variableName></actionName></action>' for value in expressions)
    data = ('<FEFExchangeFile><dataBlock><variables name="Ready" typeName="BOOL"/>'
            '<variables name="dup" typeName="BOOL"/><variables name="DUP" typeName="BOOL"/>'
            '</dataBlock><SFCProgram><identProgram name="S"/><chartSource><networkSFC><step>'
            + actions + '</step></networkSFC></chartSource></SFCProgram></FEFExchangeFile>')
    result = parse_project(capture_bytes(data.encode(), name="symbols.xef"))
    routine = result.controller.programs["S"].main_routine
    assert routine is not None
    step = routine.sequential_charts[0].elements[0].children[0]
    refs = [action.children[0].children[0] for action in step.children]
    assert [e.binding_kind for e in refs] == ["declared_symbol", "ambiguous_symbol", "missing_symbol",
                                            "unresolved_member", "unresolved_expression"]
    assert refs[0].text == " ready " and refs[0].target_symbol_name == "Ready"
    assert all(e.target_symbol_name is None for e in refs[1:])
    assert any(d.code == "sfc_ambiguous_symbol" for d in result.diagnostics)
    result.controller.tags.clear()
    resolve_sequential_bindings(result.controller, identifier_pattern=EXPRESSION_SPEC.identifier)
    assert refs[0].target_symbol_name is None and refs[0].binding_kind == "missing_symbol"


@pytest.mark.parametrize("duplicate,expected", [(False, "declared_member"), (True, "unresolved_member")])
def test_members_require_unique_library_interface(duplicate, expected):
    interface = ('<EFBSource nameOfEFBType="Timer"><ExternalToolsOnly><outputParameters>'
                 '<variables name="Q" typeName="BOOL"/></outputParameters></ExternalToolsOnly></EFBSource>')
    data = ('<FEFExchangeFile>' + interface * (2 if duplicate else 1) +
            '<dataBlock><variables name="Clock" typeName="Timer"/></dataBlock>'
            '<SFCProgram><identProgram name="S"/><chartSource><networkSFC><transition>'
            '<transitionCondition><variableName>clock.q</variableName></transitionCondition>'
            '</transition></networkSFC></chartSource></SFCProgram></FEFExchangeFile>')
    result = parse_project(capture_bytes(data.encode(), name="member.xef"))
    routine = result.controller.programs["S"].main_routine
    assert routine is not None
    ref = routine.sequential_charts[0].elements[0].children[0].children[0].children[0]
    assert ref.binding_kind == expected
    assert ref.member_data_type == (None if duplicate else "BOOL")
    assert ref.target_member_name == (None if duplicate else "Q")
    assert len(result.library_interfaces) == (2 if duplicate else 1)
