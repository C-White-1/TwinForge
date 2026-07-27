from twinforge.analysis import (
    extract_parameter_literal_write_bindings,
    extract_parameter_setpoint_bindings,
)
from twinforge.model import AddOnInstruction, Routine, StructuredTextLine


def _implementation(source: str) -> AddOnInstruction:
    implementation = AddOnInstruction(name="Drive")
    implementation.add_routine(
        Routine(
            name="Write",
            language="ST",
            structured_text_lines=[
                StructuredTextLine(number=0, text=source)
            ],
        )
    )
    return implementation


def test_extracts_number_and_setpoint_from_the_same_parsed_branch():
    bindings = extract_parameter_setpoint_bindings(
        _implementation(
            """
            IF NeedsWrite THEN
                WriteInstance := 31;
                WriteParam := Local.Params.MotorNPVoltage.SP;
            END_IF;
            """
        )
    )

    assert bindings[31].member_name == "MotorNPVoltage"
    assert bindings[31].routine_name == "Write"
    assert "WriteInstance := 31" in bindings[31].evidence


def test_rejects_branch_with_ambiguous_setpoint_members():
    bindings = extract_parameter_setpoint_bindings(
        _implementation(
            """
            IF NeedsWrite THEN
                WriteInstance := 31;
                WriteParam := Local.Params.First.SP;
                WriteParam := Local.Params.Second.SP;
            END_IF;
            """
        )
    )

    assert 31 not in bindings


def test_rejects_conflicting_bindings_for_one_parameter_number():
    bindings = extract_parameter_setpoint_bindings(
        _implementation(
            """
            IF FirstWrite THEN
                WriteInstance := 31;
                WriteParam := Local.Params.First.SP;
            END_IF;
            IF SecondWrite THEN
                WriteInstance := 31;
                WriteParam := Local.Params.Second.SP;
            END_IF;
            """
        )
    )

    assert 31 not in bindings


def test_extracts_literal_write_as_behavior_not_setpoint_value():
    implementation = _implementation(
        """
        IF NeedsCorrection THEN
            WriteInstance := 572;
            WriteParam := 100;
        END_IF;
        """
    )

    bindings = extract_parameter_literal_write_bindings(implementation)

    assert bindings[572].lexical_value == "100"
    assert bindings[572].routine_name == "Write"
