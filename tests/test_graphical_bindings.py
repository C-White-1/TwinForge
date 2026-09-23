"""Symbol evidence must not become an invented wire or execution dependency."""
from twinforge.analysis.graphical_bindings import (
    resolve_coil_write_evidence, resolve_function_block_bindings, resolve_graphical_bindings,
)
from twinforge.model import (
    AddOnInstruction, AddOnInstructionParameter, Controller, GraphicalDiagram, GraphicalObject, GraphicalPin,
    Identity, Program, Routine, Tag,
)
from twinforge.parsers.control_expert import capture_bytes, parse_project
from twinforge.schema.control_expert.expressions import EXPRESSION_SPEC


def resolve(controller: Controller):
    return resolve_graphical_bindings(controller, identifier_pattern=EXPRESSION_SPEC.identifier,
                                      literal_patterns=EXPRESSION_SPEC.literals,
                                      direct_address_pattern=EXPRESSION_SPEC.direct_address)


def resolve_fb(controller: Controller):
    return resolve_function_block_bindings(controller, identifier_pattern=EXPRESSION_SPEC.identifier,
                                           literal_patterns=EXPRESSION_SPEC.literals,
                                           direct_address_pattern=EXPRESSION_SPEC.direct_address)


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
    expressions = [
        "TRUE", "16#FF", "-3", "1.5", "'{1.101}SYS'",
        "16#0000_0001", "2#111_1000_0000", "t#200ms", "T#24h", "t#0.5s", "-t#5s",
        None, "missing", "Buffer[1]", "Buffer + missing", "",
    ]
    diagram.objects = [GraphicalObject(kind="block", pins=[
        GraphicalPin(direction="input", expression=e) for e in expressions
    ] + [GraphicalPin(direction="output", expression="1")])]
    issues = resolve(controller)
    assert [p.binding_kind for p in diagram.objects[0].pins] == [
        "literal", "literal", "literal", "literal", "literal",
        "literal", "literal", "literal", "literal", "literal", "literal",
        "unbound", "missing_symbol", "unresolved_expression", "unresolved_expression",
        "unresolved_expression", "invalid_output_literal",
    ]
    assert len(issues) == 5
    assert all(p.target_tag is None for p in diagram.objects[0].pins)


def test_digit_separator_and_time_literal_edge_cases_stay_unresolved():
    controller, diagram = fixture()
    # Leading/trailing/doubled separators, and a combined multi-unit TIME form
    # (no corpus evidence for that shape), must not be accepted as literals.
    expressions = ["16#_FF", "16#FF_", "16#0__1", "2#01_", "t#1d2h", "t#5", "t#s", "16#0000__0001"]
    diagram.objects = [GraphicalObject(kind="block", pins=[
        GraphicalPin(direction="input", expression=e) for e in expressions
    ])]
    resolve(controller)
    assert all(p.binding_kind == "unresolved_expression" for p in diagram.objects[0].pins)


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
        direct_address_pattern=EXPRESSION_SPEC.direct_address,
    )
    contacts = diagram.objects[:7]
    assert [c.operand_binding_kind for c in contacts] == [
        "declared_symbol", "declared_step_state", "declared_step_state",
        "ambiguous_step_state", "missing_symbol", "direct_address", "unbound",
    ]
    assert contacts[0].target_tag is controller.tags["Start"]
    assert contacts[1].target_step_name == "G1_0" and contacts[2].target_step_name == "G1_0"
    assert contacts[3].target_step_name is None
    contact_codes = {issue.code for issue in issues if issue.pin_index is None}
    assert contact_codes == {
        "ambiguous_contact_step_state", "unresolved_contact_symbol",
    }
    # The block's pin, unaffected by contact handling, resolves cleanly with no issue.
    assert diagram.objects[7].pins[0].target_tag is controller.tags["Start"]
    assert not any(issue.pin_index is not None for issue in issues)


