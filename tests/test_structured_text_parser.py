from pathlib import Path

from twinforge.model import Controller
from twinforge.parsers import L5XParser
from twinforge.structured_text import (
    AssignmentStatement,
    BinaryExpression,
    CallExpression,
    DirectAddressExpression,
    ExitStatement,
    ExpressionStatement,
    IfStatement,
    IndexExpression,
    JumpStatement,
    LabelStatement,
    MemberExpression,
    MissingExpression,
    NameExpression,
    ParenthesizedExpression,
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


def test_label_and_jmp_are_explicit_nodes_not_unsupported():
    # Real Control Expert shape (estradege_m580-safety.xef's E_VALVE1): a
    # label stands alone on its own line, unrelated statements follow it in
    # the same statement list, and JMP elsewhere targets it by name.
    source = """\
if X then
    JMP SAFE_CMD;
end_if;

SAFE_CMD:
_OUT := FALSE;
"""

    document = parse_structured_text(source)

    assert document.diagnostics == ()
    conditional = document.statements[0]
    assert isinstance(conditional, IfStatement)
    jump = conditional.branches[0].statements[0]
    assert isinstance(jump, JumpStatement)
    assert jump.label == "SAFE_CMD"
    label = document.statements[1]
    assert isinstance(label, LabelStatement)
    assert label.name == "SAFE_CMD"
    assignment = document.statements[2]
    assert isinstance(assignment, AssignmentStatement)


def test_label_followed_only_by_a_comment_then_a_separate_statement():
    # Real shape: "SAFE_CMD: (* comment *)" on one line, the labeled
    # program point's own first real statement on the next.
    source = "CMD_ACTION: (* comment *)\nX := TRUE;\n"

    document = parse_structured_text(source)

    assert document.diagnostics == ()
    assert len(document.statements) == 2
    assert isinstance(document.statements[0], LabelStatement)
    assert document.statements[0].name == "CMD_ACTION"
    assert isinstance(document.statements[1], AssignmentStatement)


def test_jmp_missing_a_label_is_diagnosed_not_guessed():
    document = parse_structured_text("JMP;\n")

    assert any(d.code == "missing_jump_label" for d in document.diagnostics)
    assert isinstance(document.statements[0], UnsupportedStatement)


def test_assignment_target_named_jmp_or_a_colon_shaped_prefix_still_reconstructs():
    # The lossless-reconstruction contract must hold for the new tokens too.
    source = "SAFE_CMD:\nJMP OTHER;\nX := 1;\n"
    document = parse_structured_text(source)
    assert document.reconstructed_source == source


def test_real_fixture_resolves_labels_and_jumps_when_available():
    import pytest
    from twinforge.parsers.control_expert import capture_file, parse_projects

    path = Path(__file__).resolve().parents[1] / "reference" / "control-expert" / "estradege_m580-safety.xef"
    if not path.exists():
        pytest.skip("reference fixture absent")
    result, = parse_projects(capture_file(path))
    controller = result.controller

    def all_routines():
        for program in controller.programs.values():
            for routine in program.routines.values():
                yield routine
        for aoi in controller.add_on_instructions.values():
            for routine in aoi.routines.values():
                yield routine

    labels = jumps = unsupported = 0
    for routine in all_routines():
        source = routine.structured_text
        if not source:
            continue
        document = parse_structured_text(source)
        for statement in document.statements:
            if isinstance(statement, LabelStatement):
                labels += 1
            elif isinstance(statement, JumpStatement):
                jumps += 1
            elif isinstance(statement, UnsupportedStatement):
                unsupported += 1
    # Real result measured directly against this fixture: 37 labels and 20
    # jumps now resolve as their own nodes (E_VALVE1, E_MOT1, E_FG, ...
    # share the same GOTO-style pattern); unsupported statements dropped
    # from 271 (label/jump support landed first: to 117; %-direct-address
    # support landed next: to 71) across the whole corpus once both landed
    # -- entirely attributable to this one fixture, the only one with
    # substantial ST.
    assert labels == 37 and jumps == 20
    assert unsupported == 71


def test_direct_address_is_an_explicit_node_in_a_call_argument_and_assignment():
    # Real Control Expert shapes: RESET(%S18); and _alarms.5 := %S18;
    source = "RESET(%S18);\n_alarms.5 := %S18;\n"

    document = parse_structured_text(source)

    assert document.diagnostics == ()
    call_statement = document.statements[0]
    assert isinstance(call_statement, ExpressionStatement)
    assert isinstance(call_statement.expression, CallExpression)
    argument = call_statement.expression.arguments[0].value
    assert isinstance(argument, DirectAddressExpression)
    assert argument.address == "%S18"
    assignment = document.statements[1]
    assert isinstance(assignment, AssignmentStatement)
    assert isinstance(assignment.value, DirectAddressExpression)
    assert assignment.value.address == "%S18"


def test_direct_address_inside_a_parenthesized_binary_comparison():
    # Real shape: "(%SW12 = 16#A501) and (%SW13 = 16#501A)".
    document = parse_structured_text("R := (%SW12 = 16#A501) and (%SW13 = 16#501A);")

    assert document.diagnostics == ()
    assignment = document.statements[0]
    assert isinstance(assignment, AssignmentStatement)
    outer = assignment.value
    assert isinstance(outer, BinaryExpression) and outer.operator.upper() == "AND"
    left_paren = outer.left
    assert isinstance(left_paren, ParenthesizedExpression)
    left = left_paren.expression
    assert isinstance(left, BinaryExpression)
    assert isinstance(left.left, DirectAddressExpression) and left.left.address == "%SW12"


def test_malformed_direct_address_is_diagnosed_not_guessed():
    document = parse_structured_text("R := %6;\n")
    assert any(d.code == "malformed_direct_address" for d in document.diagnostics)
    assert document.reconstructed_source == "R := %6;\n"


def test_direct_address_lossless_reconstruction():
    source = "IF %S6 AND SIM THEN\n  X := %SW30;\nEND_IF;\n"
    document = parse_structured_text(source)
    assert document.reconstructed_source == source
