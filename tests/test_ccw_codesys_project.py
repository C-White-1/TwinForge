"""Synthetic end-to-end tests for CCW-to-CODESYS project planning."""

from datetime import datetime, timezone
import xml.etree.ElementTree as ET

from twinforge.exporters import (
    PLCOPEN_CODESYS_NAMESPACE,
    PLCopenExporter,
    PLCopenProfile,
)
from twinforge.model import (
    Controller,
    Identity,
    LadderInstruction,
    LadderOperation,
    LadderParallel,
    LadderRung,
    LadderSeries,
    Program,
    Routine,
    Tag,
)
from twinforge.targets.codesys import plan_ccw_codesys_project


NS = {"p": PLCOPEN_CODESYS_NAMESPACE}
FIXED_TIME = datetime(2026, 8, 28, tzinfo=timezone.utc)


def _instruction(
    operation: LadderOperation,
    mnemonic: str,
    operand: str,
) -> LadderInstruction:
    return LadderInstruction(operation, mnemonic, operand)


def _plan():
    controller = Controller(
        name="Synthetic Parallel Conveyor",
        identity=Identity(),
    )
    for name in ("Permit", "Start", "Seal", "Fault", "Motor"):
        controller.add_tag(Tag(name=name, data_type="BOOL"))
    program = Program(name="Sequence")
    routine = Routine(name="Sequence", language="LD")
    routine.ladder_rungs.extend(
        [
            LadderRung(
                number=1,
                network=LadderSeries(
                    (
                        _instruction(
                            LadderOperation.NORMALLY_OPEN_CONTACT,
                            "XIC",
                            "Permit",
                        ),
                        LadderParallel(
                            (
                                LadderSeries(
                                    (
                                        _instruction(
                                            LadderOperation.NORMALLY_OPEN_CONTACT,
                                            "XIC",
                                            "Start",
                                        ),
                                    )
                                ),
                                LadderSeries(
                                    (
                                        _instruction(
                                            LadderOperation.NORMALLY_OPEN_CONTACT,
                                            "XIC",
                                            "Seal",
                                        ),
                                    )
                                ),
                            )
                        ),
                        _instruction(
                            LadderOperation.NORMALLY_CLOSED_CONTACT,
                            "XIO",
                            "Fault",
                        ),
                        _instruction(LadderOperation.COIL, "OTE", "Motor"),
                    )
                ),
            ),
            LadderRung(
                number=2,
                network=LadderSeries(
                    (
                        _instruction(
                            LadderOperation.UNSUPPORTED,
                            "ADD",
                            "Counter",
                        ),
                    )
                ),
            ),
            LadderRung(number=3, network=LadderSeries(())),
        ]
    )
    program.add_routine(routine)
    controller.add_program(program)
    return plan_ccw_codesys_project(controller)


def test_plan_creates_plc_prg_actions_task_and_coverage() -> None:
    plan = _plan()

    program = plan.controller.programs["PLC_PRG"]
    assert tuple(program.routines) == ("MainRoutine", "Sequence")
    assert program.main_routine is program.routines["MainRoutine"]
    main = program.main_routine
    assert main is not None
    assert main.ladder_rungs[0].text == "JSR(Sequence,0);"
    assert plan.controller.tasks["MainTask"].scheduled_programs == [program]
    assert plan.controller.tasks["MainTask"].rate == 20
    assert program.routines["Sequence"].ladder_rungs[0].text == (
        "XIC(Permit)[XIC(Start),XIC(Seal)]XIO(Fault)OTE(Motor);"
    )
    assert "UNSUPPORTED_CCW(ADD(Counter))" in (
        program.routines["Sequence"].ladder_rungs[1].text or ""
    )
    assert plan.converted_rung_count == 1
    assert plan.preserved_rung_count == 1
    assert plan.empty_rung_count == 1
    assert plan.diagnostics[0].code == "ccw_rung_preserved_for_codesys"
    assert program.routines["Sequence"].ladder_rungs[2].text == "NOP();"


