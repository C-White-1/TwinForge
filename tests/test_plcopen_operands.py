from twinforge.exporters.plcopen_operands import PLCopenOperandPlanner
from twinforge.model import Controller, Identity, LadderRung, Program, Routine, Tag


def _controller_with_rungs(*texts: str) -> Controller:
    """Build the smallest controller needed for operand-planning tests."""

    controller = Controller(name="TestPLC", identity=Identity())
    program = Program(name="PLC_PRG")
    routine = Routine(name="MainRoutine", language="RLL")
    routine.ladder_rungs = [
        LadderRung(number=index, text=text)
        for index, text in enumerate(texts)
    ]
    program.add_routine(routine)
    controller.add_program(program)
    return controller


def test_raw_rockwell_operand_gets_deterministic_surrogate() -> None:
    controller = _controller_with_rungs(
        "XIC(Local:1:I.Data.0)OTE(Output:2:O.Data.1);"
    )

    first = PLCopenOperandPlanner().prepare(controller)
    second = PLCopenOperandPlanner().prepare(controller)

    assert first == second
    assert first.portable_operand("Local:1:I.Data.0") == "TF_Local_1_I_Data_0"
    assert (
        first.portable_operand("Output:2:O.Data.1")
        == "TF_Output_2_O_Data_1"
    )
    assert [tag.name for tag in first.generated_tags] == [
        "TF_Local_1_I_Data_0",
        "TF_Output_2_O_Data_1",
    ]
    assert [diagnostic.raw_value for diagnostic in first.diagnostics] == [
        "Local:1:I.Data.0",
        "Output:2:O.Data.1",
    ]


def test_alias_name_reuses_raw_target_without_generated_tag() -> None:
    controller = _controller_with_rungs("XIC(Local:1:I.Data.0)OTE(Result);")
    controller.add_tag(
        Tag(
            name="StartInput",
            tag_type="Alias",
            alias_for="Local:1:I.Data.0",
        )
    )
    controller.add_tag(Tag(name="Result", data_type="BOOL"))

    plan = PLCopenOperandPlanner().prepare(controller)

    assert plan.portable_operand("Local:1:I.Data.0") == "StartInput"
    assert plan.generated_tags == ()
    assert plan.diagnostics == ()
    assert plan.tag_export_type(controller.tags["StartInput"]) == "BOOL"


def test_timer_without_preset_gets_explicit_zero_and_state_symbols() -> None:
    controller = _controller_with_rungs("XIC(Enable)TON(DelayTimer,?,?);")
    controller.add_tag(Tag(name="Enable", data_type="BOOL"))
    controller.add_tag(Tag(name="DelayTimer", data_type="TIMER"))

    plan = PLCopenOperandPlanner().prepare(controller)

    timer = plan.timers["DelayTimer"]
    assert timer.preset_ms == 0
    assert (
        timer.input_name,
        timer.done_name,
        timer.elapsed_name,
        timer.executed_name,
    ) == (
        "TF_DelayTimer_IN",
        "TF_DelayTimer_DN",
        "TF_DelayTimer_ET",
        "TF_DelayTimer_Executed",
    )
    assert any(
        diagnostic.code == "timer_preset_missing"
        for diagnostic in plan.diagnostics
    )


def test_oneshot_uses_target_trigger_type_and_program_scope() -> None:
    controller = _controller_with_rungs(
        "XIC(Enable)ONS(Storage)OTE(Pulse);"
    )
    controller.add_tag(Tag(name="Enable", data_type="BOOL"))
    controller.add_tag(Tag(name="Storage", data_type="BOOL"))
    controller.add_tag(Tag(name="Pulse", data_type="BOOL"))
    rung = controller.programs["PLC_PRG"].routines["MainRoutine"].ladder_rungs[0]

    plan = PLCopenOperandPlanner(
        rising_trigger_type="Standard.R_TRIG"
    ).prepare(controller)

    oneshot = plan.oneshots[id(rung)]
    assert oneshot.instance_name == "TF_ONS_PLC_PRG_MainRoutine_0_FB"
    tags = plan.oneshot_tags["PLC_PRG"]
    assert [tag.name for tag in tags] == [
        "TF_ONS_PLC_PRG_MainRoutine_0_FB",
        "TF_ONS_PLC_PRG_MainRoutine_0_IN",
        "TF_ONS_PLC_PRG_MainRoutine_0_Pulse",
        "TF_ONS_PLC_PRG_MainRoutine_0_Executed",
    ]
    assert tags[0].metadata["plcopen_derived_type"] == "Standard.R_TRIG"


def test_structured_comparison_is_left_for_unsupported_rung_handling() -> None:
    controller = _controller_with_rungs("EQU(DeviceState,ExpectedState)OTE(Equal);")
    controller.add_tag(Tag(name="DeviceState", data_type="DriveStatus"))
    controller.add_tag(Tag(name="ExpectedState", data_type="DriveStatus"))
    controller.add_tag(Tag(name="Equal", data_type="BOOL"))
    rung = controller.programs["PLC_PRG"].routines["MainRoutine"].ladder_rungs[0]

    plan = PLCopenOperandPlanner().prepare(controller)

    assert id(rung) in plan.unsupported_comparison_rungs
    assert plan.comparison_temps == {}
    assert plan.comparison_tags == {}


def test_reusing_planner_does_not_leak_symbols_between_controllers() -> None:
    planner = PLCopenOperandPlanner()
    first = planner.prepare(
        _controller_with_rungs("XIC(Local:1:I.Data.0)OTE(Result);")
    )
    second = planner.prepare(
        _controller_with_rungs("XIC(Local:2:I.Data.0)OTE(Result);")
    )

    assert "Local:1:I.Data.0" in first.operand_names
    assert "Local:1:I.Data.0" not in second.operand_names
    assert "Local:2:I.Data.0" in second.operand_names
