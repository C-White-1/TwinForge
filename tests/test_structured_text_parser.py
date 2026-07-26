from pathlib import Path

from twinforge.model import Controller
from twinforge.parsers import L5XParser
from twinforge.structured_text import (
    AssignmentStatement,
    BinaryExpression,
    CallExpression,
    ExitStatement,
    ExpressionStatement,
    IfStatement,
    IndexExpression,
    MemberExpression,
    MissingExpression,
    NameExpression,
    UnsupportedStatement,
    WhileStatement,
    parse_structured_text,
)


DATA = Path(__file__).parent / "data/aoi"


def _controller(name: str) -> Controller:
    plant = L5XParser().parse(DATA / name, report_mode=None)
    return next(plant.iter_controllers())


def test_str_capacity_parses_losslessly_as_a_call():
    routine = _controller("Str_Capacity_AOI.L5X").add_on_instructions[
        "Str_Capacity"
    ].routines["Logic"]

    document = parse_structured_text(routine.structured_text)

    assert document.reconstructed_source == routine.structured_text
    assert document.diagnostics == ()
    assert len(document.statements) == 1
    statement = document.statements[0]
    assert isinstance(statement, ExpressionStatement)
    assert isinstance(statement.expression, CallExpression)
    assert isinstance(statement.expression.callee, NameExpression)
    assert statement.expression.callee.name == "SIZE"
    assert len(statement.expression.arguments) == 3


def test_rtc_pulse_subset_parses_assignments_if_and_logix_extensions():
    source = """\
GSV(WallClockTime, , CurrentValue, TNow);

if (Inp_Enable & NOT OSR OR Out) then
    TStart := TNow;
end_if;
OSR := Inp_Enable;
Sts_Enabled := Inp_Enable;
Out := Inp_Enable & (TNow - TStart >= Inp_Interval * 1000);
"""

    document = parse_structured_text(source)

    assert document.reconstructed_source == source
    assert document.diagnostics == ()
    assert len(document.statements) == 5
    gsv = document.statements[0]
    assert isinstance(gsv, ExpressionStatement)
    assert isinstance(gsv.expression, CallExpression)
    assert isinstance(gsv.expression.arguments[1].value, MissingExpression)
    assert isinstance(document.statements[1], IfStatement)
    assert all(
        isinstance(statement, AssignmentStatement)
        for statement in document.statements[2:]
    )
    output = document.statements[-1]
    assert isinstance(output, AssignmentStatement)
    assert isinstance(output.value, BinaryExpression)


def test_numeric_member_and_index_access_are_distinct():
    document = parse_structured_text(
        "OSR.0 := Ref_Msg.Path.DATA[0];"
    )

    assert document.diagnostics == ()
    statement = document.statements[0]
    assert isinstance(statement, AssignmentStatement)
    assert isinstance(statement.target, MemberExpression)
    assert statement.target.member == "0"


def test_codesys_named_input_and_output_arguments_are_retained():
    document = parse_structured_text(
        "fbPulse(xEnable := xEnable, xPulse => xPulse);"
    )

    assert document.diagnostics == ()
    statement = document.statements[0]
    assert isinstance(statement, ExpressionStatement)
    assert isinstance(statement.expression, CallExpression)
    arguments = statement.expression.arguments
    assert (arguments[0].name, arguments[0].direction) == (
        "xEnable",
        ":=",
    )
    assert (arguments[1].name, arguments[1].direction) == (
        "xPulse",
        "=>",
    )


def test_unsupported_statement_is_preserved_with_a_diagnostic():
    source = "CASE State OF 1: Out := TRUE; END_CASE;"

    document = parse_structured_text(source)

    assert document.reconstructed_source == source
    assert document.diagnostics
    assert isinstance(document.statements[0], UnsupportedStatement)


def test_unterminated_comment_is_preserved_with_a_diagnostic():
    source = "(* unfinished"

    document = parse_structured_text(source)

    assert document.reconstructed_source == source
    assert document.diagnostics[0].code == "unterminated_comment"


def test_while_loop_parses_with_indexed_assignments():
    source = """\
while (i < Size) do
    Ref_Buffer[i] := 0;
    i := i + 1;
end_while;
"""

    document = parse_structured_text(source)

    assert document.diagnostics == ()
    assert len(document.statements) == 1
    loop = document.statements[0]
    assert isinstance(loop, WhileStatement)
    assert len(loop.statements) == 2
    assert all(
        isinstance(statement, AssignmentStatement)
        for statement in loop.statements
    )


def test_logix_dynamic_bit_selection_and_exit_are_explicit_nodes():
    source = """\
while i <= 31 do
    if FOut.[i] then
        exit;
    end_if;
    i := i + 1;
end_while;
"""

    document = parse_structured_text(source)

    assert document.diagnostics == ()
    loop = document.statements[0]
    assert isinstance(loop, WhileStatement)
    conditional = loop.statements[0]
    assert isinstance(conditional, IfStatement)
    condition = conditional.branches[0].condition
    assert isinstance(condition, IndexExpression)
    assert condition.operator == ".[]"
    assert isinstance(
        conditional.branches[0].statements[0],
        ExitStatement,
    )
