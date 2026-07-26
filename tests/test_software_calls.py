from pathlib import Path

from twinforge.analysis import extract_program_calls
from twinforge.model import (
    LadderRung,
    Program,
    Routine,
    SoftwareCallLanguage,
    StructuredTextLine,
)


def test_extracts_structured_text_calls_with_exact_named_arguments():
    program = Program("Example")
    routine = Routine(name="Logic", language="ST")
    routine.structured_text_lines = [
        StructuredTextLine(
            number=12,
            text="Drive(Axis, Enable := Start, Done => Complete);",
        )
    ]
    program.add_routine(routine)

    calls = extract_program_calls(program, source_path=Path("program.L5X"))

    assert len(calls) == 1
    call = calls[0]
    assert call.callee == "Drive"
    assert call.language is SoftwareCallLanguage.STRUCTURED_TEXT
    assert call.line_number == 12
    assert call.source_text == (
        "Drive(Axis, Enable := Start, Done => Complete)"
    )
    assert [(arg.name, arg.direction, arg.source) for arg in call.arguments] == [
        (None, None, "Axis"),
        ("Enable", ":=", "Start"),
        ("Done", "=>", "Complete"),
    ]


def test_extracts_ladder_calls_and_preserves_nested_operand_text():
    program = Program("Example")
    routine = Routine(name="Main", language="RLL")
    routine.ladder_rungs = [
        LadderRung(
            number=7,
            text=(
                "XIC(Start)Dvc_PF525(Dvc,Drive:I,"
                "Expression(A,B),\"a,b\");"
            ),
        )
    ]
    program.add_routine(routine)

    calls = extract_program_calls(program)

    assert [call.callee for call in calls] == ["XIC", "Dvc_PF525"]
    drive = calls[1]
    assert drive.language is SoftwareCallLanguage.LADDER
    assert drive.rung_number == 7
    assert [argument.source for argument in drive.arguments] == [
        "Dvc",
        "Drive:I",
        "Expression(A,B)",
        '"a,b"',
    ]
