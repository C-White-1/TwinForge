import json
from pathlib import Path
from typing import Any

import pytest

from twinforge.model import (
    Controller,
    Identity,
    LadderRung,
    Program,
    Routine,
    SourceExtension,
    SourceNode,
    Tag,
    Task,
)
from twinforge.targets.openplc import (
    OpenPLCNativeProjectExporter,
    OpenPLCNativeUnsupportedError,
)


def _controller(
    rung_text: str = "XIC(Enable)OTE(Output);",
    program_name: str = "main",
) -> Controller:
    controller = Controller(name="OpenPLCSmoke", identity=Identity())
    program = Program(name=program_name)
    program.add_tag(Tag(name="Enable", data_type="BOOL"))
    program.add_tag(Tag(name="Output", data_type="BOOL"))
    routine = Routine(name="MainRoutine", language="RLL")
    routine.ladder_rungs.append(LadderRung(number=0, text=rung_text))
    program.add_routine(routine)
    controller.add_program(program)
    controller.add_task(
        Task(
            name="task0",
            task_type="Periodic",
            rate=20,
            priority=1,
            scheduled_program_names=[program.name],
            scheduled_programs=[program],
        )
    )
    return controller


def _serial_controller() -> Controller:
    """Build the independently evidenced two-contact AND rung."""

    controller = _controller("XIC(GuardClosed)XIC(Start)OTE(MotorRun);")
    program = next(iter(controller.programs.values()))
    program.tags.clear()
    for name in ("GuardClosed", "Start", "MotorRun"):
        program.add_tag(Tag(name=name, data_type="BOOL"))
    return controller


def _parallel_controller() -> Controller:
    """Build the independently evidenced two-contact OR branch."""

    controller = _controller("[XIC(LocalStart),XIC(RemoteStart)]OTE(MotorRun);")
    program = next(iter(controller.programs.values()))
    program.tags.clear()
    for name in ("LocalStart", "RemoteStart", "MotorRun"):
        program.add_tag(Tag(name=name, data_type="BOOL"))
    return controller


def _seal_in_controller() -> Controller:
    """Build the evidenced stop/start/holding-contact seal-in rung."""

    text = "[XIC(Start),XIC(SystemActive)]XIO(StopPressed)OTE(SystemActive);"
    controller = _controller(text)
    program = next(iter(controller.programs.values()))
    program.tags.clear()
    for name in ("Start", "StopPressed", "SystemActive"):
        program.add_tag(Tag(name=name, data_type="BOOL"))
    return controller


def _timer_controller(instruction: str = "TON") -> Controller:
    """Build a canonical Rockwell timer rung followed by its DN consumer."""

    controller = _controller(f"XIC(Enable){instruction}(DelayTimer,?,?);")
    program = next(iter(controller.programs.values()))
    program.tags.clear()
    program.add_tag(Tag(name="Enable", data_type="BOOL"))
    program.add_tag(
        Tag(
            name="DelayTimer",
            data_type="TIMER",
            source_extensions=[
                SourceExtension(
                    format="l5x",
                    root=SourceNode(
                        name="Tag",
                        children=[
                            SourceNode(
                                name="Data",
                                attributes={"Format": "Decorated"},
                                children=[
                                    SourceNode(
                                        name="Structure",
                                        children=[
                                            SourceNode(
                                                name="DataValueMember",
                                                attributes={
                                                    "Name": "PRE",
                                                    "Value": "5000",
                                                },
                                            )
                                        ],
                                    )
                                ],
                            )
                        ],
                    ),
                )
            ],
        )
    )
    program.add_tag(Tag(name="Output", data_type="BOOL"))
    routine = program.main_routine
    assert routine is not None
    routine.ladder_rungs.append(
        LadderRung(number=1, text="XIC(DelayTimer.DN)OTE(Output);")
    )
    if instruction == "RTO":
        program.add_tag(Tag(name="ResetTimer", data_type="BOOL"))
        routine.ladder_rungs.append(
            LadderRung(number=2, text="XIC(ResetTimer)RES(DelayTimer);")
        )
    return controller