def test_coil_operand_binding_covers_symbols_but_never_step_state():
    controller = Controller(name="example", identity=Identity())
    controller.add_tag(Tag(name="Output", data_type="BOOL"))
    program = Program(name="logic")
    routine = Routine(name="logic", language="LD")
    diagram = GraphicalDiagram(language="LD", objects=[
        GraphicalObject(kind="coil", operand="output"),
        # Lexically matches the step-state pattern, but a coil cannot target
        # a step's active-state bit -- must resolve as a plain symbol lookup.
        GraphicalObject(kind="coil", operand="G1_0.X"),
        GraphicalObject(kind="coil", operand="Missing"),
        GraphicalObject(kind="coil", operand="%S1"),
        GraphicalObject(kind="coil", operand=None),
    ])
    routine.graphical_diagrams.append(diagram)
    program.add_routine(routine)
    controller.add_program(program)
    issues = resolve_graphical_bindings(
        controller, identifier_pattern=EXPRESSION_SPEC.identifier, literal_patterns=EXPRESSION_SPEC.literals,
        step_names={"g1_0": "G1_0"}, direct_address_pattern=EXPRESSION_SPEC.direct_address,
    )
    coils = diagram.objects
    assert [c.operand_binding_kind for c in coils] == [
        "declared_symbol", "unresolved_expression", "missing_symbol", "direct_address", "unbound",
    ]
    assert coils[0].target_tag is controller.tags["Output"]
    assert coils[1].target_step_name is None  # Never classified as a step state.
    coil_codes = {issue.code for issue in issues if issue.pin_index is None}
    assert coil_codes == {"unresolved_coil_expression", "unresolved_coil_symbol"}


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


def _fb_controller(*, parameter_name: str = "IN", pin_expression: str | None = None, global_tag_name: str | None = None):
    controller = Controller(name="example", identity=Identity())
    if global_tag_name:
        controller.add_tag(Tag(name=global_tag_name, data_type="BOOL"))
    aoi = AddOnInstruction(name="M_FN")
    aoi.add_parameter(AddOnInstructionParameter(name=parameter_name, data_type="BOOL", usage="input"))
    routine = Routine(name="M_FN", language="FBD")
    diagram = GraphicalDiagram(language="FBD", objects=[GraphicalObject(kind="block", pins=[
        GraphicalPin(name="EN", direction="input", expression=pin_expression or parameter_name),
    ])])
    routine.graphical_diagrams.append(diagram)
    aoi.add_routine(routine)
    controller.add_add_on_instruction(aoi)
    return controller, diagram


def test_function_block_pin_resolves_against_its_own_parameter():
    controller, diagram = _fb_controller()
    issues = resolve_fb(controller)
    pin = diagram.objects[0].pins[0]
    assert pin.binding_kind == "declared_symbol"
    assert pin.target_parameter is controller.add_on_instructions["M_FN"].parameters["IN"]
    assert pin.target_tag is None
    assert not issues


def test_function_block_scope_never_falls_back_to_the_project_global_tags():
    # "IN" exists as a global tag, but this FB has no parameter or local
    # named "IN" -- encapsulation means the global tag must not be used.
    controller, diagram = _fb_controller(parameter_name="OTHER", pin_expression="IN", global_tag_name="IN")
    resolve_fb(controller)
    pin = diagram.objects[0].pins[0]
    assert pin.binding_kind == "missing_symbol"
    assert pin.target_tag is None and pin.target_parameter is None


def test_same_parameter_name_in_two_function_blocks_does_not_collide():
    controller = Controller(name="example", identity=Identity())
    for fb_name in ("M_A", "M_B"):
        aoi = AddOnInstruction(name=fb_name)
        aoi.add_parameter(AddOnInstructionParameter(name="IN", data_type="BOOL", usage="input"))
        routine = Routine(name=fb_name, language="FBD")
        routine.graphical_diagrams.append(GraphicalDiagram(language="FBD", objects=[GraphicalObject(
            kind="block", pins=[GraphicalPin(name="EN", direction="input", expression="IN")])]))
        aoi.add_routine(routine)
        controller.add_add_on_instruction(aoi)
    resolve_fb(controller)
    for fb_name in ("M_A", "M_B"):
        aoi = controller.add_on_instructions[fb_name]
        pin = next(iter(aoi.routines.values())).graphical_diagrams[0].objects[0].pins[0]
        assert pin.target_parameter is aoi.parameters["IN"]  # Each FB's own, not the other's.


