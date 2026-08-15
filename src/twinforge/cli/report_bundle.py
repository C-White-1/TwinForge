"""Installed verification adapter for engineering-report bundles."""

from __future__ import annotations

from pathlib import Path
from typing import TextIO

from twinforge.exporters import (
    ReportManifestError,
    engineering_report_manifest_schema_text,
    verify_engineering_report_bundle,
)


class ReportBundleCommandError(RuntimeError):
    """Raised when an engineering-report bundle cannot be verified."""


def export_report_manifest_schema(destination: Path, *, stdout: TextIO) -> None:
    """Write the installed report-manifest JSON Schema."""

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            engineering_report_manifest_schema_text(),
            encoding="utf-8",
            newline="",
        )
    except (OSError, UnicodeError) as error:
        raise ReportBundleCommandError(
            f"could not export report manifest schema to '{destination}': {error}"
        ) from error
    stdout.write(f"Exported TwinForge report manifest v1 schema to {destination}\n")


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
