from twinforge.analysis import (
    BehaviourMatch,
    PLCopenBehaviourModel,
    assess_plcopen_behaviour,
)
from twinforge.model import AddOnInstruction, AddOnInstructionParameter


def _instruction(*parameters: tuple[str, str]) -> AddOnInstruction:
    instruction = AddOnInstruction(name="Example")
    for name, usage in parameters:
        instruction.add_parameter(
            AddOnInstructionParameter(
                name=name,
                data_type="BOOL" if name != "iErrorID" else "INT",
                usage=usage,
            )
        )
    return instruction


def test_detects_complete_edge_triggered_signature():
    assessment = assess_plcopen_behaviour(
        _instruction(
            ("xExecute", "Input"),
            ("xDone", "Output"),
            ("xBusy", "Output"),
            ("xError", "Output"),
            ("iErrorID", "Output"),
        )
    )

    assert assessment.model is PLCopenBehaviourModel.EDGE_TRIGGERED
    assert assessment.match is BehaviourMatch.COMPLETE
    assert assessment.wrapper_recommended
    assert assessment.missing_parameters == ()


def test_detects_partial_level_controlled_signature_without_recommending_wrapper():
    assessment = assess_plcopen_behaviour(
        _instruction(
            ("Enable", "Input"),
            ("Valid", "Output"),
        )
    )

    assert assessment.model is PLCopenBehaviourModel.LEVEL_CONTROLLED
    assert assessment.match is BehaviourMatch.PARTIAL
    assert not assessment.wrapper_recommended
    assert assessment.missing_parameters == ("Busy", "Error", "ErrorID")


def test_does_not_confuse_logix_system_enable_parameters_with_enable_model():
    assessment = assess_plcopen_behaviour(
        _instruction(
            ("EnableIn", "Input"),
            ("EnableOut", "Output"),
        )
    )

    assert assessment.model is PLCopenBehaviourModel.NONE
    assert assessment.match is BehaviourMatch.NONE


def test_both_control_models_are_ambiguous():
    assessment = assess_plcopen_behaviour(
        _instruction(
            ("Execute", "Input"),
            ("Enable", "Input"),
        )
    )

    assert assessment.model is PLCopenBehaviourModel.AMBIGUOUS
    assert assessment.match is BehaviourMatch.AMBIGUOUS
    assert not assessment.wrapper_recommended