def _counter_controller() -> Controller:
    """Build the runtime-proven Rockwell CTU/DN/RES sequence."""

    controller = _controller("XIC(CountPulse)CTU(PartCounter,?,?);")
    program = next(iter(controller.programs.values()))
    program.tags.clear()
    for name in ("CountPulse", "ResetCounter", "Done"):
        program.add_tag(Tag(name=name, data_type="BOOL"))
    program.add_tag(
        Tag(
            name="PartCounter",
            data_type="COUNTER",
            source_extensions=[
                SourceExtension(
                    format="l5x",
                    root=SourceNode(
                        name="Tag",
                        children=[
                            SourceNode(
                                name="Data",
                                attributes={"Format": "Decorated"},
                                children=[
                                    SourceNode(
                                        name="Structure",
                                        children=[
                                            SourceNode(
                                                name="DataValueMember",
                                                attributes={
                                                    "Name": "PRE",
                                                    "Value": "3",
                                                },
                                            )
                                        ],
                                    )
                                ],
                            )
                        ],
                    ),
                )
            ],
        )
    )
    routine = program.main_routine
    assert routine is not None
    routine.ladder_rungs.extend(
        [
            LadderRung(number=1, text="XIC(PartCounter.DN)OTE(Done);"),
            LadderRung(number=2, text="XIC(ResetCounter)RES(PartCounter);"),
        ]
    )
    return controller


def _shared_counter_controller(
    *,
    paired: bool = False,
    down_first: bool = False,
) -> Controller:
    """Build standalone CTD or paired CTU/CTD specification evidence."""

    controller = _counter_controller()
    program = next(iter(controller.programs.values()))
    program.add_tag(Tag(name="CountDown", data_type="BOOL"))
    counter = program.tags["PartCounter"]
    structure = counter.source_extensions[0].root.children[0].children[0]
    structure.children.append(
        SourceNode(
            name="DataValueMember",
            attributes={"Name": "ACC", "Value": "3"},
        )
    )
    routine = program.main_routine
    assert routine is not None
    up = LadderRung(number=0, text="XIC(CountPulse)CTU(PartCounter,?,?);")
    down = LadderRung(number=1, text="XIC(CountDown)CTD(PartCounter,?,?);")
    counts = [down]
    if paired:
        counts = [down, up] if down_first else [up, down]
    routine.ladder_rungs[:] = [
        *counts,
        LadderRung(number=2, text="XIC(PartCounter.DN)OTE(Done);"),
        LadderRung(number=3, text="XIC(ResetCounter)RES(PartCounter);"),
    ]
    return controller


