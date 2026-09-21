from pathlib import Path

import pytest

from twinforge.analysis.execution_order import resolve_fbd_execution_order
from twinforge.model import (
    Controller, GraphicalDiagram, GraphicalLink, GraphicalLinkEndpoint, GraphicalObject, GraphicalPin,
    GraphicalVariableReferences, Identity, LadderPosition, Program, Routine,
)
from twinforge.parsers.control_expert import capture_file, parse_projects


def _diagram(language="FBD", *, objects, shared_variables=(), links=()):
    diagram = GraphicalDiagram(language=language, objects=list(objects))
    diagram.shared_variables.extend(shared_variables)
    diagram.links.extend(links)
    return diagram


def _pin(name, direction, *, binding_kind="declared_symbol"):
    return GraphicalPin(name=name, direction=direction, binding_kind=binding_kind)


def _link(source_index, destination_index, *, resolved=True):
    return GraphicalLink(
        source=GraphicalLinkEndpoint(status="resolved" if resolved else "missing_pin", object_index=source_index),
        destination=GraphicalLinkEndpoint(status="resolved", object_index=destination_index),
    )


def _block(row, column, **kwargs):
    obj = GraphicalObject(kind="block", **kwargs)
    obj.position = LadderPosition(column=column, row=row)
    return obj


def _controller_with(diagram):
    controller = Controller(name="C", identity=Identity())
    program = Program(name="P")
    routine = Routine(name="R")
    routine.graphical_diagrams.append(diagram)
    program.add_routine(routine)
    controller.add_program(program)
    return controller


def test_shared_variable_chain_does_not_establish_vendor_order():
    writer = GraphicalObject(kind="block", type_name="ADDR", pins=[_pin("OUT", "output")])
    reader = GraphicalObject(kind="block", type_name="READ_VAR", pins=[_pin("ADR", "input")])
    diagram = _diagram(objects=[reader, writer], shared_variables=[
        GraphicalVariableReferences("ipaddress", input_pins=[(0, 0)], output_pins=[(1, 0)]),
    ])
    controller = _controller_with(diagram)
    issues = resolve_fbd_execution_order(controller)
    assert issues == []
    assert not diagram.execution_order_resolved
    assert diagram.execution_order == []
    assert diagram.execution_order_basis is None


def test_self_referencing_pin_does_not_block_a_real_cross_block_edge():
    # Mirrors the real readvar.zip pattern: a block's own EN and ENO share a
    # name, which must not be mistaken for an ordering constraint on itself.
    first = GraphicalObject(kind="block", type_name="ADDR", pins=[
        _pin("EN", "input"), _pin("ENO", "output"), _pin("OUT", "output"),
    ])
    second = GraphicalObject(kind="block", type_name="READ_VAR", pins=[_pin("ADR", "input")])
    diagram = _diagram(objects=[first, second], shared_variables=[
        GraphicalVariableReferences("sendmsg", input_pins=[(0, 0)], output_pins=[(0, 1)]),
        GraphicalVariableReferences("ipaddress", input_pins=[(1, 0)], output_pins=[(0, 2)]),
    ])
    controller = _controller_with(diagram)
    resolve_fbd_execution_order(controller)
    assert not diagram.execution_order_resolved
    assert diagram.execution_order == []


def test_multiple_writers_reported_ambiguous_and_left_unresolved():
    a = GraphicalObject(kind="block", type_name="A", pins=[_pin("OUT", "output")])
    b = GraphicalObject(kind="block", type_name="B", pins=[_pin("OUT", "output")])
    c = GraphicalObject(kind="block", type_name="C", pins=[_pin("IN", "input")])
    diagram = _diagram(objects=[a, b, c], shared_variables=[
        GraphicalVariableReferences("shared", input_pins=[(2, 0)], output_pins=[(0, 0), (1, 0)]),
    ])
    controller = _controller_with(diagram)
    issues = resolve_fbd_execution_order(controller)
    assert [(i.code) for i in issues] == ["ambiguous_block_order"]
    assert not diagram.execution_order_resolved


