from twinforge.analysis import extract_literal_assignments
from twinforge.model import Routine, StructuredTextLine


def test_extracts_indexed_and_scalar_integer_assignments():
    routine = Routine(name="Logic", language="ST")
    routine.structured_text_lines = [
        StructuredTextLine(
            number=10,
            text="Data[2] := 16#0026; // P038 [VoltageClass]",
        ),
        StructuredTextLine(number=11, text="Instance := 34;"),
        StructuredTextLine(number=12, text="Value := Other;"),
    ]

    evidence = extract_literal_assignments(routine)

    assert [
        (item.line_number, item.target, item.indices, item.value)
        for item in evidence
    ] == [
        (10, "Data[2]", (2,), 38),
        (11, "Instance", (), 34),
    ]
    assert evidence[0].comment == "P038 [VoltageClass]"
