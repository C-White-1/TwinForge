from twinforge.analysis.execution_order import resolve_fbd_execution_order
from twinforge.model import (
    Controller, GraphicalDiagram, GraphicalObject, GraphicalPin,
    GraphicalVariableReferences, Identity, Program, Routine,
)


def _diagram(language="FBD", *, objects, shared_variables=()):
    diagram = GraphicalDiagram(language=language, objects=list(objects))
    diagram.shared_variables.extend(shared_variables)
    return diagram


def _pin(name, direction, *, binding_kind="declared_symbol"):
    return GraphicalPin(name=name, direction=direction, binding_kind=binding_kind)


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
