"""Installed commands for validated CCW project interchange artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TextIO

from twinforge.interchange import (
    CCWProjectArtifact,
    CCWProjectInterchangeError,
    ccw_project_inventory,
    ccw_project_schema_text,
    read_ccw_project,
)


class CCWProjectCommandError(RuntimeError):
    """Raised when a CCW project interchange command cannot complete."""


def validate_ccw_project_file(path: Path, *, stdout: TextIO) -> None:
    """Validate one artifact and print its stable source identity."""

    artifact = _read(path)
    stdout.write(
        f"Valid CCW project {artifact.schema_version}: "
        f"source '{artifact.source_reference}', SHA-256 {artifact.source_sha256}.\n"
    )


def inspect_ccw_project_file(
    path: Path,
    *,
    output_format: str,
    stdout: TextIO,
) -> None:
    """Inventory a validated artifact without semantic lowering."""

    inventory = ccw_project_inventory(_read(path))
    if output_format == "json":
        stdout.write(json.dumps(inventory, indent=2, sort_keys=True) + "\n")
        return
    project_name = inventory["project_name"] or "(unnamed)"
    controller = inventory["controller_catalog_number"] or "(unknown)"
    stdout.write(
        f"CCW project {inventory['schema_version']}\n"
        f"Source: {inventory['source_reference']}\n"
        f"Project: {project_name}\n"
        f"Controller: {controller}\n"
        f"Programs: {inventory['program_count']}\n"
        f"Rungs: {inventory['rung_count']}\n"
        f"Variables: {inventory['variable_count']}\n"
        f"Unresolved operands: {inventory['unresolved_operand_count']}\n"
        f"Diagnostics: {inventory['diagnostic_count']}\n"
        "Unknown evidence entries: "
        f"{inventory['unknown_evidence_entry_count']}\n"
    )


def export_ccw_project_schema(path: Path, *, stdout: TextIO) -> None:
    """Write the vendored producer schema to a user-selected path."""

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(ccw_project_schema_text(), encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise CCWProjectCommandError(
            f"could not write CCW project schema '{path}': {error}"
        ) from error
    stdout.write(f"Exported CCW project v1 schema to {path}\n")


def _read(path: Path) -> CCWProjectArtifact:
    try:
        return read_ccw_project(path)
    except CCWProjectInterchangeError as error:
        raise CCWProjectCommandError(
            f"invalid CCW project artifact '{path}': {error}"
        ) from error
