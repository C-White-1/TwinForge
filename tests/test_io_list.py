from __future__ import annotations

import json
from pathlib import Path

from twinforge.analysis import build_io_list_report, io_list_report_json
from twinforge.parsers import L5XParser


SAMPLE = Path(__file__).parent / "data/basic/BoosterCompressor_20260128.L5X"


def test_builds_assigned_spare_and_configuration_bound_channels() -> None:
    controller = L5XParser().parse(SAMPLE, report_mode=None).controllers[0]

    report = build_io_list_report(controller)

    digital = next(
        item
        for item in report.channels
        if item.module_name == "DI_Slot2" and item.channel == 0
    )
    assert digital.assignment_status == "assigned"
    assert digital.assigned_tags == ("XV101_Open",)
    assert digital.source_operand == "Local:2:I.Data.0"
    digital_spare = next(
        item
        for item in report.channels
        if item.module_name == "DI_Slot2" and item.channel == 8
    )
    assert digital_spare.assignment_status == "spare"

    analog = next(
        item
        for item in report.channels
        if item.module_name == "AI_Slot4" and item.channel == 2
    )
    assert analog.assigned_tags == ("PT102_PV",)
    assert analog.engineering_unit == "barg"
    assert (analog.lower_range, analog.upper_range) == (0.0, 150.0)
    unavailable = next(
        item
        for item in report.channels
        if item.module_name == "AI_Slot4" and item.channel == 4
    )
    assert unavailable.assignment_status == "unavailable_by_configuration"


def test_json_retains_enum_values_and_unresolved_evidence() -> None:
    controller = L5XParser().parse(SAMPLE, report_mode=None).controllers[0]

    payload = io_list_report_json(build_io_list_report(controller))
    data = json.loads(payload)

    assert payload.endswith("\n")
    assert data["channels"][0]["signal_type"] in {"Digital", "Analog"}
    assert isinstance(data["unresolved_aliases"], list)