def test_parameter_and_local_tag_sharing_a_name_within_one_fb_is_ambiguous():
    controller = Controller(name="example", identity=Identity())
    aoi = AddOnInstruction(name="M_FN")
    aoi.add_parameter(AddOnInstructionParameter(name="X", data_type="BOOL", usage="input"))
    aoi.add_local_tag(Tag(name="X", data_type="BOOL"))
    routine = Routine(name="M_FN", language="FBD")
    diagram = GraphicalDiagram(language="FBD", objects=[GraphicalObject(kind="block", pins=[
        GraphicalPin(name="EN", direction="input", expression="X"),
    ])])
    routine.graphical_diagrams.append(diagram)
    aoi.add_routine(routine)
    controller.add_add_on_instruction(aoi)
    issues = resolve_fb(controller)
    pin = diagram.objects[0].pins[0]
    assert pin.binding_kind == "ambiguous_symbol"
    assert any(issue.code == "ambiguous_pin_symbol" and issue.scope == "function_block" for issue in issues)


def test_member_path_context_exposes_only_public_locals_of_a_function_block():
    from twinforge.analysis.graphical_bindings import member_path_context
    from twinforge.schema.control_expert.mapping import BASIC_MAPPING

    aoi = AddOnInstruction(name="IO_PM5320")
    public = Tag(name="ACPT", data_type="REAL")
    public.metadata["visibility"] = "public"
    private = Tag(name="Secret", data_type="REAL")
    private.metadata["visibility"] = "private"
    aoi.add_local_tag(public)
    aoi.add_local_tag(private)
    controller = Controller(name="example", identity=Identity())
    controller.add_add_on_instruction(aoi)

    context = member_path_context(controller, [], BASIC_MAPPING.array_pattern)
    members = context.function_blocks["io_pm5320"]
    assert members["acpt"] is public
    assert "secret" not in members


def test_member_path_context_never_picks_between_two_same_named_library_interfaces():
    from twinforge.analysis.graphical_bindings import member_path_context
    from twinforge.model.library_interface import LibraryInterface, LibraryParameter
    from twinforge.schema.control_expert.mapping import BASIC_MAPPING

    unique = LibraryInterface("CTU", "EFB", [LibraryParameter("Q", "BOOL", "output")])
    duplicate_a = LibraryInterface("TON", "EFB", [LibraryParameter("Q", "BOOL", "output")])
    duplicate_b = LibraryInterface("TON", "EFB", [LibraryParameter("ET", "TIME", "output")])
    controller = Controller(name="example", identity=Identity())

    context = member_path_context(controller, [unique, duplicate_a, duplicate_b], BASIC_MAPPING.array_pattern)
    assert context.library_interfaces["ctu"] is unique
    assert "ton" not in context.library_interfaces


def test_public_local_resolves_externally_but_private_locals_do_not():
    result = parse_project(capture_bytes((
        '<ZEFExchangeFile><contentHeader name="E"/>'
        '<FBSource nameOfFBType="IO_PM5320">'
        '<publicLocalVariables><variables name="ACPT" typeName="REAL"/></publicLocalVariables>'
        '<privateLocalVariables><variables name="Secret" typeName="REAL"/></privateLocalVariables>'
        '<FBProgram><STSource>ACPT := 1.0;</STSource></FBProgram>'
        '</FBSource>'
        '<dataBlock><variables name="PM5320" typeName="IO_PM5320"/></dataBlock>'
        '<logicConf><resource><taskDesc task="MAST" taskType="cyclic">'
        '<sectionDesc name="s"/></taskDesc></resource></logicConf>'
        '<program><identProgram name="s" task="MAST"/><FBDSource><networkFBD>'
        '<FFBBlock instanceName="B" typeName="X"><descriptionFFB>'
        '<outputVariable formalParameter="OUT" effectiveParameter="PM5320.ACPT"/>'
        '<inputVariable formalParameter="IN" effectiveParameter="PM5320.Secret"/>'
        '</descriptionFFB></FFBBlock></networkFBD></FBDSource></program></ZEFExchangeFile>').encode(),
        name="p.xef"))
    routine = result.controller.programs["s"].main_routine
    assert routine is not None
    pins = {pin.name: pin for pin in routine.graphical_diagrams[0].objects[0].pins}
    assert pins["OUT"].binding_kind == "declared_member_path"
    assert pins["OUT"].member_path is not None and pins["OUT"].member_path.type_name == "REAL"
    # A private local is never proven reachable from outside the FB instance.
    assert pins["IN"].binding_kind == "unresolved_expression"