def test_cycle_left_unresolved_without_a_claimed_order():
    a = GraphicalObject(kind="block", type_name="A", pins=[_pin("IN", "input"), _pin("OUT", "output")])
    b = GraphicalObject(kind="block", type_name="B", pins=[_pin("IN", "input"), _pin("OUT", "output")])
    diagram = _diagram(objects=[a, b], shared_variables=[
        GraphicalVariableReferences("x", input_pins=[(1, 0)], output_pins=[(0, 1)]),
        GraphicalVariableReferences("y", input_pins=[(0, 0)], output_pins=[(1, 1)]),
    ])
    controller = _controller_with(diagram)
    issues = resolve_fbd_execution_order(controller)
    assert issues == []
    assert not diagram.execution_order_resolved
    assert diagram.execution_order == []


def test_execution_override_present_leaves_order_unresolved():
    a = GraphicalObject(kind="block", type_name="A", pins=[_pin("OUT", "output")], execution_after=".1")
    b = GraphicalObject(kind="block", type_name="B", pins=[_pin("IN", "input")])
    diagram = _diagram(objects=[a, b], shared_variables=[
        GraphicalVariableReferences("x", input_pins=[(1, 0)], output_pins=[(0, 0)]),
    ])
    controller = _controller_with(diagram)
    resolve_fbd_execution_order(controller)
    assert not diagram.execution_order_resolved


def test_unresolved_pin_binding_leaves_order_unresolved():
    a = GraphicalObject(kind="block", type_name="A", pins=[_pin("OUT", "output")])
    b = GraphicalObject(kind="block", type_name="B", pins=[_pin("IN", "input", binding_kind="missing_symbol")])
    diagram = _diagram(objects=[a, b], shared_variables=[
        GraphicalVariableReferences("x", input_pins=[(1, 0)], output_pins=[(0, 0)]),
    ])
    controller = _controller_with(diagram)
    resolve_fbd_execution_order(controller)
    assert not diagram.execution_order_resolved


def test_excluded_diagram_is_skipped_even_when_otherwise_resolvable():
    a = GraphicalObject(kind="block", type_name="A", pins=[_pin("OUT", "output")])
    b = GraphicalObject(kind="block", type_name="B", pins=[_pin("IN", "input")])
    diagram = _diagram(objects=[a, b], shared_variables=[
        GraphicalVariableReferences("x", input_pins=[(1, 0)], output_pins=[(0, 0)]),
    ])
    controller = _controller_with(diagram)
    resolve_fbd_execution_order(controller, excluded=frozenset({("P", "R", 0)}))
    assert not diagram.execution_order_resolved


def test_ladder_diagrams_are_not_touched():
    a = GraphicalObject(kind="block", type_name="A", pins=[_pin("OUT", "output")])
    b = GraphicalObject(kind="block", type_name="B", pins=[_pin("IN", "input")])
    diagram = _diagram(language="LD", objects=[a, b], shared_variables=[
        GraphicalVariableReferences("x", input_pins=[(1, 0)], output_pins=[(0, 0)]),
    ])
    controller = _controller_with(diagram)
    resolve_fbd_execution_order(controller)
    assert not diagram.execution_order_resolved
    assert diagram.execution_order_basis is None


def test_disconnected_and_partially_constrained_blocks_have_no_order():
    for groups in [[], [GraphicalVariableReferences("x", input_pins=[(1, 0)], output_pins=[(0, 0)])]]:
        diagram = _diagram(objects=[GraphicalObject(kind="block", type_name=name)
                                    for name in ("A", "B", "C")], shared_variables=groups)
        resolve_fbd_execution_order(_controller_with(diagram))
        assert diagram.execution_order == []
        assert not diagram.execution_order_resolved
        assert diagram.execution_order_basis is None


