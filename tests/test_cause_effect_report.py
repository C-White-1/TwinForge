from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

from twinforge.analysis import (
    build_alarm_trip_candidate_report,
    build_cause_effect_candidate_report,
    build_tag_dependency_graph,
)
from twinforge.exporters import (
    CauseEffectCandidateCSVExporter,
    CauseEffectCandidateMarkdownExporter,
)
from twinforge.parsers import L5XParser


SAMPLE = Path(__file__).parent / "data/basic/BoosterCompressor_20260128.L5X"


def test_exports_explicitly_unverified_matrix_rows() -> None:
    controller = L5XParser().parse(SAMPLE, report_mode=None).controllers[0]
    graph = build_tag_dependency_graph(controller)
    report = build_cause_effect_candidate_report(
        build_alarm_trip_candidate_report(controller, graph), graph
    )

    markdown = CauseEffectCandidateMarkdownExporter().export(report)
    rows = list(
        csv.DictReader(StringIO(CauseEffectCandidateCSVExporter().export(report)))
    )

    assert "not proof of a causal relationship" in markdown
    assert "PT102_PV" in markdown
    assert "PT102_HH_Alm" in markdown
    relation = next(row for row in rows if row["Effect"] == "PT102_HH_Alm")
    assert relation["EvidenceBasis"] == "same_logic_location"
    assert relation["CausalRelationshipVerified"] == "false"
