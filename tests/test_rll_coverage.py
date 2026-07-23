from pathlib import Path

from twinforge.analysis import analyze_rll_coverage, extract_rll_mnemonics
from twinforge.model import Controller, Identity, LadderRung, Program, Routine, Tag
from twinforge.parsers import L5XParser


SAMPLE_L5X = Path(__file__).parent / "data/basic/BoosterCompressor_20260128.L5X"


def _controller_with_rungs(*texts: str) -> Controller:
    controller = Controller(name="CoveragePLC", identity=Identity())
    controller.add_tag(Tag(name="Enable", data_type="BOOL"))
    controller.add_tag(Tag(name="Output", data_type="BOOL"))
    program = Program(name="MainProgram")
    routine = Routine(name="MainRoutine", language="RLL")
    routine.ladder_rungs = [
        LadderRung(number=index, text=text)
        for index, text in enumerate(texts)
    ]
    program.add_routine(routine)
    controller.add_program(program)
    return controller


def test_extract_rll_mnemonics_ignores_nested_expression_calls() -> None:
    assert extract_rll_mnemonics(
        "XIC(Enable)CPT(Output,SIN(Value))OTE(Done);"
    ) == ("XIC", "CPT", "OTE")


def test_coverage_distinguishes_mnemonic_support_from_executable_rungs() -> None:
    controller = _controller_with_rungs(
        "XIC(Enable)OTE(Output);",
        "XIC(Enable)CPT(Output,1);",
    )

    report = analyze_rll_coverage(controller)

    assert report.total_rungs == 2
    assert report.executable_rungs == 1
    assert report.rung_coverage_percent == 50
    assert report.total_instruction_occurrences == 4
    assert report.executable_instruction_occurrences == 2
    assert report.instructions["XIC"].supported_mnemonic is True
    assert report.instructions["XIC"].occurrences == 2
    assert report.instructions["XIC"].executable_occurrences == 1
    assert report.instructions["CPT"].supported_mnemonic is False
    assert report.issues[0].reason == "unsupported_rll_rung"


def test_booster_compressor_has_complete_current_rung_coverage() -> None:
    plant = L5XParser().parse(SAMPLE_L5X, report_mode=None)
    controller = next(plant.iter_controllers())

    report = analyze_rll_coverage(controller)

    assert report.total_rungs > 0
    assert report.executable_rungs == report.total_rungs
    assert (
        report.executable_instruction_occurrences
        == report.total_instruction_occurrences
    )
    assert report.issues == []


def test_res_on_non_timer_is_reported_instead_of_failing_analysis() -> None:
    controller = _controller_with_rungs("RES(Output);")

    report = analyze_rll_coverage(controller)

    assert report.executable_rungs == 0
    assert report.issues[0].reason == "unsupported_timer_operand"