def test_binding_inside_the_fb_body_still_sees_both_public_and_private_locals():
    # The public/private filter is an *external* member-path rule only; the
    # existing isolated-namespace binding inside a FB's own body is unaffected.
    controller = Controller(name="example", identity=Identity())
    aoi = AddOnInstruction(name="M_FN")
    aoi.add_local_tag(Tag(name="Pub", data_type="BOOL", metadata={"visibility": "public"}))
    aoi.add_local_tag(Tag(name="Priv", data_type="BOOL", metadata={"visibility": "private"}))
    routine = Routine(name="M_FN", language="FBD")
    diagram = GraphicalDiagram(language="FBD", objects=[GraphicalObject(kind="block", pins=[
        GraphicalPin(name="EN", direction="input", expression="Pub"),
        GraphicalPin(name="EN2", direction="input", expression="Priv"),
    ])])
    routine.graphical_diagrams.append(diagram)
    aoi.add_routine(routine)
    controller.add_add_on_instruction(aoi)
    resolve_fb(controller)
    pins = diagram.objects[0].pins
    assert pins[0].binding_kind == "declared_symbol" and pins[0].target_tag is aoi.local_tags["Pub"]
    assert pins[1].binding_kind == "declared_symbol" and pins[1].target_tag is aoi.local_tags["Priv"]


def test_pin_resolves_a_binary_expression_over_two_declared_operands():
    controller, diagram = fixture()
    diagram.objects = [GraphicalObject(kind="block", pins=[
        GraphicalPin(direction="input", expression="Buffer + 1"),
        GraphicalPin(direction="input", expression="Buffer + missing"),  # right operand undeclared
    ])]
    resolve(controller)
    pins = diagram.objects[0].pins
    assert pins[0].binding_kind == "declared_expression"
    assert pins[0].binary_expression is not None
    assert pins[0].binary_expression.operator == "+"
    assert pins[0].binary_expression.left.target_tag is controller.tags["Buffer"]
    assert pins[0].binary_expression.right.kind == "literal"
    # A resolved binary expression pin has no single base symbol of its own.
    assert pins[0].target_tag is None and pins[0].member_path is None
    assert not diagram.shared_variables  # never treated as a wire
    assert pins[1].binding_kind == "unresolved_expression" and pins[1].binary_expression is None


def test_contact_and_coil_operands_also_resolve_binary_expressions():
    controller = Controller(name="example", identity=Identity())
    controller.add_tag(Tag(name="Threshold", data_type="INT"))
    program = Program(name="logic")
    routine = Routine(name="logic", language="LD")
    diagram = GraphicalDiagram(language="LD", objects=[
        GraphicalObject(kind="contact", operand="Threshold > 0"),
        GraphicalObject(kind="coil", operand="Threshold=1"),
    ])
    routine.graphical_diagrams.append(diagram)
    program.add_routine(routine)
    controller.add_program(program)
    resolve_graphical_bindings(controller, identifier_pattern=EXPRESSION_SPEC.identifier,
                               literal_patterns=EXPRESSION_SPEC.literals)
    contact, coil = diagram.objects
    assert contact.operand_binding_kind == "declared_expression"
    assert contact.operand_binary_expression is not None and contact.operand_binary_expression.operator == ">"
    assert coil.operand_binding_kind == "declared_expression"
    assert coil.operand_binary_expression is not None and coil.operand_binary_expression.operator == "="