def test_rerun_clears_legacy_inferred_order_even_when_excluded():
    diagram = _diagram(objects=[GraphicalObject(kind="block"), GraphicalObject(kind="block")])
    diagram.execution_order = [1, 0]
    diagram.execution_order_resolved = True
    diagram.execution_order_basis = "shared_variable_dataflow"
    resolve_fbd_execution_order(_controller_with(diagram), excluded=frozenset({("P", "R", 0)}))
    assert diagram.execution_order == []
    assert not diagram.execution_order_resolved
    assert diagram.execution_order_basis is None


def test_evidenced_single_block_order_is_preserved():
    diagram = _diagram(objects=[GraphicalObject(kind="block")])
    diagram.execution_order = [0]
    diagram.execution_order_resolved = True
    diagram.execution_order_basis = "single_block"
    resolve_fbd_execution_order(_controller_with(diagram))
    assert diagram.execution_order == [0]
    assert diagram.execution_order_resolved


def test_project_inspection_keeps_shared_chain_order_unresolved(tmp_path):
    from io import StringIO
    import json
    from twinforge.cli.control_expert import inspect_control_expert

    path = tmp_path / "chain.xef"
    path.write_text('<FEFExchangeFile><contentHeader name="Example"/>'
                    '<dataBlock><variables name="shared" typeName="INT"/></dataBlock>'
                    '<program><identProgram name="P"/><FBDSource><networkFBD>'
                    '<FFBBlock typeName="Writer"><descriptionFFB>'
                    '<outputVariable formalParameter="OUT" effectiveParameter="shared"/>'
                    '</descriptionFFB></FFBBlock><FFBBlock typeName="Reader"><descriptionFFB>'
                    '<inputVariable formalParameter="IN" effectiveParameter="shared"/>'
                    '</descriptionFFB></FFBBlock></networkFBD></FBDSource></program></FEFExchangeFile>')
    output = StringIO()
    inspect_control_expert(path, output_format="json", stdout=output)
    project = json.loads(output.getvalue())["projects"][0]
    diagram = project["programs"][0]["routines"][0]["diagrams"][0]
    assert diagram["shared_variables"][0]["symbol_name"] == "shared"
    assert diagram["execution_order"] == []
    assert diagram["execution_order_resolved"] is False
    assert diagram["execution_order_basis"] is None
    assert sum(d["code"] == "unresolved_block_order" for d in project["diagnostics"]) == 1


def test_explicit_link_resolves_a_two_level_chain_matching_the_documented_rule():
    # No-input block first, then the block that depends on it -- the FAQ's
    # own worked example shape.
    a = _block(0, 0, type_name="A", pins=[_pin("OUT", "output")])
    b = _block(1, 0, type_name="B", pins=[_pin("IN", "input")])
    diagram = _diagram(objects=[a, b], links=[_link(0, 1)])
    resolve_fbd_execution_order(_controller_with(diagram))
    assert diagram.execution_order_resolved
    assert diagram.execution_order == [0, 1]
    assert diagram.execution_order_basis == "documented_dependency_order"


def test_dependency_overrides_position_even_when_positioned_above():
    # Mirrors the FAQ's own example: "FFB 13 will be executed before the 11
    # that is above" -- a block positioned higher still executes after
    # something it depends on.
    below = _block(10, 0, type_name="SOURCE", pins=[_pin("OUT", "output")])
    above = _block(0, 0, type_name="DEPENDENT", pins=[_pin("IN", "input")])
    diagram = _diagram(objects=[above, below], links=[_link(1, 0)])
    resolve_fbd_execution_order(_controller_with(diagram))
    assert diagram.execution_order == [1, 0]  # "below" (source) first, despite its row.


