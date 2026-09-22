"""SFC connectivity: evidenced grid adjacency and explicit links only."""
from pathlib import Path

import pytest

from twinforge.parsers.control_expert import capture_bytes, capture_file, parse_project, parse_projects


def _chart(xml_body: str):
    data = f'<FEFExchangeFile><SFCProgram><identProgram name="S"/>{xml_body}</SFCProgram></FEFExchangeFile>'
    result = parse_project(capture_bytes(data.encode(), name="connectivity.xef"))
    routine = result.controller.programs["S"].main_routine
    assert routine is not None
    return result, routine.sequential_charts[0]


def test_linear_chain_resolves_through_grid_adjacency_and_a_closing_link():
    result, chart = _chart('''
    <chartSource><networkSFC>
    <step stepType="initialStep" stepName="S0"><objPosition posX="1" posY="1"/></step>
    <transition><objPosition posX="1" posY="2"/></transition>
    <step stepType="step" stepName="S1"><objPosition posX="1" posY="3"/></step>
    <transition><objPosition posX="1" posY="4"/></transition>
    <linkSFC>
    <directedLinkSource objectType="transition"><objPosition posX="1" posY="4"/></directedLinkSource>
    <directedLinkDestination objectType="step"><objPosition posX="1" posY="1"/></directedLinkDestination>
    </linkSFC>
    </networkSFC></chartSource>''')
    assert chart.connectivity_resolved
    assert len(chart.connectivity_edges) == 4
    bases = {tuple(e.source_path + e.destination_path): e.basis for e in chart.connectivity_edges}
    assert list(bases.values()).count("grid_adjacency") == 3
    assert list(bases.values()).count("explicit_link") == 1
    assert not any(d.code.startswith("unresolved_sfc_") or d.code.startswith("ambiguous_sfc_")
                   for d in result.diagnostics)


def test_dead_end_transition_is_diagnosed_and_leaves_chart_unresolved():
    result, chart = _chart('''
    <chartSource><networkSFC>
    <step stepType="initialStep" stepName="S0"><objPosition posX="1" posY="1"/></step>
    <transition><objPosition posX="1" posY="2"/></transition>
    <step stepType="step" stepName="S1"><objPosition posX="1" posY="3"/></step>
    <transition><objPosition posX="1" posY="4"/></transition>
    </networkSFC></chartSource>''')
    assert not chart.connectivity_resolved
    assert sum(d.code == "unresolved_sfc_successor" for d in result.diagnostics) == 1
    # The three resolvable edges upstream of the dead end still resolve independently.
    assert len(chart.connectivity_edges) == 3


def test_position_collision_leaves_both_candidates_unresolved():
    result, chart = _chart('''
    <chartSource><networkSFC>
    <step stepType="initialStep" stepName="S0"><objPosition posX="1" posY="1"/></step>
    <transition><objPosition posX="1" posY="2"/></transition>
    <transition><objPosition posX="1" posY="2"/></transition>
    <step stepType="step" stepName="S1"><objPosition posX="1" posY="3"/></step>
    </networkSFC></chartSource>''')
    assert not chart.connectivity_resolved
    # S0 finds no unique transition at the collided position, and S1 (the chain's
    # end) has no successor of its own: two independent dead ends.
    assert sum(d.code == "unresolved_sfc_successor" for d in result.diagnostics) == 2