def test_direct_address_is_classified_on_pins_and_operands_without_a_target():
    controller, diagram = fixture()
    diagram.objects = [GraphicalObject(kind="block", pins=[
        GraphicalPin(direction="input", expression="%S6"),
        GraphicalPin(direction="output", expression="%MW200.1"),
    ])]
    resolve(controller)
    pins = diagram.objects[0].pins
    assert pins[0].binding_kind == "direct_address" and pins[0].target_tag is None
    assert pins[1].binding_kind == "direct_address"  # allowed on an output pin, unlike a literal


def test_direct_address_pattern_is_opt_in_and_never_defaults_on():
    # A caller that doesn't pass direct_address_pattern keeps the prior
    # behavior: a "%..." expression stays unresolved rather than silently
    # gaining a new classification.
    controller, diagram = fixture()
    diagram.objects = [GraphicalObject(kind="block", pins=[
        GraphicalPin(direction="input", expression="%S6"),
    ])]
    from twinforge.analysis.graphical_bindings import resolve_graphical_bindings
    resolve_graphical_bindings(controller, identifier_pattern=EXPRESSION_SPEC.identifier,
                               literal_patterns=EXPRESSION_SPEC.literals)
    assert diagram.objects[0].pins[0].binding_kind == "unresolved_expression"


def test_real_fixtures_classify_direct_addresses_when_available():
    from pathlib import Path
    from twinforge.parsers.control_expert import capture_file, parse_projects

    # glob() only ever returns paths that already exist, so checking "any of
    # them exists" is a no-op that skips only when the whole directory is
    # empty -- this must check the specific fixtures the assertion below
    # depends on, or it silently runs (and fails) against a partial checkout.
    # The exact-set assertion below is calibrated against these two fixtures
    # only; iterating the whole directory (glob.glob("reference/control-
    # expert/*")) would also fail the moment any other real fixture is added
    # locally -- deliberately scoped instead of "whatever happens to be
    # present" (see the local-corpus fragility this caused in practice: a
    # third-party fixture download broke this test's exact-set assertion by
    # adding real %M12/%M15 evidence of its own, unrelated to what this test
    # verifies).
    required = ["estradege_m580-safety.xef", "Escalier_Mecanique.XEF"]
    if not all((Path("reference/control-expert") / name).exists() for name in required):
        import pytest
        pytest.skip("reference fixtures absent")
    found = set()
    for name in required:
        path = Path("reference/control-expert") / name
        for result in parse_projects(capture_file(path)):
            controller = result.controller
            for container in [*controller.programs.values(), *controller.add_on_instructions.values()]:
                for routine in container.routines.values():
                    for diagram in routine.graphical_diagrams:
                        for obj in diagram.objects:
                            if obj.operand_binding_kind == "direct_address":
                                found.add(obj.operand)
                            for pin in obj.pins:
                                if pin.binding_kind == "direct_address":
                                    found.add(pin.expression)
    assert found == {"%S1", "%S6"}


