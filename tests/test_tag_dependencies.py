from twinforge.analysis import (
    TagReferenceAccess,
    build_tag_dependency_graph,
    tag_dependency_graph_json,
)
from twinforge.model import (
    Controller,
    Identity,
    LadderInstruction,
    LadderOperation,
    LadderParallel,
    LadderRung,
    LadderSeries,
    Program,
    Routine,
    StructuredTextLine,
    Tag,
)


def _controller() -> Controller:
    controller = Controller(name="PLC", identity=Identity())
    for name in ("Source", "Result", "Timer", "Array", "Index"):
        controller.add_tag(Tag(name=name))
    controller.add_tag(Tag(name="ResultAlias", alias_for="Result.Value"))
    controller.add_tag(
        Tag(name="DirectOutputAlias", alias_for="Local:1:O.Data.1")
    )
    program = Program("MainProgram")
    program.add_tag(Tag(name="Start"))
    ladder = Routine(name="Ladder", language="RLL")
    ladder.ladder_rungs = [
        LadderRung(
            number=1,
            text="XIC(Start)MOV(Source,Result);",
        ),
        LadderRung(
            number=2,
            text="GRT(Timer.ACC,100)OTE(Local:1:O.Data.0);",
        ),
    ]
    structured = Routine(name="Structured", language="ST")
    structured.structured_text_lines = [
        StructuredTextLine(
            number=10,
            text="Drive(Enable := Start, Done => Result);",
        ),
        StructuredTextLine(number=11, text="Result := Source;"),
        StructuredTextLine(number=12, text="IF Start AND Timer.DN THEN"),
        StructuredTextLine(number=13, text="Result := Array[Index];"),
        StructuredTextLine(number=14, text="END_IF;"),
        StructuredTextLine(number=15, text="WHILE Missing DO"),
        StructuredTextLine(number=16, text="Source := Result;"),
        StructuredTextLine(number=17, text="END_WHILE;"),
    ]
    program.add_routine(ladder)
    program.add_routine(structured)
    controller.add_program(program)
    return controller


def test_builds_scoped_read_write_cross_references() -> None:
    graph = build_tag_dependency_graph(_controller())

    references = {
        (
            item.instruction,
            item.tag_key,
            item.member_path,
            item.access,
        )
        for item in graph.references
    }
    assert (
        "XIC",
        "program:MainProgram:Start",
        None,
        TagReferenceAccess.READ,
    ) in references
    assert (
        "MOV",
        "controller:Result",
        None,
        TagReferenceAccess.WRITE,
    ) in references
    assert (
        "GRT",
        "controller:Timer",
        ".ACC",
        TagReferenceAccess.READ,
    ) in references
    assert (
        "Drive",
        "controller:Result",
        None,
        TagReferenceAccess.WRITE,
    ) in references


def test_preserves_unresolved_direct_io_operand_and_serializes_deterministically() -> None:
    first = build_tag_dependency_graph(_controller())
    second = build_tag_dependency_graph(_controller())

    unresolved = {item.identifier for item in first.unresolved_references}
    assert "Local:1:O.Data.0" in unresolved
    assert tag_dependency_graph_json(first) == tag_dependency_graph_json(second)
    assert '"access": "write"' in tag_dependency_graph_json(first)


def test_extracts_direct_st_assignments_conditions_and_array_indices() -> None:
    graph = build_tag_dependency_graph(_controller())

    references = {
        (item.instruction, item.tag_key, item.member_path, item.access)
        for item in graph.references
    }
    assert (
        "ST_ASSIGN",
        "controller:Result",
        None,
        TagReferenceAccess.WRITE,
    ) in references
    assert (
        "ST_IF",
        "controller:Timer",
        ".DN",
        TagReferenceAccess.READ,
    ) in references
    assert (
        "ST_ASSIGN",
        "controller:Array",
        "[Index]",
        TagReferenceAccess.READ,
    ) in references
    assert (
        "ST_ASSIGN",
        "controller:Index",
        None,
        TagReferenceAccess.READ,
    ) in references
    assert any(
        item.instruction == "ST_WHILE" and item.identifier == "Missing"
        for item in graph.unresolved_references
    )


def test_preserves_resolved_and_unresolved_alias_definition_edges() -> None:
    graph = build_tag_dependency_graph(_controller())

    resolved = next(
        item
        for item in graph.references
        if item.source_tag_key == "controller:ResultAlias"
    )
    assert resolved.tag_key == "controller:Result"
    assert resolved.member_path == ".Value"
    assert resolved.access is TagReferenceAccess.ALIAS
    unresolved = next(
        item
        for item in graph.unresolved_references
        if item.source_tag_key == "controller:DirectOutputAlias"
    )
    assert unresolved.identifier == "Local:1:O.Data.1"
    assert unresolved.instruction == "ALIAS"


