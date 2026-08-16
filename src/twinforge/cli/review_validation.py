"""Standalone validation adapter for engineering-review input contracts."""

from __future__ import annotations

from pathlib import Path
from typing import TextIO

from twinforge.analysis import (
    apply_alarm_review,
    apply_cause_effect_review,
    build_alarm_trip_candidate_report,
    build_cause_effect_candidate_report,
    build_tag_dependency_graph,
    load_alarm_review,
    load_cause_effect_review,
)
from twinforge.model import Controller
from twinforge.parsers.l5x import L5XParser


class ReviewValidationCommandError(RuntimeError):
    """Raised when an engineering-review document is not contract-valid."""


def validate_review_document(
    kind: str,
    source: Path,
    *,
    l5x_source: Path | None = None,
    stdout: TextIO,
) -> None:
    """Validate one review overlay and optionally reconcile its L5X keys."""

    try:
        alarms = None
        dependency_graph = None
        if l5x_source is not None:
            parsed = L5XParser().parse_document(l5x_source, report_mode=None)
            if not isinstance(parsed.target, Controller):
                raise ValueError(
                    "review reconciliation requires a Controller L5X target; "
                    f"found {parsed.target_type.value}"
                )
            dependency_graph = build_tag_dependency_graph(parsed.target)
            alarms = build_alarm_trip_candidate_report(
                parsed.target,
                dependency_graph,
            )

        if kind == "alarm":
            document = load_alarm_review(source)
            label = "alarm review v1"
            if alarms is not None:
                apply_alarm_review(alarms, document)
        elif kind == "cause-effect":
            document = load_cause_effect_review(source)
            label = "cause-and-effect review v1"
            if alarms is not None and dependency_graph is not None:
                cause_effect = build_cause_effect_candidate_report(
                    alarms,
                    dependency_graph,
                )
                apply_cause_effect_review(cause_effect, document)
        else:
            raise ValueError(f"unsupported review kind: {kind!r}")
    except (OSError, ValueError) as error:
        raise ReviewValidationCommandError(str(error)) from error

    reconciliation = (
        f" and reconciled against {l5x_source}" if l5x_source is not None else ""
    )
    stdout.write(
        f"Validated TwinForge {label}: {source}{reconciliation} "
        f"(controller {document.controller_name!r}, {len(document.items)} items)\n"
    )
