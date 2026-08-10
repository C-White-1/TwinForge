from __future__ import annotations

import csv
import json
from io import StringIO

from twinforge.analysis import (
    AlarmTripCandidate,
    AlarmTripCandidateKind,
    AlarmTripCandidateReport,
    alarm_trip_candidate_report_json,
)
from twinforge.exporters import (
    AlarmTripCandidateCSVExporter,
    AlarmTripCandidateMarkdownExporter,
)
from twinforge.model import SoftwareTagScope


def _report() -> AlarmTripCandidateReport:
    return AlarmTripCandidateReport(
        controller_name="PLC",
        candidates=(
            AlarmTripCandidate(
                tag_key="controller:PumpTripAlarm",
                tag_name="PumpTripAlarm",
                tag_scope=SoftwareTagScope.CONTROLLER,
                program_name=None,
                description="Pump trip alarm",
                kinds=(
                    AlarmTripCandidateKind.ALARM,
                    AlarmTripCandidateKind.TRIP,
                ),
                classification_evidence=(
                    "name explicitly contains an alarm token",
                    "name explicitly contains a trip token",
                ),
                reader_locations=("Main.Alarms: rung 2",),
                writer_locations=("Main.Trips: rung 1",),
                alias_source_keys=("controller:PumpTripAlias",),
            ),
        ),
    )


def test_markdown_and_csv_keep_unestablished_fields_unknown() -> None:
    report = _report()

    markdown = AlarmTripCandidateMarkdownExporter().export(report)
    csv_rows = list(
        csv.DictReader(StringIO(AlarmTripCandidateCSVExporter().export(report)))
    )

    assert "not a verified alarm philosophy" in markdown
    assert "| PumpTripAlarm | controller | alarm, trip |" in markdown
    assert "| — | — | — | — | — | — | — | — |" in markdown
    assert csv_rows[0]["Kind"] == "alarm;trip"
    assert csv_rows[0]["Priority"] == ""
    assert csv_rows[0]["Setpoint"] == ""
    assert csv_rows[0]["ShutdownAction"] == ""


def test_json_is_deterministic_and_retains_null_review_fields() -> None:
    payload = alarm_trip_candidate_report_json(_report())

    assert payload.endswith("\n")
    candidate = json.loads(payload)["candidates"][0]
    assert candidate["tag_scope"] == "controller"
    assert candidate["kinds"] == ["alarm", "trip"]
    assert candidate["priority"] is None
    assert candidate["applicability"] is None
