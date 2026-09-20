"""Write an SFC test-coverage/traceability skeleton for Control Expert projects."""
from __future__ import annotations

from pathlib import Path
from typing import TextIO

from twinforge.analysis.sfc_coverage import build_sfc_coverage_report
from twinforge.exporters.sfc_coverage import (
    SFCCoverageCSVExporter,
    SFCCoverageMarkdownExporter,
    sfc_coverage_json,
)
from twinforge.parsers.control_expert import capture_file, parse_projects

from .control_expert import _artifacts, ControlExpertCommandError


def export_control_expert_coverage(path: Path, *, destination: Path, stdout: TextIO) -> None:
    """Write one Markdown/CSV/JSON coverage skeleton per parsed project.

    This is a starting point for a reviewer's test matrix, not a record of
    tests performed. It reflects only what structurally parsed; capture or
    parsing failures are reported, not silently skipped.
    """
    try:
        captured = capture_file(path)
        projects = parse_projects(captured)
    except (OSError, ValueError) as error:
        raise ControlExpertCommandError(f"could not inspect Control Expert input '{path}': {error}") from error
    failures = [d for artifact in _artifacts(captured) for d in artifact.diagnostics
                if d.code not in {"unclassified_xml", "unclassified_content"}]
    if failures or not projects:
        raise ControlExpertCommandError(
            f"could not build a coverage skeleton for '{path}': capture was incomplete "
            "or no supported exchange project was found"
        )
    destination.mkdir(parents=True, exist_ok=True)
    for index, project in enumerate(projects):
        report = build_sfc_coverage_report(project.controller, project.diagnostics)
        stem = f"sfc_coverage_project{index}" if len(projects) > 1 else "sfc_coverage"
        (destination / f"{stem}.md").write_text(SFCCoverageMarkdownExporter().export(report), encoding="utf-8")
        (destination / f"{stem}.csv").write_text(SFCCoverageCSVExporter().export(report), encoding="utf-8", newline="")
        (destination / f"{stem}.json").write_text(sfc_coverage_json(report), encoding="utf-8")
        stdout.write(f"Project {index + 1} ({project.controller.name or '(unnamed)'}): "
                     f"{report.step_count} steps, {report.transition_count} transitions, "
                     f"{report.unresolved_connectivity_count} unresolved, "
                     f"{report.diagnostic_count} diagnostics -> {destination / stem}.{{md,csv,json}}\n")
