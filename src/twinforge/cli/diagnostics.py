"""Stable process outcomes and machine-readable CLI diagnostics."""

from __future__ import annotations

import json
from enum import IntEnum
from pathlib import Path
from typing import Any, TextIO


class ExitCode(IntEnum):
    """Documented process exit codes used by installed TwinForge commands."""

    SUCCESS = 0
    INVALID_INPUT = 2
    UNSUPPORTED = 3
    VALIDATION_FAILED = 4
    OPERATION_FAILED = 5


def write_json_diagnostic(
    stream: TextIO,
    *,
    status: str,
    operation: str,
    exit_code: ExitCode,
    message: str,
    target: str | None = None,
    source: Path | None = None,
    destination: Path | None = None,
    dry_run: bool | None = None,
    outputs: tuple[Path, ...] = (),
    diagnostics: tuple[dict[str, Any], ...] = (),
) -> None:
    """Write one versioned JSON object suitable for CI and subprocesses."""
    document: dict[str, Any] = {
        "schema_version": "1.0",
        "status": status,
        "operation": operation,
        "exit_code": int(exit_code),
        "message": message,
        "diagnostics": list(diagnostics),
    }
    if target is not None:
        document["target"] = target
    if source is not None:
        document["source"] = str(source)
    if destination is not None:
        document["destination"] = str(destination)
    if dry_run is not None:
        document["dry_run"] = dry_run
    if outputs:
        document["outputs"] = [str(path) for path in outputs]
    stream.write(json.dumps(document, indent=2, sort_keys=True) + "\n")