def test_independent_blocks_execute_in_position_order():
    first = _block(0, 0, type_name="A")
    second = _block(5, 0, type_name="B")
    third = _block(2, 0, type_name="C")
    diagram = _diagram(objects=[first, second, third])
    resolve_fbd_execution_order(_controller_with(diagram))
    assert diagram.execution_order_resolved
    assert diagram.execution_order == [0, 2, 1]  # Row order: first(0), third(2), second(5).


def test_deep_chain_resolves_via_full_topological_sort():
    # A -> B -> C -> D -> E, five levels: proves this is a genuine multilevel
    # topological sort, not just the FAQ's literal two-bucket wording.
    blocks = [_block(i, 0, type_name=name, pins=[_pin("IN", "input"), _pin("OUT", "output")])
              for i, name in enumerate("ABCDE")]
    links = [_link(i, i + 1) for i in range(4)]
    diagram = _diagram(objects=blocks, links=links)
    resolve_fbd_execution_order(_controller_with(diagram))
    assert diagram.execution_order_resolved
    assert diagram.execution_order == [0, 1, 2, 3, 4]
    assert diagram.execution_order_basis == "documented_dependency_order"


def test_link_cycle_is_diagnosed_not_guessed():
    a = _block(0, 0, type_name="A", pins=[_pin("IN", "input"), _pin("OUT", "output")])
    b = _block(1, 0, type_name="B", pins=[_pin("IN", "input"), _pin("OUT", "output")])
    diagram = _diagram(objects=[a, b], links=[_link(0, 1), _link(1, 0)])
    issues = resolve_fbd_execution_order(_controller_with(diagram))
    assert [i.code for i in issues] == ["cyclic_block_dependency"]
    assert not diagram.execution_order_resolved
    assert diagram.execution_order == []


def test_unresolved_link_disqualifies_the_whole_diagram():
    a = _block(0, 0, type_name="A", pins=[_pin("OUT", "output")])
    b = _block(1, 0, type_name="B", pins=[_pin("IN", "input")])
    diagram = _diagram(objects=[a, b], links=[_link(0, 1, resolved=False)])
    resolve_fbd_execution_order(_controller_with(diagram))
    assert not diagram.execution_order_resolved


def test_unrelated_unresolved_pin_no_longer_blocks_link_based_order():
    # An unresolved *symbol* on an unrelated pin says nothing about whether
    # an explicit block-to-block wire is trustworthy.
    a = _block(0, 0, type_name="A", pins=[_pin("OUT", "output")])
    b = _block(1, 0, type_name="B", pins=[
        _pin("IN", "input"), _pin("X", "input", binding_kind="missing_symbol"),
    ])
    diagram = _diagram(objects=[a, b], links=[_link(0, 1)])
    resolve_fbd_execution_order(_controller_with(diagram))
    assert diagram.execution_order_resolved
    assert diagram.execution_order == [0, 1]


def test_shared_variable_without_a_matching_link_still_blocks_resolution():
    # Even with the unresolved-pin gate loosened, unlinked shared-variable
    # dataflow (the withdrawn shared_variable_dataflow pattern) must still
    # disqualify resolution -- proven real in the M580 safety corpus.
    a = _block(0, 0, type_name="A", pins=[_pin("OUT", "output")])
    b = _block(1, 0, type_name="B", pins=[_pin("IN", "input")])
    diagram = _diagram(objects=[a, b], shared_variables=[
        GraphicalVariableReferences("x", input_pins=[(1, 0)], output_pins=[(0, 0)]),
    ])
    resolve_fbd_execution_order(_controller_with(diagram))
    assert not diagram.execution_order_resolved


def test_ambiguous_block_order_still_checked_when_pins_are_otherwise_clean():
    a = _block(0, 0, type_name="A", pins=[_pin("OUT", "output")])
    b = _block(1, 0, type_name="B", pins=[_pin("OUT", "output")])
    c = _block(2, 0, type_name="C", pins=[_pin("IN", "input")])
    diagram = _diagram(objects=[a, b, c], shared_variables=[
        GraphicalVariableReferences("shared", input_pins=[(2, 0)], output_pins=[(0, 0), (1, 0)]),
    ])
    issues = resolve_fbd_execution_order(_controller_with(diagram))
    assert [i.code for i in issues] == ["ambiguous_block_order"]
    assert not diagram.execution_order_resolved