def test_selective_branch_and_join_resolve_using_annecy_evidenced_shape():
    # Mirrors the real IUT-GEII-Annecy 02_MAIN.sfc.xml topology: a step diverges
    # via altBranch into two transitions; one continues linearly, the other
    # reaches the shared altJoint through an explicit link whose recorded
    # coordinate differs from the altJoint's own (it lies within its width span).
    result, chart = _chart('''
    <chartSource><networkSFC>
    <step stepType="initialStep" stepName="S0"><objPosition posX="4" posY="1"/></step>
    <transition><objPosition posX="4" posY="2"/></transition>
    <altBranch width="2" relativePos="0"><objPosition posX="4" posY="2"/></altBranch>
    <transition><objPosition posX="5" posY="2"/></transition>
    <step stepType="step" stepName="S_Main"><objPosition posX="4" posY="3"/></step>
    <step stepType="step" stepName="S_Alt"><objPosition posX="5" posY="3"/></step>
    <transition><objPosition posX="4" posY="4"/></transition>
    <altJoint width="2" relativePos="0"><objPosition posX="4" posY="4"/></altJoint>
    <transition><objPosition posX="5" posY="4"/></transition>
    <step stepType="step" stepName="S_Joined"><objPosition posX="4" posY="5"/></step>
    <transition><objPosition posX="4" posY="6"/></transition>
    <linkSFC>
    <directedLinkSource objectType="transition"><objPosition posX="5" posY="4"/></directedLinkSource>
    <directedLinkDestination objectType="altJoint"><objPosition posX="5" posY="4"/></directedLinkDestination>
    </linkSFC>
    <linkSFC>
    <directedLinkSource objectType="transition"><objPosition posX="4" posY="6"/></directedLinkSource>
    <directedLinkDestination objectType="step"><objPosition posX="4" posY="1"/></directedLinkDestination>
    </linkSFC>
    </networkSFC></chartSource>''')
    assert chart.connectivity_resolved
    assert len(chart.connectivity_edges) == 10
    bases = [e.basis for e in chart.connectivity_edges]
    assert bases.count("grid_adjacency") == 8
    assert bases.count("join_indirection") == 1
    assert bases.count("explicit_link") == 1
    # The anchor transition (child index 6) and the linked alt-branch transition
    # (via the altJoint at child index 7) both resolve onward to the same step.
    join_edge = next(e for e in chart.connectivity_edges if e.basis == "join_indirection")
    anchor_edge = next(e for e in chart.connectivity_edges
                        if e.basis == "grid_adjacency" and e.source_path == [0, 6])
    assert join_edge.destination_path == anchor_edge.destination_path
    assert not any(d.code.startswith(("unresolved_sfc_", "ambiguous_sfc_", "unsupported_sfc_"))
                   for d in result.diagnostics)


def test_branch_with_unevidenced_relative_position_is_not_guessed():
    result, chart = _chart('''
    <chartSource><networkSFC>
    <step stepType="initialStep" stepName="S0"><objPosition posX="1" posY="1"/></step>
    <altBranch width="2" relativePos="1"><objPosition posX="1" posY="2"/></altBranch>
    <transition><objPosition posX="1" posY="2"/></transition>
    <transition><objPosition posX="2" posY="2"/></transition>
    </networkSFC></chartSource>''')
    assert not chart.connectivity_resolved
    assert any(d.code == "unsupported_sfc_branch_position" for d in result.diagnostics)
    assert not chart.connectivity_edges


def test_conflicting_plain_adjacency_and_explicit_link_is_ambiguous():
    result, chart = _chart('''
    <chartSource><networkSFC>
    <step stepType="initialStep" stepName="S0"><objPosition posX="1" posY="1"/></step>
    <transition><objPosition posX="1" posY="2"/></transition>
    <step stepType="step" stepName="S1"><objPosition posX="1" posY="3"/></step>
    <transition><objPosition posX="1" posY="4"/></transition>
    <step stepType="step" stepName="S2"><objPosition posX="1" posY="5"/></step>
    <linkSFC>
    <directedLinkSource objectType="transition"><objPosition posX="1" posY="4"/></directedLinkSource>
    <directedLinkDestination objectType="step"><objPosition posX="1" posY="1"/></directedLinkDestination>
    </linkSFC>
    </networkSFC></chartSource>''')
    assert not chart.connectivity_resolved
    assert sum(d.code == "ambiguous_sfc_successor" for d in result.diagnostics) == 1
    # S0->T(1,2), T(1,2)->S1 and S1->T(1,4) still resolve independently.
    assert len(chart.connectivity_edges) == 3


