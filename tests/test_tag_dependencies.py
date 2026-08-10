from twinforge.analysis import (
    TagReferenceAccess,
    build_tag_dependency_graph,
    tag_dependency_graph_json,
)
from twinforge.model import (
    Controller,
    Identity,
    LadderRung,
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
