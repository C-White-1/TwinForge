from __future__ import annotations

from pathlib import Path

from twinforge.analysis import (
    build_alarm_trip_candidate_report,
    build_cause_effect_candidate_report,
    build_controller_functional_description,
    build_io_list_report,
    build_tag_dependency_graph,
)
from twinforge.exporters import ControllerFunctionalDescriptionMarkdownExporter
from twinforge.parsers import L5XParser


SAMPLE = Path(__file__).parent / "data/basic/BoosterCompressor_20260128.L5X"


def _report():
    controller = L5XParser().parse(SAMPLE, report_mode=None).controllers[0]
    graph = build_tag_dependency_graph(controller)
    alarms = build_alarm_trip_candidate_report(controller, graph)
    cause_effect = build_cause_effect_candidate_report(alarms, graph)
    return build_controller_functional_description(
        controller,
        graph,
        build_io_list_report(controller),
        alarms,
        cause_effect,
    )


def test_aggregates_controller_execution_and_engineering_evidence() -> None:
    report = _report()

    assert report.controller_name == "booster_compressor"
    assert report.tasks[0].name == "MainTask"
    assert report.tasks[0].scheduled_programs == ("MainProgram",)
    assert report.programs[0].ladder_rung_count > 0
    assert report.io_channel_count > report.assigned_io_count > 0
    assert report.alarm_trip_candidate_count > 0
    assert report.cause_effect_candidate_count > 0
    assert report.unresolved_dependency_count > 0


def test_renders_controller_functional_description_draft() -> None:
    markdown = ControllerFunctionalDescriptionMarkdownExporter().export(_report())

    assert "# booster_compressor functional-description draft" in markdown
    assert "## Execution schedule" in markdown
    assert "MainTask" in markdown
    assert "MainProgram" in markdown
    assert "## Derived engineering evidence" in markdown
    assert "not a validated statement of plant intent" in markdown
