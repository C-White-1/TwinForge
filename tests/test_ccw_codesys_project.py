"""Synthetic end-to-end tests for CCW-to-CODESYS project planning.

Rungs reach the PLCopen exporter as networks, not RLL text; exported rungs
are checked as power flow against their network for every input.
"""

from datetime import datetime, timezone
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from test_export_plcopen_network import assert_equivalent

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
from twinforge.cli.ccw_project import export_ccw_codesys_project
from twinforge.targets.codesys import plan_ccw_codesys_project


NS = {"p": PLCOPEN_CODESYS_NAMESPACE}
CCW_TESTS = Path(__file__).parents[1] / "reference" / "ccw-tests"
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
    converted, preserved, _ = program.routines["Sequence"].ladder_rungs
    # Networks pass through untouched; no RLL text is synthesized.
    assert converted.text is None and converted.network is not None
    assert preserved.text is None and preserved.network is not None
    assert plan.converted_rung_count == 1
    assert plan.preserved_rung_count == 1
    assert plan.empty_rung_count == 1
    assert plan.diagnostics[0].code == "ccw_rung_preserved_for_codesys"
    assert plan.coverage[1].reason == "ADD (unsupported) has no PLCopen LD encoding"
    assert program.routines["Sequence"].ladder_rungs[2].text == "NOP();"


def test_plan_converts_rung_with_two_parallel_groups_in_series() -> None:
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

    # The RLL bridge refused this: flattening it would duplicate conditions.
    # The LD graph needs no duplication.
    assert plan.converted_rung_count == 1
    assert plan.preserved_rung_count == 0
    _assert_action_exports_equivalently(plan)


def test_plan_converts_rung_with_empty_parallel_branch() -> None:
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

    # An empty branch is a wire around Start, so Motor is always powered.
    assert plan.converted_rung_count == 1
    assert plan.preserved_rung_count == 0
    _assert_action_exports_equivalently(plan)


def _assert_action_exports_equivalently(plan) -> None:
    """Export the plan and compare the action's one rung with its network."""
    (rung,) = plan.controller.programs["PLC_PRG"].routines["Sequence"].ladder_rungs
    assert rung.network is not None
    result = PLCopenExporter(PLCopenProfile.CODESYS).export(plan.controller, creation_time=FIXED_TIME)
    assert not [d for d in result.diagnostics if d.code == "unsupported_network_rung"]
    root = ET.fromstring(result.xml)
    (action,) = root.findall(".//p:action[@name='Sequence']", NS)
    (ld,) = action.findall(".//p:LD", NS)
    assert_equivalent(rung.network, list(ld))


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
    assert "Unsupported ladder network: ADD(Counter)" in comments
    assert [d.code for d in result.diagnostics] == ["unsupported_network_rung"]
    assert any("intentional no operation" in text for text in comments)


@pytest.mark.skipif(not (CCW_TESTS / "M10_Conveyor.json").exists(), reason="reference CCW project is local-only")
def test_real_project_reproduces_the_recorded_coverage_report(tmp_path: Path) -> None:
    # Recorded with the former network-to-RLL bridge; the direct network path
    # must convert exactly the same rungs.
    coverage_path = tmp_path / "coverage.json"
    export_ccw_codesys_project(
        CCW_TESTS / "M10_Conveyor.json", destination=tmp_path / "out.xml", coverage_path=coverage_path,
        task_rate_ms=20, stdout=io.StringIO(),
    )
    produced = json.loads(coverage_path.read_text(encoding="utf-8"))
    recorded = json.loads((CCW_TESTS / "M10_Conveyor_codesys.coverage.json").read_text(encoding="utf-8"))

    assert {key: produced[key] for key in recorded} == recorded