def _structured_ladder_controller() -> Controller:
    # Mirrors Control Expert's and CCW's own ladder capture: LadderRung.network
    # populated, LadderRung.text left None -- unlike L5X, which is the reverse.
    controller = Controller(name="PLC", identity=Identity())
    controller.add_tag(Tag(name="Start"))
    controller.add_tag(Tag(name="Output"))
    program = Program("Main")
    routine = Routine(name="Logic", language="LD")
    routine.ladder_rungs = [
        LadderRung(number=1, network=LadderSeries(elements=(
            LadderInstruction(operation=LadderOperation.NORMALLY_OPEN_CONTACT,
                              source_mnemonic="contact", operand="Start"),
            LadderInstruction(operation=LadderOperation.COIL,
                              source_mnemonic="coil", operand="Output"),
        )))
    ]
    program.add_routine(routine)
    controller.add_program(program)
    return controller


def test_structured_ladder_network_resolves_read_and_write_references() -> None:
    graph = build_tag_dependency_graph(_structured_ladder_controller())
    references = {(item.instruction, item.tag_key, item.access) for item in graph.references}
    assert ("normally_open_contact", "controller:Start", TagReferenceAccess.READ) in references
    assert ("coil", "controller:Output", TagReferenceAccess.WRITE) in references


def test_structured_ladder_network_is_skipped_when_text_is_also_present() -> None:
    # Text and network are mutually exclusive by construction across every
    # real converter, but if both were ever set, .text must win -- this
    # never double-counts a reference _ladder_calls already extracted.
    controller = _structured_ladder_controller()
    routine = controller.programs["Main"].routines["Logic"]
    routine.ladder_rungs[0].text = "XIC(Start)OTE(Output);"
    graph = build_tag_dependency_graph(controller)
    structured_style = [r for r in graph.references if r.instruction in ("coil", "normally_open_contact")]
    assert structured_style == []


def test_structured_ladder_network_resolves_parallel_branches() -> None:
    controller = Controller(name="PLC", identity=Identity())
    controller.add_tag(Tag(name="A"))
    controller.add_tag(Tag(name="B"))
    controller.add_tag(Tag(name="Output"))
    program = Program("Main")
    routine = Routine(name="Logic", language="LD")
    routine.ladder_rungs = [
        LadderRung(number=1, network=LadderSeries(elements=(
            LadderParallel(branches=(
                LadderSeries(elements=(LadderInstruction(
                    operation=LadderOperation.NORMALLY_OPEN_CONTACT, source_mnemonic="contact", operand="A"),)),
                LadderSeries(elements=(LadderInstruction(
                    operation=LadderOperation.NORMALLY_OPEN_CONTACT, source_mnemonic="contact", operand="B"),)),
            )),
            LadderInstruction(operation=LadderOperation.COIL, source_mnemonic="coil", operand="Output"),
        )))
    ]
    program.add_routine(routine)
    controller.add_program(program)
    graph = build_tag_dependency_graph(controller)
    reads = {item.tag_key for item in graph.references if item.access is TagReferenceAccess.READ}
    assert reads == {"controller:A", "controller:B"}


def test_structured_ladder_network_skips_unsupported_and_unbound_instructions() -> None:
    # An instruction shape this project has no portable meaning for (or one
    # with no operand at all) is never guessed at as a read or write -- not
    # even reported as unresolved, since the access kind itself is unknown.
    controller = Controller(name="PLC", identity=Identity())
    program = Program("Main")
    routine = Routine(name="Logic", language="LD")
    routine.ladder_rungs = [
        LadderRung(number=1, network=LadderSeries(elements=(
            LadderInstruction(operation=LadderOperation.UNSUPPORTED, source_mnemonic="textBox", operand="Mystery"),
            LadderInstruction(operation=LadderOperation.COIL, source_mnemonic="coil", operand=None),
        )))
    ]
    program.add_routine(routine)
    controller.add_program(program)
    graph = build_tag_dependency_graph(controller)
    assert graph.references == ()
    assert graph.unresolved_references == ()


def test_real_fixture_resolves_structured_ladder_references_when_available() -> None:
    import pytest
    from pathlib import Path
    from twinforge.parsers.control_expert import capture_file, parse_projects

    path = Path("reference/control-expert/Escalier_Mecanique.XEF")
    if not path.exists():
        pytest.skip("reference fixture absent")
    result, = parse_projects(capture_file(path))
    graph = build_tag_dependency_graph(result.controller)
    p_prev = {(item.instruction, item.program_name, item.routine_name, item.access)
             for item in graph.references if item.tag_name == "p_prev"}
    assert ("reset_coil", "Init_Logic", "Init_Logic", TagReferenceAccess.WRITE) in p_prev
    assert ("coil", "Rising_Edge_Detection", "Rising_Edge_Detection", TagReferenceAccess.WRITE) in p_prev
    assert ("normally_closed_contact", "Rising_Edge_Detection", "Rising_Edge_Detection",
           TagReferenceAccess.READ) in p_prev


