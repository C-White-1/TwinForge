"""Machine Expert - Basic expression boxes -> typed IEC expressions."""
import pytest

from twinforge.model import LadderOperation
from twinforge.parsers.machine_expert_basic.expression import (
    ExpressionUnsupported, expression_instruction, parse_expression,
)


@pytest.mark.parametrize(("text", "rendered", "data_type"), [
    ("%MW0 > 10", "%MW0 > 10", "BOOL"),
    ("%MW1 := %MW1 + 1", "%MW1 := (%MW1 + 1)", "INT"),
    # Precedence and brackets, as in the samples.
    ("%MF1 := %MF3 * ( %MF2 * 3.0 + %MF5 ) + -99.0", "%MF1 := ((%MF3 * ((%MF2 * 3.0) + %MF5)) + -99.0)", "REAL"),
    ("%MW107 := (%mw1 +1) * 2", "%MW107 := ((%MW1 + 1) * 2)", "INT"),  # lowercase operand, as in one sample
    ("%MD0 := %MD1 / 3", "%MD0 := (%MD1 / 3)", "DINT"),
    ("%QW0.100 := 0", "%QW0.100 := 0", "INT"),
    ("%IW0.0 >= 500", "%IW0.0 >= 500", "BOOL"),
    # Shift instructions, as in the samples (spaces inside the call included).
    ("%MW10 := ROR ( %KW9 , 10 )", "%MW10 := ROR(%KW9, 10)", "INT"),
    ("%MD0 := shl(%MD1, 32)", "%MD0 := SHL(%MD1, 32)", "DINT"),
    ("%MW0 > SHR(%MW1, 2) + 1", "%MW0 > (SHR(%MW1, 2) + 1)", "BOOL"),
])
def test_parses_and_types(text, rendered, data_type):
    expression = parse_expression(text)
    assert (expression.render(), expression.data_type) == (rendered, data_type)
    assert all(node.data_type for node in expression.iter_nodes())


def test_integer_literal_adopts_a_real_context():
    expression = parse_expression("%MF1 := %MF2 * 3")
    assert expression.render() == "%MF1 := (%MF2 * 3.0)"
    assert {node.data_type for node in expression.iter_nodes()} == {"REAL"}


def test_symbols_replace_addresses_and_keep_them():
    expression = parse_expression("%MW0 > %MW1", {"%MW0": "LEVEL"})
    assert expression.left is not None and expression.right is not None
    assert (expression.left.text, expression.left.address) == ("LEVEL", "%MW0")
    assert (expression.right.text, expression.right.address) == ("%MW1", None)


@pytest.mark.parametrize(("text", "reason"), [
    ("%MW0 := %MF1", "assigns REAL to INT"),
    ("%MW0 + %MF1 > 1", "mixes types"),
    ("%TM0.P := %MW0", "member"),  # a timer preset write
    ("%MW0:X3 = 1", "member or bit"),
    # BCD conversions: no IEC name every target is evidenced to provide.
    ("%MW1 := ITB ( %KW9 )", "function ITB has no IEC equivalent"),
    ("%MW0 := BTI ( %MW10 )", "function BTI has no IEC equivalent"),
    ("%MW1 := ROR(%MW2, 17)", "not an immediate 1..16"),
    ("%MW1 := ROR(%MW2, 0)", "not an immediate 1..16"),
    ("%MW1 := ROR(%MW2, %MW3)", "not an immediate"),
    ("%MF1 := ROR(%MF2, 1)", "not a word or double word"),
    ("%MW0 := 40000", "does not fit INT"),
    ("%MW0 := -%MW1", "unary minus"),
    ("%MW0 + 1", "comparison or assignment"),
    ("%M0 = 1", "no documented numeric type"),
])
def test_refuses_what_it_cannot_type(text, reason):
    with pytest.raises(ExpressionUnsupported) as error:
        parse_expression(text)
    assert reason in str(error.value)


def test_instruction_kinds_and_fallback():
    comparison = expression_instruction("%MW0 > 10", "Comparison")
    assignment = expression_instruction("%MW1 := %MW1 + 1", "Operation", {"%MW1": "COUNT"})
    refused = expression_instruction("%TM0.P := %MW0", "Comparison")

    assert (comparison.operation, comparison.operand) == (LadderOperation.COMPARISON, "%MW0 > 10")
    assert (assignment.operation, assignment.operand) == (LadderOperation.ASSIGNMENT, "COUNT")
    assert "address=%MW1" in assignment.annotations
    assert refused.operation is LadderOperation.UNSUPPORTED and refused.expression is None
    assert any(a.startswith("reason=") for a in refused.annotations)
    for instruction in (comparison, assignment, refused):
        assert any(a.startswith("source_expression=") for a in instruction.annotations)
