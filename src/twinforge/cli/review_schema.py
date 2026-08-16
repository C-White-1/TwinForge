"""Installed export adapter for engineering-review JSON Schemas."""

from __future__ import annotations

from pathlib import Path
from typing import TextIO

from twinforge.analysis import (
    alarm_review_schema_text,
    cause_effect_review_schema_text,
    engineering_review_coverage_schema_text,
)

from .review_validation import review_validation_result_schema_text


class ReviewSchemaCommandError(RuntimeError):
    """Raised when an installed review schema cannot be exported."""


_SCHEMAS = {
    "alarm": ("alarm review v1", alarm_review_schema_text),
    "cause-effect": (
        "cause-and-effect review v1",
        cause_effect_review_schema_text,
    ),
    "coverage": (
        "engineering-review coverage v1",
        engineering_review_coverage_schema_text,
    ),
    "validation-result": (
        "review-validation result v1",
        review_validation_result_schema_text,
    ),
}


def export_review_schema(
    kind: str,
    destination: Path,
    *,
    stdout: TextIO,
) -> None:
    """Write one exact packaged review schema to a user-selected path."""

    try:
        label, loader = _SCHEMAS[kind]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(loader(), encoding="utf-8")
    except (KeyError, OSError, UnicodeError) as error:
        raise ReviewSchemaCommandError(
            f"could not export {kind!r} review schema to '{destination}': {error}"
        ) from error
    stdout.write(f"Exported TwinForge {label} schema to {destination}\n")