def _assert_order_respects_every_link(diagram):
    blocks = {i for i, obj in enumerate(diagram.objects) if obj.kind == "block"}
    assert set(diagram.execution_order) == blocks  # Every block placed exactly once.
    rank = {block: position for position, block in enumerate(diagram.execution_order)}
    for link in diagram.links:
        if link.source.status == "resolved" and link.destination.status == "resolved":
            source, destination = link.source.object_index, link.destination.object_index
            if source in blocks and destination in blocks:
                assert rank[source] < rank[destination]


@pytest.mark.parametrize("filename", ["estradege_m580-safety.xef"])
def test_optional_real_m580_safety_execution_order(filename):
    path = Path(__file__).resolve().parents[1] / "reference" / "control-expert" / filename
    if not path.exists():
        pytest.skip("Local M580 safety reference unavailable")
    result, = parse_projects(capture_file(path))
    controller = result.controller

    # Every program-scoped FBD diagram resolves, as before.
    program_diagrams = [d for program in controller.programs.values() for routine in program.routines.values()
                         for d in routine.graphical_diagrams if d.language == "FBD"]
    assert len(program_diagrams) == 22
    assert all(d.execution_order_resolved for d in program_diagrams)
    for d in program_diagrams:
        assert d.execution_order_basis == "documented_dependency_order"
        _assert_order_respects_every_link(d)

    # DFB-body FBD diagrams are now included too: 10 real ones, and not all
    # resolve -- exactly the 3 with unlinked shared-variable dataflow
    # (IO_READVAR, PC_T_GEN, P_MUX3) correctly stay unresolved, the first
    # real-data exercise of that guard since it was only synthetically
    # tested before DFB bodies were in scope.
    dfb_diagrams = {aoi.name: d for aoi in controller.add_on_instructions.values()
                     for routine in aoi.routines.values()
                     for d in routine.graphical_diagrams if d.language == "FBD"}
    assert len(dfb_diagrams) == 10
    unresolved = {name for name, d in dfb_diagrams.items() if not d.execution_order_resolved}
    assert unresolved == {"IO_READVAR", "PC_T_GEN", "P_MUX3"}
    for name, d in dfb_diagrams.items():
        if name not in unresolved:
            _assert_order_respects_every_link(d)

    codes = {}
    for d in result.diagnostics:
        if d.code in {"ambiguous_block_order", "cyclic_block_dependency", "unresolved_block_order"}:
            codes[d.code] = codes.get(d.code, 0) + 1
    assert codes == {"ambiguous_block_order": 1, "unresolved_block_order": 3}


def test_ladder_diagrams_never_get_a_meaningless_unresolved_block_order(tmp_path):
    # execution_order_resolved never becomes True for LD by any mechanism
    # (only FBD networks are topologically sorted), so reporting
    # unresolved_block_order for every LD diagram forever is pure noise, not
    # information distinct from diagram.language == "LD" itself.
    from io import StringIO
    import json
    from twinforge.cli.control_expert import inspect_control_expert

    path = tmp_path / "ld.xef"
    path.write_text('''
      <FEFExchangeFile><contentHeader name="Example"/>
      <program><identProgram name="P"/><LDSource><networkLD>
        <typeLine><contact typeContact="openContact" contactVariableName="A"/>
        <HLink nbCells="9"/></typeLine>
      </networkLD></LDSource></program></FEFExchangeFile>''')
    output = StringIO()
    inspect_control_expert(path, output_format="json", stdout=output)
    project = json.loads(output.getvalue())["projects"][0]
    assert not any(d["code"] == "unresolved_block_order" for d in project["diagnostics"])