def test_rerun_clears_prior_edges_instead_of_duplicating():
    from twinforge.analysis.sfc_connectivity import resolve_sfc_connectivity
    result, chart = _chart('''
    <chartSource><networkSFC>
    <step stepType="initialStep" stepName="S0"><objPosition posX="1" posY="1"/></step>
    <transition><objPosition posX="1" posY="2"/></transition>
    <step stepType="step" stepName="S1"><objPosition posX="1" posY="3"/></step>
    </networkSFC></chartSource>''')
    assert len(chart.connectivity_edges) == 2
    resolve_sfc_connectivity(result.controller)
    assert len(chart.connectivity_edges) == 2
    assert not chart.connectivity_resolved  # S1 (the chain's end) has no successor.


@pytest.mark.parametrize("filename", ["Escalier_Mecanique.XEF", "escalier_mecanique.zef"])
def test_optional_real_escalator_connectivity_fully_resolves(filename):
    path = Path("reference/control-expert") / filename
    if not path.exists():
        pytest.skip("Local SFC reference unavailable")
    result, = parse_projects(capture_file(path))
    charts = [chart for program in result.controller.programs.values()
              for routine in program.routines.values() for chart in routine.sequential_charts]
    assert len(charts) == 2
    assert all(chart.connectivity_resolved for chart in charts)
    assert not any(d.code.startswith(("unresolved_sfc_", "ambiguous_sfc_", "unsupported_sfc_"))
                   for d in result.diagnostics)


@pytest.mark.parametrize("filename", ["MultiGrafcet_Coordination_V1_2026.XEF", "tsaii_multigrafcet_final_v1.zef"])
def test_optional_real_multigrafcet_connectivity_fully_resolves(filename):
    path = Path("reference/control-expert") / filename
    if not path.exists():
        pytest.skip("Local multi-Grafcet reference unavailable")
    result, = parse_projects(capture_file(path))
    charts = [chart for program in result.controller.programs.values()
              for routine in program.routines.values() for chart in routine.sequential_charts]
    assert len(charts) == 3
    assert all(chart.connectivity_resolved for chart in charts)
    assert not any(d.code.startswith(("unresolved_sfc_", "ambiguous_sfc_", "unsupported_sfc_"))
                   for d in result.diagnostics)


def test_jump_sfc_closes_the_loop_to_a_named_step_within_the_same_network():
    result, chart = _chart('''
    <chartSource><networkSFC>
    <step stepType="initialStep" stepName="S0"><objPosition posX="1" posY="1"/></step>
    <transition><objPosition posX="1" posY="2"/></transition>
    <step stepType="step" stepName="S1"><objPosition posX="1" posY="3"/></step>
    <transition><objPosition posX="1" posY="4"/></transition>
    <jumpSFC stepName="S0"><objPosition posX="1" posY="5"/></jumpSFC>
    </networkSFC></chartSource>''')
    assert chart.connectivity_resolved
    assert len(chart.connectivity_edges) == 4
    bases = {tuple(e.source_path + e.destination_path): e.basis for e in chart.connectivity_edges}
    assert list(bases.values()).count("grid_adjacency") == 3
    assert list(bases.values()).count("named_jump_indirection") == 1
    jump_edge = next(e for e in chart.connectivity_edges if e.basis == "named_jump_indirection")
    assert jump_edge.source_path == [0, 3] and jump_edge.destination_path == [0, 0]  # transition[1,4] -> S0
    assert not any(d.code.startswith(("unresolved_sfc_", "ambiguous_sfc_")) for d in result.diagnostics)


