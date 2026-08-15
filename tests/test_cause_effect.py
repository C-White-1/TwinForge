from __future__ import annotations

import json
from pathlib import Path

from twinforge.analysis import (
    build_alarm_trip_candidate_report,
    build_cause_effect_candidate_report,
    build_tag_dependency_graph,
    cause_effect_candidate_report_json,
)
from twinforge.exporters import CauseEffectCandidateMarkdownExporter
from twinforge.parsers import L5XParser


SAMPLE = Path(__file__).parent / "data/basic/BoosterCompressor_20260128.L5X"


def test_joins_reads_to_alarm_writes_at_the_same_logic_location() -> None:
    controller = L5XParser().parse(SAMPLE, report_mode=None).controllers[0]
    graph = build_tag_dependency_graph(controller)
    alarms = build_alarm_trip_candidate_report(controller, graph)

    report = build_cause_effect_candidate_report(alarms, graph)

    high_high = next(
        item for item in report.candidates if item.effect_tag_name == "PT102_HH_Alm"
    )
    assert high_high.writer_instruction == "OTE"
    assert {cause.tag_name for cause in high_high.causes} == {
        "CFG_PT102_HH",
        "PT102_PV",
    }
    assert high_high.evidence_basis == "same_logic_location"
    assert high_high.causal_relationship_verified is False
    assert all(cause.relationship_key.startswith("ce:") for cause in high_high.causes)
    assert len({cause.relationship_key for cause in high_high.causes}) == 2


def test_json_marks_candidate_relationships_unverified() -> None:
    controller = L5XParser().parse(SAMPLE, report_mode=None).controllers[0]
    graph = build_tag_dependency_graph(controller)
    alarms = build_alarm_trip_candidate_report(controller, graph)

    payload = cause_effect_candidate_report_json(
        build_cause_effect_candidate_report(alarms, graph)
    )
    candidates = json.loads(payload)["candidates"]

    assert payload.endswith("\n")
    assert candidates
    assert all(not item["causal_relationship_verified"] for item in candidates)
    assert all(
        cause["relationship_key"].startswith("ce:")
        for item in candidates
        for cause in item["causes"]
    )


def test_markdown_exposes_relationship_key_in_first_column() -> None:
    controller = L5XParser().parse(SAMPLE, report_mode=None).controllers[0]
    graph = build_tag_dependency_graph(controller)
    report = build_cause_effect_candidate_report(
        build_alarm_trip_candidate_report(controller, graph),
        graph,
    )

    markdown = CauseEffectCandidateMarkdownExporter().export(report)
    relationship = next(
        cause.relationship_key
        for item in report.candidates
        for cause in item.causes
    )
    row = next(line for line in markdown.splitlines() if relationship in line)

    assert row.startswith(f"| {relationship} |")
    assert "| unreviewed |" in row
    assert row.endswith("| — | — | — | — | — |")
