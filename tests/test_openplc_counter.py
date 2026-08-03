from twinforge.model import (
    LadderRung,
    Program,
    Routine,
    SourceExtension,
    SourceNode,
    Tag,
)
from twinforge.targets.openplc.counter import CounterOrder, match_counter_group


def _counter_tag(name: str = "PartCounter") -> Tag:
    members = {
        "PRE": "3",
        "ACC": "2",
        "DN": "0",
        "OV": "1",
        "UN": "0",
    }
    return Tag(
        name=name,
        data_type="COUNTER",
        source_extensions=[
            SourceExtension(
                format="l5x",
                root=SourceNode(
                    name="Tag",
                    children=[
                        SourceNode(
                            name="Data",
                            attributes={"Format": "Decorated"},
                            children=[
                                SourceNode(
                                    name="Structure",
                                    children=[
                                        SourceNode(
                                            name="DataValueMember",
                                            attributes={"Name": key, "Value": value},
                                        )
                                        for key, value in members.items()
                                    ],
                                )
                            ],
                        )
                    ],
                ),
            )
        ],
    )


def _program(*rung_texts: str) -> Program:
    program = Program(name="CounterProgram")
    program.add_tag(_counter_tag())
    routine = Routine(name="MainRoutine", language="RLL")
    routine.ladder_rungs.extend(
        LadderRung(number=index, text=text)
        for index, text in enumerate(rung_texts)
    )
    program.add_routine(routine)
    return program


def test_matches_standalone_ctd_with_initial_decorated_state() -> None:
    group = match_counter_group(
        _program(
            "XIC(PartLeft)CTD(PartCounter,?,?);",
            "XIC(PartCounter.DN)OTE(AtCapacity);",
            "XIC(ResetCount)RES(PartCounter);",
        ),
        0,
    )

    assert group is not None
    assert group.order is CounterOrder.DOWN_ONLY
    assert group.count_up_name is None
    assert group.count_down_name == "PartLeft"
    assert group.preset == 3
    assert group.initial_accumulator == 2
    assert group.initial_done is False
    assert group.initial_overflow is True
    assert group.source_rung_count == 3


def test_matches_paired_counter_and_preserves_up_then_down_order() -> None:
    group = match_counter_group(
        _program(
            "XIC(PartEntered)CTU(PartCounter,?,?);",
            "XIC(PartLeft)CTD(PartCounter,?,?);",
            "XIC(PartCounter.DN)OTE(AtCapacity);",
            "XIC(ResetCount)RES(PartCounter);",
        ),
        0,
    )

    assert group is not None
    assert group.order is CounterOrder.UP_THEN_DOWN
    assert group.count_up_name == "PartEntered"
    assert group.count_down_name == "PartLeft"
    assert group.source_rung_count == 4


def test_matches_paired_counter_and_preserves_down_then_up_order() -> None:
    group = match_counter_group(
        _program(
            "XIC(PartLeft)CTD(PartCounter,?,?);",
            "XIC(PartEntered)CTU(PartCounter,?,?);",
            "XIC(PartCounter.DN)OTE(AtCapacity);",
            "XIC(ResetCount)RES(PartCounter);",
        ),
        0,
    )

    assert group is not None
    assert group.order is CounterOrder.DOWN_THEN_UP


def test_rejects_paired_instructions_with_different_counter_tags() -> None:
    program = _program(
        "XIC(PartEntered)CTU(PartCounter,?,?);",
        "XIC(PartLeft)CTD(OtherCounter,?,?);",
        "XIC(PartCounter.DN)OTE(AtCapacity);",
        "XIC(ResetCount)RES(PartCounter);",
    )
    program.add_tag(_counter_tag("OtherCounter"))

    assert match_counter_group(program, 0) is None
