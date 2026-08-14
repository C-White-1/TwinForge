"""Installed command adapter for validated CODESYS deployment bundles."""

from __future__ import annotations

from pathlib import Path
from typing import TextIO

from twinforge.targets.codesys import (
    CodesysPowerFlex525BundleExporter,
    load_codesys_powerflex525_manifest,
)


class CodesysDeploymentCommandError(RuntimeError):
    """Raised when a CODESYS deployment bundle cannot be produced."""


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
