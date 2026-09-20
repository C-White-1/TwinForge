from twinforge.analysis.library_calls import match_library_calls
from twinforge.model import Controller, Identity, Program, Routine, GraphicalDiagram, GraphicalObject, GraphicalPin
from twinforge.model.library_interface import LibraryInterface, LibraryParameter


def test_direction_ambiguity_conventions_and_rerun():
    controller = Controller(name="C", identity=Identity())
    program = Program(name="P")
    routine = Routine(name="R")
    obj = GraphicalObject(kind="block", type_name="timer", pins=[
        GraphicalPin(name="Q", direction="output"),
        GraphicalPin(name="Q", direction="input"),
        GraphicalPin(name="EN", direction="input", role="execution_enable"),
        GraphicalPin(name="EXTRA", direction="input"),
    ])
    routine.graphical_diagrams.append(GraphicalDiagram(language="FBD", objects=[obj]))
    program.add_routine(routine)
    controller.add_program(program)
    signature = LibraryInterface("Timer", "function_block", [LibraryParameter("Q", "BOOL", "output")])
    issues = match_library_calls(controller, [signature])
    assert obj.interface_index == 0
    assert [p.interface_status for p in obj.pins] == ["matched", "unresolved_convention", "implicit_execution_pin", "unresolved_convention"]
    assert obj.pins[0].parameter_index == 0
    assert len(issues) == 2
    match_library_calls(controller, [signature, signature])
    assert obj.interface_status == "ambiguous" and obj.interface_index is None
    assert all(p.parameter_index is None for p in obj.pins)
    signature.parameters.append(LibraryParameter("q", "TIME", "output"))
    match_library_calls(controller, [signature])
    assert obj.pins[0].interface_status == "ambiguous"
    match_library_calls(controller, [])
    assert obj.interface_status == "missing"


def test_extensible_parameter_matches_numbered_pins_with_evidence():
    controller = Controller(name="C", identity=Identity())
    program = Program(name="P")
    routine = Routine(name="R")
    obj = GraphicalObject(kind="block", type_name="ADD", pins=[
        GraphicalPin(name="IN1", direction="input"),
        GraphicalPin(name="IN2", direction="input"),
        GraphicalPin(name="IN3", direction="input"),
        GraphicalPin(name="OUT", direction="output"),
        # No matching evidence marks OUT as extensible; a second output must stay unresolved.
        GraphicalPin(name="OUT2", direction="output"),
    ])
    routine.graphical_diagrams.append(GraphicalDiagram(language="FBD", objects=[obj]))
    program.add_routine(routine)
    controller.add_program(program)
    signature = LibraryInterface("ADD", "function", [
        LibraryParameter("IN1", "ANY_NUM", "input", comment="Summand (Extensible)"),
        LibraryParameter("nin", "DWORD", "input"),
        LibraryParameter("OUT", "ANY_NUM", "output", comment="Sum"),
    ])
    issues = match_library_calls(controller, [signature])
    statuses = [pin.interface_status for pin in obj.pins]
    assert statuses == ["matched", "matched_extensible", "matched_extensible", "matched", "unresolved_convention"]
    assert obj.pins[1].parameter_index == 0 and obj.pins[2].parameter_index == 0
    assert len(issues) == 1 and issues[0][1] is obj.pins[4]


def test_extensible_ambiguous_templates_reported():
    controller = Controller(name="C", identity=Identity())
    program = Program(name="P")
    routine = Routine(name="R")
    obj = GraphicalObject(kind="block", type_name="DUP", pins=[
        # "A1" and "A01" both reduce to base "A" once trailing digits are stripped.
        GraphicalPin(name="A2", direction="input"),
    ])
    routine.graphical_diagrams.append(GraphicalDiagram(language="FBD", objects=[obj]))
    program.add_routine(routine)
    controller.add_program(program)
    signature = LibraryInterface("DUP", "function", [
        LibraryParameter("A1", "ANY_NUM", "input", comment="First (Extensible)"),
        LibraryParameter("A01", "ANY_NUM", "input", comment="Alt (Extensible)"),
    ])
    match_library_calls(controller, [signature])
    assert obj.pins[0].interface_status == "ambiguous"


def test_split_inout_requires_profile_and_preserves_both_pins():
    controller = Controller(name="C", identity=Identity())
    program = Program(name="P")
    routine = Routine(name="R")
    obj = GraphicalObject(kind="block", type_name="Transfer", pins=[
        GraphicalPin(name="state", direction="input", expression="before"),
        GraphicalPin(name="STATE", direction="output", expression="after"),
    ])
    routine.graphical_diagrams.append(GraphicalDiagram(language="FBD", objects=[obj]))
    program.add_routine(routine)
    controller.add_program(program)
    signature = LibraryInterface("Transfer", "function", [LibraryParameter("State", "ANY_ARRAY_INT", "inout")])
    assert len(match_library_calls(controller, [signature])) == 2
    aliases = (("inout", "input"), ("inout", "output"))
    assert not match_library_calls(controller, [signature], direction_aliases=aliases)
    assert [p.parameter_index for p in obj.pins] == [0, 0]
    assert [p.interface_status for p in obj.pins] == ["matched_direction_alias"] * 2
    assert [p.expression for p in obj.pins] == ["before", "after"]
    signature.parameters.append(LibraryParameter("State", "INT", "input"))
    match_library_calls(controller, [signature], direction_aliases=aliases)
    assert obj.pins[0].interface_status == "ambiguous"
    assert obj.pins[0].parameter_index is None
    assert obj.pins[1].parameter_index == 0
    match_library_calls(controller, [signature])
    assert obj.pins[1].interface_status == "unresolved_convention"
    assert obj.pins[1].parameter_index is None
