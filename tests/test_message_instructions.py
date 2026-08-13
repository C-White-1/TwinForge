import json

from twinforge.analysis import (
    analyze_message_instructions,
    message_instruction_analysis_json,
)
from twinforge.model import (
    Controller,
    Identity,
    LadderRung,
    MessageTagConfiguration,
    Program,
    Routine,
    Tag,
)


def _controller() -> Controller:
    controller = Controller(name="PLC", identity=Identity())
    controller.add_tag(
        Tag(
            name="ReadRemote",
            data_type="MESSAGE",
            message_configuration=MessageTagConfiguration(
                message_type="CIP Data Table Read",
                destination_tag="RemoteValue",
            ),
        )
    )
    program = Program(name="MainProgram")
    program.add_tag(
        Tag(
            name="GenericRequest",
            data_type="MESSAGE",
            message_configuration=MessageTagConfiguration(
                message_type="CIP Generic",
                service_code=14,
                object_type=1,
            ),
        )
    )
    routine = Routine(name="MainRoutine", language="RLL")
    routine.ladder_rungs.extend(
        (
            LadderRung(number=0, text="XIC(Enable)MSG(ReadRemote);"),
            LadderRung(number=1, text="MSG(GenericRequest);"),
            LadderRung(number=2, text="MSG(MissingRequest);"),
            LadderRung(number=3, text="MSG();"),
        )
    )
    program.add_routine(routine)
    controller.add_program(program)
    return controller


def test_resolves_message_calls_and_identifies_cip_generic_configuration():
    result = analyze_message_instructions(_controller())

    assert [item.control_tag.name for item in result.resolved] == [
        "ReadRemote",
        "GenericRequest",
    ]
    assert result.resolved[0].owner == "controller"
    assert result.resolved[0].is_cip_generic is False
    assert result.resolved[1].owner == "program:MainProgram"
    assert result.resolved[1].is_cip_generic is True
    assert result.resolved[0].call.rung_number == 0
    assert len(result.unresolved) == 2
    assert "not present" in result.unresolved[0].reason
    assert "exactly one" in result.unresolved[1].reason
    document = json.loads(message_instruction_analysis_json(result))
    assert document["schema_version"] == "1.0"
    assert document["resolved"][1]["is_cip_generic"] is True
    assert document["resolved"][1]["rung_number"] == 1
    assert document["unresolved"][0]["control_operand"] == "MissingRequest"


def test_does_not_treat_non_msg_calls_as_message_execution():
    controller = _controller()
    controller.programs["MainProgram"].routines["MainRoutine"].ladder_rungs = [
        LadderRung(number=0, text="JSR(MSG_Routine,0);")
    ]

    result = analyze_message_instructions(controller)

    assert result.resolved == ()
    assert result.unresolved == ()
