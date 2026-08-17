"""Installed verification adapter for engineering-report bundles."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import TextIO

from twinforge.exporters import (
    ReportManifestError,
    engineering_report_manifest_schema_text,
    engineering_report_verification_schema_text,
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


def export_report_verification_schema(
    destination: Path,
    *,
    stdout: TextIO,
) -> None:
    """Write the installed report-verification result JSON Schema."""

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            engineering_report_verification_schema_text(),
            encoding="utf-8",
            newline="",
        )
    except (OSError, UnicodeError) as error:
        raise ReportBundleCommandError(
            f"could not export report verification schema to "
            f"'{destination}': {error}"
        ) from error
    stdout.write(
        f"Exported TwinForge report verification v1 schema to {destination}\n"
    )


def verify_report_bundle(
    directory: Path,
    *,
    source: Path,
    alarm_review: Path | None,
    cause_effect_review: Path | None,
    output_format: str = "text",
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
    if output_format == "json":
        manifest = directory / "report_manifest.json"
        try:
            manifest_digest = sha256(manifest.read_bytes()).hexdigest()
        except OSError as error:
            raise ReportBundleCommandError(
                f"cannot hash verified report manifest '{manifest}': {error}"
            ) from error
        stdout.write(
            json.dumps(
                {
                    "schema_version": (
                        "twinforge.engineering-report-verification.v1"
                    ),
                    "status": "valid",
                    "directory": str(directory),
                    "manifest_sha256": manifest_digest,
                    "input_count": input_count,
                    "report_count": report_count,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        return
    stdout.write(
        f"Verified {input_count} inputs and {report_count} reports in {directory}\n"
    )
