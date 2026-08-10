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
    for name in ("Source", "Result", "Timer"):
        controller.add_tag(Tag(name=name))
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
        )
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