def test_jump_sfc_target_missing_or_ambiguous_is_diagnosed_not_guessed():
    missing_result, missing_chart = _chart('''
    <chartSource><networkSFC>
    <step stepType="initialStep" stepName="S0"><objPosition posX="1" posY="1"/></step>
    <transition><objPosition posX="1" posY="2"/></transition>
    <jumpSFC stepName="NoSuchStep"><objPosition posX="1" posY="3"/></jumpSFC>
    </networkSFC></chartSource>''')
    assert not missing_chart.connectivity_resolved
    assert any(d.code == "unresolved_sfc_successor" for d in missing_result.diagnostics)
    assert len(missing_chart.connectivity_edges) == 1  # S0 -> its transition still resolves independently

    ambiguous_result, ambiguous_chart = _chart('''
    <chartSource><networkSFC>
    <step stepType="initialStep" stepName="S0"><objPosition posX="1" posY="1"/></step>
    <step stepType="step" stepName="S0"><objPosition posX="2" posY="1"/></step>
    <transition><objPosition posX="1" posY="2"/></transition>
    <jumpSFC stepName="S0"><objPosition posX="1" posY="3"/></jumpSFC>
    </networkSFC></chartSource>''')
    assert not ambiguous_chart.connectivity_resolved
    assert any(d.code == "unresolved_sfc_successor" for d in ambiguous_result.diagnostics)
    assert len(ambiguous_chart.connectivity_edges) == 1  # S0 -> its transition still resolves independently


def test_jump_sfc_competing_with_a_plain_adjacent_step_is_ambiguous():
    result, chart = _chart('''
    <chartSource><networkSFC>
    <step stepType="initialStep" stepName="S0"><objPosition posX="1" posY="1"/></step>
    <transition><objPosition posX="1" posY="2"/></transition>
    <step stepType="step" stepName="S1"><objPosition posX="1" posY="3"/></step>
    <jumpSFC stepName="S0"><objPosition posX="1" posY="3"/></jumpSFC>
    </networkSFC></chartSource>''')
    assert not chart.connectivity_resolved
    assert sum(d.code == "ambiguous_sfc_successor" for d in result.diagnostics) == 1


@pytest.mark.parametrize("filename", ["probst_injection_molding_sfc_packaging_robot.xml"])
def test_optional_real_packaging_robot_jump_sfc_resolves(filename):
    # A real, independently authored (Stefan Probst, 2018) demo project's SFC
    # section, sourced via github.com/apexsotjo-blip/control-expert-mcp's
    # tools/lang_refs/. It is a bare section export (SFCExchangeFile), not a
    # whole project (ZEFExchangeFile/FEFExchangeFile), so its real
    # <SFCProgram>/<dataBlock> content is wrapped in a minimal project
    # envelope here -- the same technique _chart() already uses, applied to
    # real rather than synthetic content.
    path = Path("reference/control-expert") / filename
    if not path.exists():
        pytest.skip("Local SFC reference unavailable")
    import re
    raw = path.read_text(encoding="utf-8")
    sfc_match = re.search(r"(<SFCProgram.*?</SFCProgram>)", raw, re.S)
    data_match = re.search(r"(<dataBlock>.*?</dataBlock>)", raw, re.S)
    assert sfc_match is not None and data_match is not None
    sfc_program, data_block = sfc_match.group(1), data_match.group(1)
    wrapped = f'<ZEFExchangeFile><contentHeader name="Packaging_Robot"/>{sfc_program}{data_block}</ZEFExchangeFile>'
    result = parse_project(capture_bytes(wrapped.encode(), name="probst.xef"))
    routine = result.controller.programs["Packaging_Robot"].main_routine
    assert routine is not None
    chart = routine.sequential_charts[0]
    jump_edges = [e for e in chart.connectivity_edges if e.basis == "named_jump_indirection"]
    assert len(jump_edges) == 1
    network = chart.elements[0]
    jump_index = next(i for i, obj in enumerate(network.children) if obj.kind == "step_jump")
    start_robot_index = next(i for i, obj in enumerate(network.children)
                             if obj.kind == "step" and obj.properties.get("name") == "Start_Robot")
    assert jump_edges[0].destination_path == [0, start_robot_index]
    # The chart does not fully resolve end to end: real evidence for jumpSFC
    # is confirmed above, but this chart's altBranch has transitions at only
    # 2 of its declared width=4 columns (a sparser layout than the Annecy
    # evidence this project's alternative-branch rule was built from) -- a
    # separate, pre-existing, correctly conservative limitation, not a
    # regression from this jumpSFC work.
    assert any(d.code == "unsupported_sfc_branch_position" for d in result.diagnostics)
    assert not chart.connectivity_resolved
    assert jump_index > 0  # sanity: the jump element was actually captured