def _ladder_json(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    start = text.index("{")
    end = text.rindex("}") + 1
    value = json.loads(text[start:end])
    return value


def test_exports_evidenced_native_openplc_project(tmp_path: Path) -> None:
    destination = tmp_path / "project"

    result = OpenPLCNativeProjectExporter().export(
        _controller(),
        destination=destination,
        project_name="TwinForge Smoke",
    )

    assert result.destination == destination
    assert {path.relative_to(destination).as_posix() for path in result.files} == {
        "project.json",
        "devices/configuration.json",
        "devices/pin-mapping.json",
        "pous/programs/main.ld",
    }
    project = json.loads((destination / "project.json").read_text())
    resource = project["data"]["configuration"]["resource"]
    assert resource["tasks"] == [
        {
            "name": "task0",
            "triggering": "Cyclic",
            "interval": "T#20ms",
            "priority": 1,
        }
    ]
    assert resource["instances"] == [
        {"name": "instance0", "task": "task0", "program": "main"}
    ]
    ladder = _ladder_json(destination / "pous/programs/main.ld")
    rung = ladder["rungs"][0]
    assert [node["type"] for node in rung["nodes"]] == [
        "powerRail",
        "contact",
        "coil",
        "powerRail",
    ]
    assert [edge["sourceHandle"] for edge in rung["edges"]] == [
        "left-rail",
        "output",
        "output",
    ]


def test_plans_native_project_without_writing_files(tmp_path: Path) -> None:
    destination = tmp_path / "project"

    plan = OpenPLCNativeProjectExporter().plan(_controller())

    assert not destination.exists()
    assert plan.source_program_name == "main"
    assert set(plan.documents) == {
        Path("project.json"),
        Path("devices/configuration.json"),
        Path("devices/pin-mapping.json"),
        Path("pous/programs/main.ld"),
    }
    assert '"type": "contact"' in plan.documents[
        Path("pous/programs/main.ld")
    ]


def test_native_openplc_project_is_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    exporter = OpenPLCNativeProjectExporter()

    exporter.export(_controller(), destination=first)
    exporter.export(_controller(), destination=second)

    first_files = {
        path.relative_to(first): path.read_bytes()
        for path in first.rglob("*")
        if path.is_file()
    }
    second_files = {
        path.relative_to(second): path.read_bytes()
        for path in second.rglob("*")
        if path.is_file()
    }
    assert first_files == second_files


def test_maps_source_program_to_required_lowercase_main(tmp_path: Path) -> None:
    destination = tmp_path / "mapped"

    result = OpenPLCNativeProjectExporter().export(
        _controller(program_name="PLC_PRG"),
        destination=destination,
    )

    assert result.source_program_name == "PLC_PRG"
    assert result.native_program_name == "main"
    assert (destination / "pous/programs/main.ld").is_file()
    assert not (destination / "pous/programs/PLC_PRG.ld").exists()
    project = json.loads((destination / "project.json").read_text())
    instances = project["data"]["configuration"]["resource"]["instances"]
    assert instances[0]["program"] == "main"


def test_native_project_can_explicitly_select_compile_only(tmp_path: Path) -> None:
    destination = tmp_path / "compile-only"

    OpenPLCNativeProjectExporter().export(
        _controller(),
        destination=destination,
        compile_only=True,
    )

    configuration = json.loads((destination / "devices/configuration.json").read_text())
    assert configuration["compileOnly"] is True


def test_emits_evidenced_bool_locations_in_declaration_only(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "located"

    OpenPLCNativeProjectExporter().export(
        _controller(),
        destination=destination,
        locations={"Enable": "%QX0.0", "Output": "%QX0.1"},
    )

    path = destination / "pous/programs/main.ld"
    text = path.read_text()
    assert "Enable : bool AT %QX0.0;" in text
    assert "Output : bool AT %QX0.1;" in text
    ladder = _ladder_json(path)
    variables = [
        node["data"]["variable"]
        for node in ladder["rungs"][0]["nodes"]
        if node["type"] in {"contact", "coil"}
    ]
    assert [variable["location"] for variable in variables] == ["", ""]


def test_exports_serial_contacts_and_input_locations(tmp_path: Path) -> None:
    destination = tmp_path / "serial-and"

    OpenPLCNativeProjectExporter().export(
        _serial_controller(),
        destination=destination,
        locations={
            "GuardClosed": "%IX0.0",
            "Start": "%IX0.1",
            "MotorRun": "%QX0.0",
        },
    )

    path = destination / "pous/programs/main.ld"
    text = path.read_text()
    assert "GuardClosed : bool AT %IX0.0;" in text
    assert "Start : bool AT %IX0.1;" in text
    assert "MotorRun : bool AT %QX0.0;" in text
    rung = _ladder_json(path)["rungs"][0]
    assert [node["type"] for node in rung["nodes"]] == [
        "powerRail",
        "contact",
        "contact",
        "coil",
        "powerRail",
    ]
    assert [
        node["data"]["variable"]["name"]
        for node in rung["nodes"]
        if node["type"] in {"contact", "coil"}
    ] == ["GuardClosed", "Start", "MotorRun"]
    assert [edge["sourceHandle"] for edge in rung["edges"]] == [
        "left-rail",
        "output",
        "output",
        "output",
    ]


def test_exports_two_path_parallel_or_rung(tmp_path: Path) -> None:
    destination = tmp_path / "parallel-or"

    OpenPLCNativeProjectExporter().export(
        _parallel_controller(),
        destination=destination,
        locations={
            "LocalStart": "%IX0.0",
            "RemoteStart": "%IX0.1",
            "MotorRun": "%QX0.0",
        },
    )

    rung = _ladder_json(destination / "pous/programs/main.ld")["rungs"][0]
    assert [node["type"] for node in rung["nodes"]] == [
        "powerRail",
        "parallel",
        "contact",
        "contact",
        "parallel",
        "coil",
        "powerRail",
    ]
    parallel = [node for node in rung["nodes"] if node["type"] == "parallel"]
    assert [node["data"]["type"] for node in parallel] == ["open", "close"]
    assert parallel[0]["data"]["parallelCloseReference"] == parallel[1]["id"]
    assert parallel[1]["data"]["parallelOpenReference"] == parallel[0]["id"]
    assert [edge["sourceHandle"] for edge in rung["edges"]] == [
        "left-rail",
        "output-right",
        "output",
        "output-down",
        "output",
        "output-right",
        "output",
    ]


def test_exports_seal_in_rung_with_negated_stop(tmp_path: Path) -> None:
    destination = tmp_path / "seal-in"

    OpenPLCNativeProjectExporter().export(
        _seal_in_controller(),
        destination=destination,
        locations={
            "Start": "%QX0.0",
            "StopPressed": "%QX0.1",
            "SystemActive": "%QX0.2",
        },
    )

    rung = _ladder_json(destination / "pous/programs/main.ld")["rungs"][0]
    assert [node["type"] for node in rung["nodes"]] == [
        "powerRail",
        "contact",
        "parallel",
        "contact",
        "contact",
        "parallel",
        "coil",
        "powerRail",
    ]
    contacts = [node for node in rung["nodes"] if node["type"] == "contact"]
    assert [node["data"]["variable"]["name"] for node in contacts] == [
        "StopPressed",
        "Start",
        "SystemActive",
    ]
    assert [node["data"]["variant"] for node in contacts] == [
        "negated",
        "default",
        "default",
    ]
    assert [edge["sourceHandle"] for edge in rung["edges"]] == [
        "left-rail",
        "output",
        "output-right",
        "output",
        "output-down",
        "output",
        "output-right",
        "output",
    ]


def test_exports_fail_safe_healthy_stop_as_positive_contact(tmp_path: Path) -> None:
    controller = _controller(
        "[XIC(Start),XIC(SystemActive)]XIC(StopCircuitHealthy)OTE(SystemActive);"
    )
    program = next(iter(controller.programs.values()))
    program.tags.clear()
    for name in ("Start", "StopCircuitHealthy", "SystemActive"):
        program.add_tag(Tag(name=name, data_type="BOOL"))

    destination = tmp_path / "fail-safe-seal-in"
    OpenPLCNativeProjectExporter().export(controller, destination=destination)

    rung = _ladder_json(destination / "pous/programs/main.ld")["rungs"][0]
    contacts = [node for node in rung["nodes"] if node["type"] == "contact"]
    assert contacts[0]["data"]["variable"]["name"] == "StopCircuitHealthy"
    assert contacts[0]["data"]["variant"] == "default"


def test_lowers_canonical_rockwell_timer_pair_to_iec_ton(tmp_path: Path) -> None:
    destination = tmp_path / "timer"

    OpenPLCNativeProjectExporter().export(
        _timer_controller(),
        destination=destination,
        locations={"Enable": "%QX0.0", "Output": "%QX0.1"},
    )

    path = destination / "pous/programs/main.ld"
    text = path.read_text()
    assert "DelayTimer : TON;" in text
    ladder = _ladder_json(path)
    assert len(ladder["rungs"]) == 1
    rung = ladder["rungs"][0]
    assert [node["type"] for node in rung["nodes"]] == [
        "powerRail",
        "contact",
        "variable",
        "block",
        "coil",
        "powerRail",
    ]
    block = next(node for node in rung["nodes"] if node["type"] == "block")
    assert block["data"]["variable"]["name"] == "DelayTimer"
    assert block["data"]["connectedVariables"][0]["variable"]["name"] == ("TIME#5000ms")
    assert [edge["sourceHandle"] for edge in rung["edges"]] == [
        "left-rail",
        "output",
        "output",
        "Q",
        "output",
    ]


def test_lowers_canonical_rockwell_tof_pair_to_iec_tof(tmp_path: Path) -> None:
    destination = tmp_path / "off-delay-timer"

    OpenPLCNativeProjectExporter().export(
        _timer_controller("TOF"),
        destination=destination,
        locations={"Enable": "%QX0.0", "Output": "%QX0.1"},
    )

    path = destination / "pous/programs/main.ld"
    text = path.read_text()
    assert "DelayTimer : TOF;" in text
    ladder = _ladder_json(path)
    assert len(ladder["rungs"]) == 1
    block = next(
        node for node in ladder["rungs"][0]["nodes"] if node["type"] == "block"
    )
    assert block["data"]["variant"]["name"] == "TOF"
    assert block["data"]["variable"]["name"] == "DelayTimer"
    assert block["data"]["variable"]["type"]["value"] == "TOF"
    assert block["data"]["connectedVariables"][0]["variable"]["name"] == ("TIME#5000ms")


def test_lowers_canonical_rto_dn_res_group_to_tf_rto(tmp_path: Path) -> None:
    destination = tmp_path / "retentive-timer"

    result = OpenPLCNativeProjectExporter().export(
        _timer_controller("RTO"),
        destination=destination,
        locations={
            "Enable": "%QX0.0",
            "ResetTimer": "%QX0.1",
            "Output": "%QX0.2",
        },
    )

    path = destination / "pous/programs/main.ld"
    assert "DelayTimer : TF_RTO;" in path.read_text()
    ladder = _ladder_json(path)
    assert len(ladder["rungs"]) == 1
    block = next(
        node for node in ladder["rungs"][0]["nodes"] if node["type"] == "block"
    )
    assert block["data"]["variant"]["name"] == "TF_RTO"
    assert block["data"]["variable"]["name"] == "DelayTimer"
    assert [
        item["variable"]["name"] for item in block["data"]["connectedVariables"]
    ] == ["ResetTimer", "TIME#5000ms"]

    function_block = destination / "pous/function-blocks/TF_RTO.st"
    assert function_block in result.files
    source = function_block.read_text()
    assert source.count("FUNCTION_BLOCK TF_RTO") == 1
    assert "RetainedTime := RetainedTime + SegmentTimer.ET;" in source
    assert "IF RESET THEN" in source


def test_lowers_canonical_ctu_dn_res_group_to_tf_counter(tmp_path: Path) -> None:
    destination = tmp_path / "count-up"

    result = OpenPLCNativeProjectExporter().export(
        _counter_controller(),
        destination=destination,
        locations={
            "CountPulse": "%QX0.0",
            "ResetCounter": "%QX0.1",
            "Done": "%QX0.2",
        },
        counter_accumulator_locations={"PartCounter": "%MD0"},
        counter_status_locations={
            "PartCounter": {"OV": "%QX0.4", "UN": "%QX0.5"}
        },
    )

    path = destination / "pous/programs/main.ld"
    text = path.read_text()
    assert "PartCounter : TF_COUNTER;" in text
    assert "PartCounter_ACC : DINT AT %MD0;" in text
    ladder = _ladder_json(path)
    assert len(ladder["rungs"]) == 1
    block = next(
        node for node in ladder["rungs"][0]["nodes"] if node["type"] == "block"
    )
    assert block["data"]["variant"]["name"] == "TF_COUNTER"
    assert block["data"]["variable"]["name"] == "PartCounter"
    connected = {
        item["handleId"]: item["variable"]["name"]
        for item in block["data"]["connectedVariables"]
    }
    assert connected["CD"] == "FALSE"
    assert connected["RESET"] == "ResetCounter"
    assert connected["PV"] == "3"
    assert connected["INITIAL_ACC"] == "0"
    assert connected["UP_FIRST"] == "TRUE"
    assert connected["CV"] == "PartCounter_ACC"

    function_block = destination / "pous/function-blocks/TF_COUNTER.st"
    assert function_block in result.files
    source = function_block.read_text()
    assert "CV := CV + 1;" in source
    assert "CV := -2147483647 - 1;" in source
    assert "Q := CV >= PV;" in source


def test_rejects_ctu_without_adjacent_res_rung(tmp_path: Path) -> None:
    controller = _counter_controller()
    program = next(iter(controller.programs.values()))
    routine = program.main_routine
    assert routine is not None
    routine.ladder_rungs.pop()

    with pytest.raises(OpenPLCNativeUnsupportedError, match="outside the evidenced"):
        OpenPLCNativeProjectExporter().export(
            controller,
            destination=tmp_path / "ctu-without-reset",
        )


@pytest.mark.parametrize(
    "paired, down_first", [(False, False), (True, False), (True, True)]
)
def test_lowers_ctd_and_paired_counter_to_one_shared_state_owner(
    tmp_path: Path,
    paired: bool,
    down_first: bool,
) -> None:
    destination = tmp_path / "shared-counter"

    result = OpenPLCNativeProjectExporter().export(
        _shared_counter_controller(paired=paired, down_first=down_first),
        destination=destination,
        locations={
            "CountPulse": "%QX0.0",
            "CountDown": "%QX0.1",
            "ResetCounter": "%QX0.2",
            "Done": "%QX0.3",
        },
        counter_accumulator_locations={"PartCounter": "%MD0"},
        counter_status_locations={"PartCounter": {"OV": "%QX0.4", "UN": "%QX0.5"}},
    )

    path = destination / "pous/programs/main.ld"
    assert "PartCounter : TF_COUNTER;" in path.read_text()
    assert "PartCounter_OV : BOOL AT %QX0.4;" in path.read_text()
    assert "PartCounter_UN : BOOL AT %QX0.5;" in path.read_text()
    ladder = _ladder_json(path)
    assert len(ladder["rungs"]) == 1
    block = next(
        node for node in ladder["rungs"][0]["nodes"] if node["type"] == "block"
    )
    assert block["data"]["variant"]["name"] == "TF_COUNTER"
    assert block["data"]["variable"]["name"] == "PartCounter"
    connected = {
        item["handleId"]: item["variable"]["name"]
        for item in block["data"]["connectedVariables"]
    }
    assert connected["INITIAL_ACC"] == "3"
    assert connected["PV"] == "3"
    assert connected["CV"] == "PartCounter_ACC"
    assert connected["OV"] == "PartCounter_OV"
    assert connected["UN"] == "PartCounter_UN"
    assert connected["UP_FIRST"] == str(paired and not down_first).upper()

    function_block = destination / "pous/function-blocks/TF_COUNTER.st"
    assert function_block in result.files
    source = function_block.read_text()
    assert "IF UP_FIRST THEN" in source
    assert "CV := CV - 1;" in source
    assert "Q := CV >= PV;" in source


@pytest.mark.parametrize(
    "status_locations, message",
    [
        ({"Missing": {"OV": "%QX0.4"}}, "without shared state"),
        ({"PartCounter": {"DN": "%QX0.4"}}, "only OV/UN"),
        ({"PartCounter": {"OV": "%MD1"}}, "requires evidenced"),
    ],
)
def test_rejects_unsupported_counter_status_telemetry(
    tmp_path: Path,
    status_locations: dict[str, dict[str, str]],
    message: str,
) -> None:
    with pytest.raises(OpenPLCNativeUnsupportedError, match=message):
        OpenPLCNativeProjectExporter().export(
            _shared_counter_controller(),
            destination=tmp_path / "invalid-counter-status",
            counter_status_locations=status_locations,
        )


def test_rejects_rto_without_adjacent_res_rung(tmp_path: Path) -> None:
    controller = _timer_controller("RTO")
    program = next(iter(controller.programs.values()))
    routine = program.main_routine
    assert routine is not None
    routine.ladder_rungs.pop()

    with pytest.raises(
        OpenPLCNativeUnsupportedError,
        match="outside the evidenced",
    ):
        OpenPLCNativeProjectExporter().export(
            controller,
            destination=tmp_path / "rto-without-reset",
        )


def test_exposes_timer_elapsed_seconds_at_explicit_md_location(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "timer-elapsed"

    OpenPLCNativeProjectExporter().export(
        _timer_controller(),
        destination=destination,
        locations={"Enable": "%QX0.0", "Output": "%QX0.1"},
        timer_elapsed_locations={"DelayTimer": "%MD0"},
    )

    path = destination / "pous/programs/main.ld"
    text = path.read_text()
    assert "DelayTimer_ET : TIME;" in text
    assert "DelayTimer_ElapsedSeconds : DINT AT %MD0;" in text
    ladder = _ladder_json(path)
    assert len(ladder["rungs"]) == 2

    timer_rung, conversion_rung = ladder["rungs"]
    elapsed = next(
        node
        for node in timer_rung["nodes"]
        if node["type"] == "variable" and node["data"]["block"]["handleId"] == "ET"
    )
    assert elapsed["data"]["variable"]["name"] == "DelayTimer_ET"

    block = next(node for node in conversion_rung["nodes"] if node["type"] == "block")
    assert block["data"]["variant"]["name"] == "TIME_TO_DINT"
    assert block["data"]["executionControl"] is True
    assert block["data"]["lockExecutionControl"] is True
    assert [
        item["variable"]["name"] for item in block["data"]["connectedVariables"]
    ] == ["DelayTimer_ET", "DelayTimer_ElapsedSeconds"]
    assert block["data"]["connectedVariables"][1]["variable"]["location"] == "%MD0"


@pytest.mark.parametrize(
    "timer_elapsed_locations, message",
    [
        ({"MissingTimer": "%MD0"}, "unknown TIMER tags"),
        ({"DelayTimer": "%MW0"}, "requires evidenced %MD"),
    ],
)
def test_rejects_unknown_timer_or_unevidenced_elapsed_location(
    tmp_path: Path,
    timer_elapsed_locations: dict[str, str],
    message: str,
) -> None:
    with pytest.raises(OpenPLCNativeUnsupportedError, match=message):
        OpenPLCNativeProjectExporter().export(
            _timer_controller(),
            destination=tmp_path / "invalid-timer-elapsed",
            timer_elapsed_locations=timer_elapsed_locations,
        )


def test_rejects_tof_elapsed_telemetry_until_runtime_evidenced(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        OpenPLCNativeUnsupportedError,
        match="runtime-evidenced only for TON",
    ):
        OpenPLCNativeProjectExporter().export(
            _timer_controller("TOF"),
            destination=tmp_path / "unevidenced-tof-elapsed",
            timer_elapsed_locations={"DelayTimer": "%MD0"},
        )


@pytest.mark.parametrize(
    "locations, message",
    [
        ({"Missing": "%QX0.0"}, "unknown local variables"),
        ({"Enable": "%MW0"}, "only evidenced %IX/%QX"),
    ],
)
def test_rejects_unevidenced_or_unknown_locations(
    tmp_path: Path,
    locations: dict[str, str],
    message: str,
) -> None:
    with pytest.raises(OpenPLCNativeUnsupportedError, match=message):
        OpenPLCNativeProjectExporter().export(
            _controller(),
            destination=tmp_path / "invalid-location",
            locations=locations,
        )


def test_rejects_unevidenced_ladder_without_writing_project(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "unsupported"

    with pytest.raises(
        OpenPLCNativeUnsupportedError,
        match="outside the evidenced serial/parallel-XIC-to-OTE subset",
    ):
        OpenPLCNativeProjectExporter().export(
            _controller("XIO(Enable)OTE(Output);"),
            destination=destination,
        )

    assert not destination.exists()