def test_plan_preserves_rung_with_two_parallel_groups_in_series() -> None:
    controller = Controller(name="Synthetic Two Parallels", identity=Identity())
    for name in ("Permit", "Start", "Seal", "SecondEnable", "A", "B", "Motor"):
        controller.add_tag(Tag(name=name, data_type="BOOL"))
    program = Program(name="Sequence")
    routine = Routine(name="Sequence", language="LD")
    routine.ladder_rungs.append(
        LadderRung(
            number=1,
            network=LadderSeries(
                (
                    _instruction(
                        LadderOperation.NORMALLY_OPEN_CONTACT, "XIC", "Permit"
                    ),
                    LadderParallel(
                        (
                            LadderSeries(
                                (
                                    _instruction(
                                        LadderOperation.NORMALLY_OPEN_CONTACT,
                                        "XIC",
                                        "Start",
                                    ),
                                )
                            ),
                            LadderSeries(
                                (
                                    _instruction(
                                        LadderOperation.NORMALLY_OPEN_CONTACT,
                                        "XIC",
                                        "Seal",
                                    ),
                                )
                            ),
                        )
                    ),
                    _instruction(
                        LadderOperation.NORMALLY_OPEN_CONTACT,
                        "XIC",
                        "SecondEnable",
                    ),
                    LadderParallel(
                        (
                            LadderSeries(
                                (
                                    _instruction(
                                        LadderOperation.NORMALLY_OPEN_CONTACT,
                                        "XIC",
                                        "A",
                                    ),
                                )
                            ),
                            LadderSeries(
                                (
                                    _instruction(
                                        LadderOperation.NORMALLY_OPEN_CONTACT,
                                        "XIC",
                                        "B",
                                    ),
                                )
                            ),
                        )
                    ),
                    _instruction(LadderOperation.COIL, "OTE", "Motor"),
                )
            ),
        )
    )
    program.add_routine(routine)
    controller.add_program(program)

    plan = plan_ccw_codesys_project(controller)

    assert plan.converted_rung_count == 0
    assert plan.preserved_rung_count == 1
    rung_text = plan.controller.programs["PLC_PRG"].routines["Sequence"].ladder_rungs[0].text
    assert rung_text is not None
    assert rung_text.startswith("UNSUPPORTED_CCW(")
    assert plan.coverage[0].reason is not None
    assert "duplicate" in plan.coverage[0].reason


def test_plan_preserves_rung_with_empty_parallel_branch() -> None:
    controller = Controller(name="Synthetic Empty Branch", identity=Identity())
    for name in ("Start", "Motor"):
        controller.add_tag(Tag(name=name, data_type="BOOL"))
    program = Program(name="Sequence")
    routine = Routine(name="Sequence", language="LD")
    routine.ladder_rungs.append(
        LadderRung(
            number=1,
            network=LadderSeries(
                (
                    LadderParallel(
                        (
                            LadderSeries(()),
                            LadderSeries(
                                (
                                    _instruction(
                                        LadderOperation.NORMALLY_OPEN_CONTACT,
                                        "XIC",
                                        "Start",
                                    ),
                                )
                            ),
                        )
                    ),
                    _instruction(LadderOperation.COIL, "OTE", "Motor"),
                )
            ),
        )
    )
    program.add_routine(routine)
    controller.add_program(program)

    plan = plan_ccw_codesys_project(controller)

    assert plan.converted_rung_count == 0
    assert plan.preserved_rung_count == 1
    rung_text = plan.controller.programs["PLC_PRG"].routines["Sequence"].ladder_rungs[0].text
    assert rung_text is not None
    assert rung_text.startswith("UNSUPPORTED_CCW(")


def test_plan_exports_importable_codesys_shape_and_preserved_comment() -> None:
    plan = _plan()

    result = PLCopenExporter(PLCopenProfile.CODESYS).export(
        plan.controller,
        project_name="Synthetic Parallel Conveyor",
        creation_time=FIXED_TIME,
    )
    root = ET.fromstring(result.xml)

    assert root.find(".//p:pou[@name='PLC_PRG']", NS) is not None
    assert root.find(".//p:action[@name='Sequence']", NS) is not None
    assert root.find(".//p:task[@name='MainTask']", NS) is not None
    assert root.find(".//p:contact[p:variable='Start']", NS) is not None
    assert root.find(".//p:contact[p:variable='Permit']", NS) is not None
    assert len(root.findall(".//p:contact[p:variable='Permit']", NS)) == 1
    assert len(root.findall(".//p:contact[p:variable='Fault']", NS)) == 1
    assert root.find(".//p:coil[p:variable='Motor']", NS) is not None
    comments = [
        element.text or "" for element in root.findall(".//p:comment/p:content/*", NS)
    ]
    assert any("Unsupported Rockwell RLL" in text for text in comments)
    assert any("intentional no operation" in text for text in comments)
