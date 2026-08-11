from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path

from twinforge.analysis import (
    build_io_list_report,
    build_module_schedule_report,
    module_schedule_report_json,
)
from twinforge.exporters import (
    ModuleScheduleCSVExporter,
    ModuleScheduleMarkdownExporter,
)
from twinforge.parsers import L5XParser


SAMPLE = Path(__file__).parent / "data/basic/BoosterCompressor_20260128.L5X"


def _report():
    controller = L5XParser().parse(SAMPLE, report_mode=None).controllers[0]
    return build_module_schedule_report(controller, build_io_list_report(controller))


def test_aggregates_module_capacity_without_losing_unknown_modules() -> None:
    report = _report()

    digital = next(item for item in report.modules if item.module_name == "DI_Slot2")
    assert digital.nominal_channels == 16
    assert digital.assigned_channels > 0
    assert digital.spare_candidates > 0
    analog = next(item for item in report.modules if item.module_name == "AI_Slot4")
    assert analog.configured_channels == 4
    assert analog.unavailable_by_configuration == 4
    controller = next(item for item in report.modules if item.module_name == "Local")
    assert controller.capability_status == "unknown"
    assert controller.nominal_channels is None


def test_exports_schedule_as_markdown_csv_and_json() -> None:
    report = _report()

    markdown = ModuleScheduleMarkdownExporter().export(report)
    rows = list(csv.DictReader(StringIO(ModuleScheduleCSVExporter().export(report))))
    payload = module_schedule_report_json(report)

    assert "Unknown capability is retained" in markdown
    assert "Spare candidates" in markdown
    ai = next(row for row in rows if row["Module"] == "AI_Slot4")
    assert ai["UnavailableByConfiguration"] == "4"
    assert json.loads(payload)["modules"]
    assert payload.endswith("\n")
