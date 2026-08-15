"""Installed verification adapter for engineering-report bundles."""

from __future__ import annotations

from pathlib import Path
from typing import TextIO

from twinforge.exporters import (
    ReportManifestError,
    verify_engineering_report_bundle,
)


class ReportBundleCommandError(RuntimeError):
    """Raised when an engineering-report bundle cannot be verified."""


def verify_report_bundle(
    directory: Path,
    *,
    source: Path,
    alarm_review: Path | None,
    cause_effect_review: Path | None,
    stdout: TextIO,
) -> None:
    """Verify one complete report evidence chain and print a stable summary."""

    try:
        input_count, report_count = verify_engineering_report_bundle(
            directory,
            source=source,
            alarm_review=alarm_review,
            cause_effect_review=cause_effect_review,
        )
    except ReportManifestError as error:
        raise ReportBundleCommandError(str(error)) from error
    stdout.write(
        f"Verified {input_count} inputs and {report_count} reports in {directory}\n"
    )