def test_call_parameter_type_resolves_a_program_and_a_step_reference():
    # Generalized by declared parameter type (SFCCHART_STATE/SFCSTEP_STATE),
    # not hardcoded to INITCHART/SETSTEP -- any block whose library interface
    # declares a parameter of one of these types is covered the same way.
    controller = Controller(name="example", identity=Identity())
    controller.add_program(Program(name="G1"))
    diagram = GraphicalDiagram(language="FBD", objects=[
        GraphicalObject(kind="block", type_name="InitChart", pins=[
            GraphicalPin(name="CHARTREF", direction="input", expression="G1"),
            GraphicalPin(name="CHARTREF", direction="input", expression="NoSuchChart"),
        ]),
        GraphicalObject(kind="block", type_name="SetStep", pins=[
            GraphicalPin(name="STEPNAME", direction="input", expression="G1_0"),
        ]),
    ])
    program = Program(name="Init")
    routine = Routine(name="Init", language="FBD")
    routine.graphical_diagrams.append(diagram)
    program.add_routine(routine)
    controller.add_program(program)

    from twinforge.model.library_interface import LibraryInterface, LibraryParameter
    interfaces = [
        LibraryInterface("InitChart", "function", [LibraryParameter("CHARTREF", "SFCCHART_STATE", "input")]),
        LibraryInterface("SetStep", "function", [LibraryParameter("STEPNAME", "SFCSTEP_STATE", "input")]),
    ]
    call_parameter_types = {
        "initchart": {"chartref": "SFCCHART_STATE"}, "setstep": {"stepname": "SFCSTEP_STATE"},
    }
    resolve_graphical_bindings(
        controller, identifier_pattern=EXPRESSION_SPEC.identifier, literal_patterns=EXPRESSION_SPEC.literals,
        program_names={"g1": "G1"}, call_parameter_types=call_parameter_types,
        step_names={"g1_0": "G1_0"},
    )
    init_pins = diagram.objects[0].pins
    assert init_pins[0].binding_kind == "declared_program_reference" and init_pins[0].target_program_name == "G1"
    assert init_pins[1].binding_kind == "missing_symbol"  # "NoSuchChart" -- never guessed at
    step_pin = diagram.objects[1].pins[0]
    assert step_pin.binding_kind == "declared_step_reference" and step_pin.target_step_name == "G1_0"
    _ = interfaces  # documents the real library interfaces this scenario mirrors


def test_call_parameter_type_reference_stays_missing_symbol_without_a_declared_type():
    # A plain identifier-shaped pin with no matching call_parameter_types
    # entry (e.g. an ordinary block, or a call this project has no library
    # interface evidence for) must not be treated as a program/step reference.
    controller, diagram = fixture()
    diagram.objects = [GraphicalObject(kind="block", type_name="SomeOtherBlock", pins=[
        GraphicalPin(name="IN", direction="input", expression="G1"),
    ])]
    resolve_graphical_bindings(
        controller, identifier_pattern=EXPRESSION_SPEC.identifier, literal_patterns=EXPRESSION_SPEC.literals,
        program_names={"g1": "G1"},
    )
    assert diagram.objects[0].pins[0].binding_kind == "missing_symbol"


def test_call_parameter_type_reference_is_ambiguous_when_the_name_collides():
    controller = Controller(name="example", identity=Identity())
    diagram = GraphicalDiagram(language="FBD", objects=[
        GraphicalObject(kind="block", type_name="InitChart", pins=[
            GraphicalPin(name="CHARTREF", direction="input", expression="G1"),
        ]),
        GraphicalObject(kind="block", type_name="SetStep", pins=[
            GraphicalPin(name="STEPNAME", direction="input", expression="Dup"),
        ]),
    ])
    program = Program(name="Init")
    routine = Routine(name="Init", language="FBD")
    routine.graphical_diagrams.append(diagram)
    program.add_routine(routine)
    controller.add_program(program)
    issues = resolve_graphical_bindings(
        controller, identifier_pattern=EXPRESSION_SPEC.identifier, literal_patterns=EXPRESSION_SPEC.literals,
        program_names={"g1": "G1"}, ambiguous_program_names=frozenset({"g1"}),
        step_names={"dup": "Dup"}, ambiguous_step_names=frozenset({"dup"}),
        call_parameter_types={"initchart": {"chartref": "SFCCHART_STATE"},
                              "setstep": {"stepname": "SFCSTEP_STATE"}},
    )
    chart_pin, step_pin = diagram.objects[0].pins[0], diagram.objects[1].pins[0]
    assert chart_pin.binding_kind == "ambiguous_symbol" and chart_pin.target_program_name is None
    assert step_pin.binding_kind == "ambiguous_symbol" and step_pin.target_step_name is None
    assert {issue.code for issue in issues} == {"ambiguous_pin_symbol"}


