"""Installed command adapter for validated CODESYS deployment bundles."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

from twinforge.exporters.plcopen_library_package import LIBRARY_NAME, LIBRARY_VERSION, library_document
from twinforge.targets.codesys import (
    CodesysPowerFlex525BundleExporter,
    load_codesys_powerflex525_manifest,
)


class CodesysDeploymentCommandError(RuntimeError):
    """Raised when a CODESYS deployment bundle cannot be produced."""


def export_generated_block_library(destination: Path, *, stdout: TextIO) -> None:
    """Write the generated function blocks as PLCopen XML for a CODESYS library.

    `<name>.xml` holds the blocks, for a library project; `<name>_Tests.xml`
    adds a program replaying the recorded vendor checks, for a test project.
    """
    created = datetime.now(timezone.utc)
    files = {
        destination / f"{LIBRARY_NAME}.xml": library_document(creation_time=created),
        destination / f"{LIBRARY_NAME}_Tests.xml": library_document(creation_time=created, include_tests=True),
    }
    try:
        destination.mkdir(parents=True, exist_ok=True)
        for path, xml in files.items():
            path.write_text(xml, encoding="utf-8")
    except OSError as error:
        raise CodesysDeploymentCommandError(f"cannot write the block library to '{destination}': {error}") from error
    stdout.write(f"Wrote {LIBRARY_NAME} {LIBRARY_VERSION}:\n")
    for path in files:
        stdout.write(f"  {path}\n")


def export_codesys_powerflex525_bundle(
    manifest_path: Path,
    destination: Path,
    *,
    stdout: TextIO,
) -> None:
    """Validate a PowerFlex manifest and write its CODESYS bundle."""

    try:
        manifest = load_codesys_powerflex525_manifest(manifest_path)
        bundle = CodesysPowerFlex525BundleExporter().export(
            manifest,
            destination,
            manifest_directory=manifest_path.parent,
        )
    except (OSError, ValueError) as error:
        raise CodesysDeploymentCommandError(
            f"cannot export CODESYS deployment manifest "
            f"'{manifest_path}': {error}"
        ) from error
    stdout.write(f"Exported CODESYS deployment bundle to {bundle.directory}\n")
