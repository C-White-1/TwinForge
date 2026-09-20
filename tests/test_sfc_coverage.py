"""SFC test-coverage/traceability skeleton: analysis model and exporters."""
import csv
from dataclasses import asdict
from io import StringIO
import json
from pathlib import Path

from twinforge.analysis.sfc_coverage import build_sfc_coverage_report
from twinforge.cli import main
from twinforge.exporters.sfc_coverage import (
    SFCCoverageCSVExporter,
    SFCCoverageMarkdownExporter,
    sfc_coverage_data,
)
from twinforge.parsers.control_expert import capture_bytes, parse_project


def _project(xml_body: str):
    data = f'<FEFExchangeFile><SFCProgram><identProgram name="S"/>{xml_body}</SFCProgram></FEFExchangeFile>'
    return parse_project(capture_bytes(data.encode(), name="coverage.xef"))


def test_report_lists_steps_transitions_and_correlates_diagnostics():
    result = _project('''
    <chartSource name="C"><networkSFC>
    <step stepType="initialStep" stepName="S0"><objPosition posX="1" posY="1"/></step>
    <transition><objPosition posX="1" posY="2"/></transition>
    <step stepType="step" stepName="S1"><objPosition posX="1" posY="3"/></step>
    <transition><objPosition posX="1" posY="4"/></transition>
    </networkSFC></chartSource>''')
    report = build_sfc_coverage_report(result.controller, result.diagnostics)
    assert report.step_count == 2
    assert report.transition_count == 2
    # The dead-end transition at (1,4) has no successor.
    assert report.unresolved_connectivity_count == 1
    # At least the dead-end diagnostic and the always-emitted execution-unresolved one.
    codes = {item.diagnostic_code for item in report.items if item.item_type == "diagnostic"}
    assert "unresolved_sfc_successor" in codes
    assert "uninterpreted_sfc_execution" in codes
    # Diagnostics correlate back to the owning program/routine/chart via source location.
    execution_item = next(item for item in report.items if item.diagnostic_code == "uninterpreted_sfc_execution")
    assert execution_item.program_name == "S"
    # Routine-level diagnostics (like this one) aren't pinned to a specific chart.
    assert execution_item.chart_index == -1


def test_resolved_chart_has_no_connectivity_diagnostics_or_unresolved_items():
    result = _project('''
    <chartSource name="C"><networkSFC>
    <step stepType="initialStep" stepName="S0"><objPosition posX="1" posY="1"/></step>
    <transition><objPosition posX="1" posY="2"/></transition>
    <step stepType="step" stepName="S1"><objPosition posX="1" posY="3"/></step>
    <transition><objPosition posX="1" posY="4"/></transition>
    <linkSFC>
    <directedLinkSource objectType="transition"><objPosition posX="1" posY="4"/></directedLinkSource>
    <directedLinkDestination objectType="step"><objPosition posX="1" posY="1"/></directedLinkDestination>
    </linkSFC>
    </networkSFC></chartSource>''')
    report = build_sfc_coverage_report(result.controller, result.diagnostics)
    assert report.unresolved_connectivity_count == 0
    codes = {item.diagnostic_code for item in report.items if item.item_type == "diagnostic"}
    assert "unresolved_sfc_successor" not in codes
    assert "ambiguous_sfc_successor" not in codes


def test_markdown_exporter_renders_summary_and_blank_editable_columns():
    result = _project('''
    <chartSource name="C"><networkSFC>
    <step stepType="initialStep" stepName="S0"><objPosition posX="1" posY="1"/></step>
    <transition><objPosition posX="1" posY="2"/></transition>
    </networkSFC></chartSource>''')
    report = build_sfc_coverage_report(result.controller, result.diagnostics)
    text = SFCCoverageMarkdownExporter().export(report)
    assert f"- Steps: {report.step_count}" in text
    assert "S0" in text
    # Requirement ID / Test ID / Status columns are present but blank.
    assert "| Requirement ID | Test ID | Status |" in text
    step_line = next(line for line in text.splitlines() if "Step S0 (initial)" in line)
    cells = [cell.strip() for cell in step_line.strip().strip("|").split("|")]
    assert cells[-3:] == ["", "", ""]  # Requirement ID, Test ID, Status


def test_csv_exporter_round_trips_through_csv_reader():
    result = _project('''
    <chartSource name="C"><networkSFC>
    <step stepType="initialStep" stepName="S0"><objPosition posX="1" posY="1"/></step>
    <transition><objPosition posX="1" posY="2"/></transition>
    </networkSFC></chartSource>''')
    report = build_sfc_coverage_report(result.controller, result.diagnostics)
    text = SFCCoverageCSVExporter().export(report)
    rows = list(csv.DictReader(StringIO(text)))
    assert len(rows) == len(report.items)
    step_row = next(r for r in rows if r["Type"] == "step")
    assert step_row["Element"] == "S0"
    assert step_row["RequirementID"] == "" and step_row["TestID"] == "" and step_row["Status"] == ""


def test_json_export_matches_summary_counts():
    result = _project('''
    <chartSource name="C"><networkSFC>
    <step stepType="initialStep" stepName="S0"><objPosition posX="1" posY="1"/></step>
    <transition><objPosition posX="1" posY="2"/></transition>
    </networkSFC></chartSource>''')
    report = build_sfc_coverage_report(result.controller, result.diagnostics)
    data = sfc_coverage_data(report)
    assert data["schema_version"] == "twinforge.sfc-coverage.v1"
    assert data["summary"] == {
        "step_count": report.step_count,
        "transition_count": report.transition_count,
        "unresolved_connectivity_count": report.unresolved_connectivity_count,
        "diagnostic_count": report.diagnostic_count,
    }
    assert data["items"] == [asdict(item) for item in report.items]


def test_cli_writes_coverage_bundle_for_a_single_project(tmp_path: Path):
    path = tmp_path / "sequence.xef"
    path.write_text('<FEFExchangeFile><SFCProgram><identProgram name="S"/>'
                     '<chartSource name="C"><networkSFC>'
                     '<step stepType="initialStep" stepName="S0"><objPosition posX="1" posY="1"/></step>'
                     '<transition><objPosition posX="1" posY="2"/></transition>'
                     '</networkSFC></chartSource></SFCProgram></FEFExchangeFile>')
    out_dir = tmp_path / "out"
    output = StringIO()
    assert main(("control-expert", "coverage", str(path), "--output", str(out_dir)), stdout=output) == 0
    assert (out_dir / "sfc_coverage.md").exists()
    assert (out_dir / "sfc_coverage.csv").exists()
    assert (out_dir / "sfc_coverage.json").exists()
    data = json.loads((out_dir / "sfc_coverage.json").read_text(encoding="utf-8"))
    assert data["summary"]["step_count"] == 1
    assert "sfc_coverage.md" in output.getvalue() or "sfc_coverage" in output.getvalue()


def test_cli_coverage_has_clean_error_on_missing_input(tmp_path: Path):
    output, errors = StringIO(), StringIO()
    assert main(("control-expert", "coverage", str(tmp_path / "missing.zef"), "--output", str(tmp_path / "out")),
                stdout=output, stderr=errors) == 1
    assert not output.getvalue()
    assert "could not inspect Control Expert input" in errors.getvalue()
