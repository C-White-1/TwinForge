"""Standalone validation adapter for engineering-review input contracts."""

from __future__ import annotations

import json
import os
import tempfile
from importlib.resources import files
from pathlib import Path
from typing import TextIO

from twinforge.analysis import (
    AlarmReviewDocument,
    apply_alarm_review,
    apply_cause_effect_review,
    build_alarm_trip_candidate_report,
    build_cause_effect_candidate_report,
    build_tag_dependency_graph,
    load_alarm_review,
    load_cause_effect_review,
    CauseEffectReviewDocument,
)
from twinforge.model import Controller
from twinforge.parsers.l5x import L5XParser
from twinforge.exporters import (
    review_validation_result_json,
    verify_review_validation_result,
)


class ReviewValidationCommandError(RuntimeError):
    """Raised when an engineering-review document is not contract-valid."""


def review_validation_result_schema_text() -> str:
    """Return the packaged review-validation result JSON Schema text."""

    schema = files("twinforge.schemas").joinpath(
        "review-validation-result.v1.schema.json"
    )
    return schema.read_text(encoding="utf-8")


def validate_review_document(
    kind: str,
    source: Path,
    *,
    l5x_source: Path | None = None,
    output_format: str = "text",
    destination: Path | None = None,
    stdout: TextIO,
) -> None:
    """Validate one review overlay and optionally reconcile its L5X keys."""

    try:
        label, document = _load_and_reconcile(kind, source, l5x_source)
    except (OSError, ValueError) as error:
        raise ReviewValidationCommandError(str(error)) from error

    serialized = review_validation_result_json(
        kind,
        source,
        controller_name=document.controller_name,
        item_count=len(document.items),
        source=l5x_source,
    )
    if destination is not None:
        _write_atomic(destination, serialized)
    if output_format == "json":
        stdout.write(serialized)
        return

    reconciliation = f" and reconciled against {l5x_source}" if l5x_source else ""
    stdout.write(
        f"Validated TwinForge {label}: {source}{reconciliation} "
        f"(controller {document.controller_name!r}, {len(document.items)} items)\n"
    )
    if destination is not None:
        stdout.write(f"Wrote validation receipt to {destination}\n")


def verify_review_receipt(
    kind: str,
    receipt: Path,
    review: Path,
    *,
    l5x_source: Path | None = None,
    output_format: str = "text",
    stdout: TextIO,
) -> None:
    """Verify one saved receipt and repeat its semantic reconciliation."""

    try:
        _, document = _load_and_reconcile(kind, review, l5x_source)
        result = verify_review_validation_result(
            receipt,
            kind,
            review,
            controller_name=document.controller_name,
            item_count=len(document.items),
            source=l5x_source,
        )
    except (OSError, ValueError) as error:
        raise ReviewValidationCommandError(str(error)) from error

    if output_format == "json":
        stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
        return
    source_text = f" and source {l5x_source}" if l5x_source is not None else ""
    stdout.write(
        f"Verified review-validation receipt {receipt} against {review}"
        f"{source_text}\n"
    )


def _load_and_reconcile(
    kind: str,
    review: Path,
    l5x_source: Path | None,
) -> tuple[str, AlarmReviewDocument | CauseEffectReviewDocument]:
    """Load a review and repeat evidence-derived key reconciliation."""

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
        document = load_alarm_review(review)
        if alarms is not None:
            apply_alarm_review(alarms, document)
        return "alarm review v1", document
    if kind == "cause-effect":
        document = load_cause_effect_review(review)
        if alarms is not None and dependency_graph is not None:
            cause_effect = build_cause_effect_candidate_report(
                alarms,
                dependency_graph,
            )
            apply_cause_effect_review(cause_effect, document)
        return "cause-and-effect review v1", document
    raise ValueError(f"unsupported review kind: {kind!r}")


def _write_atomic(destination: Path, content: str) -> None:
    """Replace one receipt only after its complete bytes reach disk."""

    temporary: Path | None = None
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            stream.write(content)
            temporary = Path(stream.name)
        os.replace(temporary, destination)
    except OSError as error:
        raise ReviewValidationCommandError(
            f"could not write review-validation receipt '{destination}': {error}"
        ) from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