def test_a_declared_tag_takes_precedence_over_a_chart_or_step_reference():
    # Symbols are checked first; a program/step reference is only attempted
    # once a pin's text is confirmed *not* to name a declared tag.
    controller = Controller(name="example", identity=Identity())
    controller.add_tag(Tag(name="G1", data_type="BOOL"))
    controller.add_program(Program(name="G1"))
    diagram = GraphicalDiagram(language="FBD", objects=[
        GraphicalObject(kind="block", type_name="InitChart", pins=[
            GraphicalPin(name="CHARTREF", direction="input", expression="G1"),
        ]),
    ])
    program = Program(name="Init")
    routine = Routine(name="Init", language="FBD")
    routine.graphical_diagrams.append(diagram)
    program.add_routine(routine)
    controller.add_program(program)
    resolve_graphical_bindings(
        controller, identifier_pattern=EXPRESSION_SPEC.identifier, literal_patterns=EXPRESSION_SPEC.literals,
        program_names={"g1": "G1"}, call_parameter_types={"initchart": {"chartref": "SFCCHART_STATE"}},
    )
    pin = diagram.objects[0].pins[0]
    assert pin.binding_kind == "declared_symbol"
    assert pin.target_tag is controller.tags["G1"] and pin.target_program_name is None


def test_chart_control_call_references_resolve_inside_a_function_block_body_too():
    # A call's chart/step reference is project-wide identity, not project-wide
    # *tag* scope -- unlike an LD contact's `.X` step-state test (deliberately
    # FB-scope-empty), it resolves inside a DFB body the same way it does at
    # program scope.
    aoi = AddOnInstruction(name="MyDFB")
    routine = Routine(name="MyDFB", language="FBD")
    diagram = GraphicalDiagram(language="FBD", objects=[
        GraphicalObject(kind="block", type_name="SetStep", pins=[
            GraphicalPin(name="STEPNAME", direction="input", expression="G1_0"),
        ]),
    ])
    routine.graphical_diagrams.append(diagram)
    aoi.add_routine(routine)
    controller = Controller(name="example", identity=Identity())
    controller.add_add_on_instruction(aoi)
    resolve_function_block_bindings(
        controller, identifier_pattern=EXPRESSION_SPEC.identifier, literal_patterns=EXPRESSION_SPEC.literals,
        step_names={"g1_0": "G1_0"}, call_parameter_types={"setstep": {"stepname": "SFCSTEP_STATE"}},
    )
    pin = diagram.objects[0].pins[0]
    assert pin.binding_kind == "declared_step_reference" and pin.target_step_name == "G1_0"


def test_step_state_contact_inside_a_function_block_body_still_stays_unresolved():
    # The one thing the fix above must NOT change: an LD contact testing
    # `<step>.X` is still resolved against an empty, FB-scope-local step
    # table, even when the same project-wide steps are supplied for
    # chart-control-call resolution above.
    aoi = AddOnInstruction(name="MyDFB")
    routine = Routine(name="MyDFB", language="LD")
    diagram = GraphicalDiagram(language="LD", objects=[
        GraphicalObject(kind="contact", operand="G1_0.X"),
    ])
    routine.graphical_diagrams.append(diagram)
    aoi.add_routine(routine)
    controller = Controller(name="example", identity=Identity())
    controller.add_add_on_instruction(aoi)
    resolve_function_block_bindings(
        controller, identifier_pattern=EXPRESSION_SPEC.identifier, literal_patterns=EXPRESSION_SPEC.literals,
        step_names={"g1_0": "G1_0"},
    )
    assert diagram.objects[0].operand_binding_kind == "missing_step_state"
    assert diagram.objects[0].target_step_name is None


def test_real_fixture_resolves_chart_control_call_references_when_available():
    import pytest
    from pathlib import Path
    from twinforge.parsers.control_expert import capture_file, parse_projects

    path = Path("reference/control-expert/MultiGrafcet_Coordination_V1_2026.XEF")
    if not path.exists():
        pytest.skip("reference fixture absent")
    result, = parse_projects(capture_file(path))
    found = []
    for program in result.controller.programs.values():
        for routine in program.routines.values():
            for diagram in routine.graphical_diagrams:
                for obj in diagram.objects:
                    if obj.type_name and obj.type_name.upper() in ("INITCHART", "SETSTEP"):
                        for pin in obj.pins:
                            if pin.binding_kind in ("declared_program_reference", "declared_step_reference"):
                                found.append((obj.type_name, pin.name, pin.target_program_name, pin.target_step_name))
    assert ("INITCHART", "CHARTREF", "G1", None) in found
    assert ("INITCHART", "CHARTREF", "G2", None) in found
    assert ("SETSTEP", "STEPNAME", None, "G1_0") in found
    assert len(found) == 3


