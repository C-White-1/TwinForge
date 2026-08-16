"""Standalone validation adapter for engineering-review input contracts."""

from __future__ import annotations

from pathlib import Path
from typing import TextIO

from twinforge.analysis import load_alarm_review, load_cause_effect_review


class ReviewValidationCommandError(RuntimeError):
    """Raised when an engineering-review document is not contract-valid."""


def validate_review_document(
    kind: str,
    source: Path,
    *,
    stdout: TextIO,
) -> None:
    """Validate one review overlay without requiring report generation."""

    try:
        if kind == "alarm":
            document = load_alarm_review(source)
            label = "alarm review v1"
        elif kind == "cause-effect":
            document = load_cause_effect_review(source)
            label = "cause-and-effect review v1"
        else:
            raise ValueError(f"unsupported review kind: {kind!r}")
    except (OSError, ValueError) as error:
        raise ReviewValidationCommandError(str(error)) from error

    stdout.write(
        f"Validated TwinForge {label}: {source} "
        f"(controller {document.controller_name!r}, {len(document.items)} items)\n"
    )