def _step_state_controller(step_source: str) -> Controller:
    controller = Controller(name="PLC", identity=Identity())
    program = Program("Main")
    routine = Routine(name="Logic", language="ST")
    routine.structured_text_lines = [
        StructuredTextLine(number=1, text=step_source),
    ]
    program.add_routine(routine)
    controller.add_program(program)
    return controller


def test_step_state_reference_resolves_against_a_declared_step() -> None:
    # Real Control Expert shape (MultiGrafcet_Coordination_V1_2026.XEF's
    # G1_Voyants): "IF G1_0.X THEN" -- the same ".X" step-active-state
    # convention already established for LD contacts, now inside ST.
    controller = _step_state_controller("IF G1_0.X THEN X := TRUE; END_IF;")
    graph = build_tag_dependency_graph(
        controller, step_names={"g1_0": "G1_0"}, ambiguous_step_names=frozenset(),
    )
    assert len(graph.step_state_references) == 1
    reference = graph.step_state_references[0]
    assert reference.step_name == "G1_0" and reference.operand == "G1_0.X"
    assert reference.program_name == "Main" and reference.routine_name == "Logic"
    assert not any("G1_0" in u.identifier for u in graph.unresolved_references)


def test_step_state_reference_stays_ambiguous_when_the_step_name_collides() -> None:
    controller = _step_state_controller("IF G1_0.X THEN X := TRUE; END_IF;")
    graph = build_tag_dependency_graph(
        controller, step_names={"g1_0": "G1_0"}, ambiguous_step_names=frozenset({"g1_0"}),
    )
    assert graph.step_state_references == ()
    assert len(graph.ambiguous_step_state_references) == 1
    assert graph.ambiguous_step_state_references[0].identifier == "G1_0"


def test_a_declared_tag_takes_precedence_over_a_step_state_reading() -> None:
    # Symbols are checked first; a step interpretation is only attempted
    # once a name is confirmed *not* to be a declared tag -- the same
    # precedence already established for chart-control calls.
    controller = _step_state_controller("IF G1_0.X THEN X := TRUE; END_IF;")
    controller.programs["Main"].add_tag(Tag(name="G1_0"))
    graph = build_tag_dependency_graph(
        controller, step_names={"g1_0": "G1_0"}, ambiguous_step_names=frozenset(),
    )
    assert graph.step_state_references == ()
    resolved = {item.tag_key for item in graph.references}
    assert "program:Main:G1_0" in resolved


def test_step_state_resolution_is_opt_in_and_never_defaults_on() -> None:
    # Omitting step_names must behave exactly as before -- no interception,
    # matching an L5X caller with no step evidence to offer.
    controller = _step_state_controller("IF G1_0.X THEN X := TRUE; END_IF;")
    graph = build_tag_dependency_graph(controller)
    assert graph.step_state_references == ()
    assert any(u.identifier == "G1_0.X" for u in graph.unresolved_references)


def test_real_fixture_resolves_step_state_references_when_available() -> None:
    import pytest
    from pathlib import Path
    from twinforge.parsers.control_expert import capture_file, parse_projects

    path = Path("reference/control-expert/MultiGrafcet_Coordination_V1_2026.XEF")
    if not path.exists():
        pytest.skip("reference fixture absent")
    result, = parse_projects(capture_file(path))
    controller = result.controller

    step_names: dict[str, str] = {}
    step_counts: dict[str, int] = {}

    def collect_steps(elements):
        for element in elements:
            if element.kind == "step":
                name = element.properties.get("name")
                if name:
                    key = name.casefold()
                    step_counts[key] = step_counts.get(key, 0) + 1
                    step_names.setdefault(key, name)
            collect_steps(element.children)

    for program in controller.programs.values():
        for routine in program.routines.values():
            for chart in routine.sequential_charts:
                collect_steps(chart.elements)

    graph = build_tag_dependency_graph(
        controller, step_names=step_names,
        ambiguous_step_names=frozenset(k for k, c in step_counts.items() if c > 1),
    )
    resolved = {(item.step_name, item.routine_name) for item in graph.step_state_references}
    assert resolved == {("G1_0", "G1_Voyants"), ("G1_1", "G1_Voyants"), ("G1_2", "G1_Voyants")}
    assert graph.ambiguous_step_state_references == ()
    assert not any("G1_" in u.identifier for u in graph.unresolved_references)