def test_coil_write_evidence_reports_every_writer_including_single():
    controller = Controller(name="example", identity=Identity())
    controller.add_tag(Tag(name="Alarm", data_type="BOOL"))
    controller.add_tag(Tag(name="Reset", data_type="BOOL"))
    set_program = Program(name="SetLogic")
    set_routine = Routine(name="SetLogic", language="LD")
    set_routine.graphical_diagrams.append(GraphicalDiagram(language="LD", objects=[
        GraphicalObject(kind="coil", operand="Alarm"),
    ]))
    set_program.add_routine(set_routine)
    reset_program = Program(name="ResetLogic")
    reset_routine = Routine(name="ResetLogic", language="LD")
    reset_routine.graphical_diagrams.append(GraphicalDiagram(language="LD", objects=[
        GraphicalObject(kind="coil", operand="Alarm"),
        GraphicalObject(kind="coil", operand="Reset"),
    ]))
    reset_program.add_routine(reset_routine)
    controller.add_program(set_program)
    controller.add_program(reset_program)
    resolve(controller)
    evidence = {e.tag_name: e for e in resolve_coil_write_evidence(controller)}
    assert len(evidence["Alarm"].locations) == 2
    assert {(loc.program_name, loc.routine_name) for loc in evidence["Alarm"].locations} == {
        ("SetLogic", "SetLogic"), ("ResetLogic", "ResetLogic"),
    }
    assert len(evidence["Reset"].locations) == 1


def test_coil_write_evidence_excludes_output_pins_and_function_block_bodies():
    # A general FBD/EFB output pin is not treated as a write -- source pin
    # direction alone does not prove memory read/write effects. A coil
    # inside an FB body writes the FB *definition*'s own local tag, shared
    # textually across every call-site instance, not a single project-wide
    # storage location -- also excluded.
    controller = Controller(name="example", identity=Identity())
    controller.add_tag(Tag(name="Buffer", data_type="WORD"))
    program = Program(name="logic")
    routine = Routine(name="logic", language="FBD")
    routine.graphical_diagrams.append(GraphicalDiagram(language="FBD", objects=[
        GraphicalObject(kind="block", pins=[
            GraphicalPin(name="OUT", direction="output", expression="Buffer"),
        ]),
    ]))
    program.add_routine(routine)
    controller.add_program(program)
    aoi = AddOnInstruction(name="MyDFB")
    aoi.add_local_tag(Tag(name="Local", data_type="BOOL"))
    fb_routine = Routine(name="MyDFB", language="LD")
    fb_routine.graphical_diagrams.append(GraphicalDiagram(language="LD", objects=[
        GraphicalObject(kind="coil", operand="Local"),
    ]))
    aoi.add_routine(fb_routine)
    controller.add_add_on_instruction(aoi)
    resolve(controller)
    resolve_fb(controller)
    assert resolve_coil_write_evidence(controller) == []


def test_real_fixture_resolves_coil_write_evidence_when_available():
    import pytest
    from pathlib import Path
    from twinforge.parsers.control_expert import capture_file, parse_projects

    path = Path("reference/control-expert/Escalier_Mecanique.XEF")
    if not path.exists():
        pytest.skip("reference fixture absent")
    result, = parse_projects(capture_file(path))
    multi = {e.tag_name: e for e in result.coil_write_evidence if len(e.locations) > 1}
    assert set(multi) == {"p_prev"}
    assert {(loc.program_name, loc.routine_name) for loc in multi["p_prev"].locations} == {
        ("Init_Logic", "Init_Logic"), ("Rising_Edge_Detection", "Rising_Edge_Detection"),
    }
    assert any(d.code == "multiple_coil_writers" and d.message.startswith("p_prev:")
              for d in result.diagnostics)
