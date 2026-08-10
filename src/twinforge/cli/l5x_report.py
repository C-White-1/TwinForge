"""Installed command adapter for controller engineering reports."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TextIO

from twinforge.analysis import (
    alarm_trip_candidate_report_json,
    build_alarm_trip_candidate_report,
    build_tag_dependency_graph,
    tag_dependency_graph_json,
)
from twinforge.exporters import (
    AlarmTripCandidateCSVExporter,
    AlarmTripCandidateMarkdownExporter,
    TagDependencyCSVExporter,
    TagDependencyMarkdownExporter,
    TextReportBundle,
    TextReportExporter,
)
from twinforge.model import Controller
from twinforge.parsers.l5x import L5XParser


class L5XReportError(RuntimeError):
    """Raised when an L5X report bundle cannot be generated or written."""


def export_l5x_reports(
    source: Path,
    *,
    destination: Path,
    stdout: TextIO,
) -> None:
    """Generate the supported controller report bundle at ``destination``."""
    try:
        document = L5XParser().parse_document(source, report_mode=None)
        if not isinstance(document.target, Controller):
            raise L5XReportError(
                "engineering report bundles currently require a Controller "
                f"L5X target; found {document.target_type.value}"
            )
        controller = document.target
        files = dict(TextReportExporter().export(controller).files)
        dependency_graph = build_tag_dependency_graph(controller)
        alarm_candidates = build_alarm_trip_candidate_report(
            controller, dependency_graph
        )
        files.update(
            {
                "tag_dependencies.md": TagDependencyMarkdownExporter().export(
                    dependency_graph,
                    title=f"{controller.name} tag and program dependency report",
                ),
                "tag_dependencies.csv": TagDependencyCSVExporter().export(
                    dependency_graph
                ),
                "tag_dependencies.json": tag_dependency_graph_json(
                    dependency_graph
                ),
                "alarm_trip_candidates.md": (
                    AlarmTripCandidateMarkdownExporter().export(
                        alarm_candidates,
                        title=(
                            f"{controller.name} alarm and trip candidate report"
                        ),
                    )
                ),
                "alarm_trip_candidates.csv": (
                    AlarmTripCandidateCSVExporter().export(alarm_candidates)
                ),
                "alarm_trip_candidates.json": (
                    alarm_trip_candidate_report_json(alarm_candidates)
                ),
            }
        )
        paths = TextReportBundle(files).write_to(destination)
    except L5XReportError:
        raise
    except (ET.ParseError, OSError, ValueError) as error:
        raise L5XReportError(
            f"cannot generate reports from L5X '{source}': {error}"
        ) from error

    stdout.write(f"Exported {len(paths)} reports to {destination}\n")
    for path in paths:
        stdout.write(f"- {path}\n")
