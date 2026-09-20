"""Symbol evidence must not become an invented wire or execution dependency."""
from twinforge.analysis.graphical_bindings import resolve_graphical_bindings
from twinforge.model import (
    Controller, GraphicalDiagram, GraphicalObject, GraphicalPin,
    Identity, Program, Routine, Tag,
)
from twinforge.parsers.control_expert import capture_bytes, parse_project
from twinforge.schema.control_expert.expressions import EXPRESSION_SPEC


def resolve(controller: Controller):
    return resolve_graphical_bindings(controller, identifier_pattern=EXPRESSION_SPEC.identifier,
                                      literal_patterns=EXPRESSION_SPEC.literals)


def fixture():
    controller = Controller(name="example", identity=Identity())
    controller.add_tag(Tag(name="Buffer", data_type="WORD"))
    program = Program(name="logic")
    routine = Routine(name="logic", language="FBD")
    diagram = GraphicalDiagram(language="FBD", objects=[
        GraphicalObject(kind="block", pins=[
            GraphicalPin(name="OUT", direction="output", expression="Buffer"),
            GraphicalPin(name="IN", direction="input", expression="buffer"),
        ]),
        GraphicalObject(kind="block", pins=[
            GraphicalPin(name="IN", direction="input", expression=" BUFFER "),
        ]),
    ])
    routine.graphical_diagrams.append(diagram)
    program.add_routine(routine)
    controller.add_program(program)
    return controller, diagram


def test_case_insensitive_resolution_and_shared_variables_are_not_wires():
    controller, diagram = fixture()
    assert not resolve(controller)
    assert all(p.target_tag is controller.tags["Buffer"] for o in diagram.objects for p in o.pins)
    assert diagram.objects[1].pins[0].expression == " BUFFER "
    group = diagram.shared_variables[0]
    assert group.symbol_name == "Buffer"
    assert group.input_pins == [(0, 1), (1, 0)]
    assert group.output_pins == [(0, 0)]
    assert not diagram.connectivity_resolved
    assert not diagram.execution_order_resolved
    assert diagram.execution_order == []


def test_literal_unbound_missing_and_complex_expressions():
    controller, diagram = fixture()
    expressions = ["TRUE", "16#FF", "-3", "1.5", "'{1.101}SYS'", None, "missing", "Buffer[1]", "Buffer + 1", ""]
    diagram.objects = [GraphicalObject(kind="block", pins=[
        GraphicalPin(direction="input", expression=e) for e in expressions
    ] + [GraphicalPin(direction="output", expression="1")])]
    issues = resolve(controller)
    assert [p.binding_kind for p in diagram.objects[0].pins] == [
        "literal", "literal", "literal", "literal", "literal", "unbound",
        "missing_symbol", "unresolved_expression", "unresolved_expression",
        "unresolved_expression", "invalid_output_literal",
    ]
    assert len(issues) == 5
    assert all(p.target_tag is None for p in diagram.objects[0].pins)


def test_resolution_rebuilds_derived_state():
    controller, diagram = fixture()
    resolve(controller)
    assert len(diagram.shared_variables) == 1
    resolve(controller)
    assert len(diagram.shared_variables) == 1
    controller.tags.clear()
    assert len(resolve(controller)) == 3
    assert diagram.shared_variables == []
    assert all(p.target_tag is None for o in diagram.objects for p in o.pins)


def test_contact_operand_binding_covers_symbols_and_step_state():
    controller = Controller(name="example", identity=Identity())
    controller.add_tag(Tag(name="Start", data_type="BOOL"))
    program = Program(name="logic")
    routine = Routine(name="logic", language="LD")
    diagram = GraphicalDiagram(language="LD", objects=[
        GraphicalObject(kind="contact", operand="start"),
        GraphicalObject(kind="contact", operand="G1_0.X"),
        GraphicalObject(kind="contact", operand="g1_0.x"),
        GraphicalObject(kind="contact", operand="G1_1.X"),
        GraphicalObject(kind="contact", operand="Missing"),
        GraphicalObject(kind="contact", operand="%S1"),
        GraphicalObject(kind="contact", operand=None),
        GraphicalObject(kind="block", pins=[GraphicalPin(direction="input", expression="Start")]),
    ])
    routine.graphical_diagrams.append(diagram)
    program.add_routine(routine)
    controller.add_program(program)
    issues = resolve_graphical_bindings(
        controller, identifier_pattern=EXPRESSION_SPEC.identifier, literal_patterns=EXPRESSION_SPEC.literals,
        step_names={"g1_0": "G1_0"}, ambiguous_step_names=frozenset({"g1_1"}),
    )
    contacts = diagram.objects[:7]
    assert [c.operand_binding_kind for c in contacts] == [
        "declared_symbol", "declared_step_state", "declared_step_state",
        "ambiguous_step_state", "missing_symbol", "unresolved_expression", "unbound",
    ]
    assert contacts[0].target_tag is controller.tags["Start"]
    assert contacts[1].target_step_name == "G1_0" and contacts[2].target_step_name == "G1_0"
    assert contacts[3].target_step_name is None
    contact_codes = {issue.code for issue in issues if issue.pin_index is None}
    assert contact_codes == {
        "ambiguous_contact_step_state", "unresolved_contact_symbol", "unresolved_contact_expression",
    }
    # The block's pin, unaffected by contact handling, resolves cleanly with no issue.
    assert diagram.objects[7].pins[0].target_tag is controller.tags["Start"]
    assert not any(issue.pin_index is not None for issue in issues)


def test_contact_binding_rebuilds_on_rerun():
    controller = Controller(name="example", identity=Identity())
    program = Program(name="logic")
    routine = Routine(name="logic", language="LD")
    diagram = GraphicalDiagram(language="LD", objects=[GraphicalObject(kind="contact", operand="Sensor")])
    routine.graphical_diagrams.append(diagram)
    program.add_routine(routine)
    controller.add_program(program)
    resolve_graphical_bindings(controller, identifier_pattern=EXPRESSION_SPEC.identifier,
                               literal_patterns=EXPRESSION_SPEC.literals)
    assert diagram.objects[0].operand_binding_kind == "missing_symbol"
    controller.add_tag(Tag(name="Sensor", data_type="BOOL"))
    resolve_graphical_bindings(controller, identifier_pattern=EXPRESSION_SPEC.identifier,
                               literal_patterns=EXPRESSION_SPEC.literals)
    assert diagram.objects[0].operand_binding_kind == "declared_symbol"
    assert diagram.objects[0].target_tag is controller.tags["Sensor"]


def test_ambiguous_source_declarations_never_bind_to_first_retained_tag():
    xml = b'''<ZEFExchangeFile><contentHeader name="example"/>
      <dataBlock><variables name="x" typeName="INT"/><variables name="X" typeName="INT"/></dataBlock>
      <program><identProgram name="logic" task="MAST"/><FBDSource><networkFBD>
        <FFBBlock typeName="FN"><descriptionFFB><inputVariable formalParameter="IN" effectiveParameter="x"/></descriptionFFB></FFBBlock>
      </networkFBD></FBDSource></program></ZEFExchangeFile>'''
    result = parse_project(capture_bytes(xml, name="example.xef"))
    pin = result.controller.programs["logic"].routines["logic"].graphical_diagrams[0].objects[0].pins[0]
    assert pin.binding_kind == "ambiguous_symbol"
    assert pin.target_tag is None
    issue = next(d for d in result.diagnostics if d.code == "ambiguous_pin_symbol")
    assert issue.source.xml_path.startswith("/ZEFExchangeFile/")
