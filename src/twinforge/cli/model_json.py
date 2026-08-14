"""Installed command handlers for neutral-model JSON documents."""

from __future__ import annotations

from pathlib import Path
from typing import TextIO

from twinforge.exporters import ModelJSONValidationError, validate_model_json


class ModelJSONCommandError(RuntimeError):
    """Raised when an installed model-JSON operation cannot complete."""


def validate_model_json_file(path: Path, *, stdout: TextIO) -> None:
    """Validate one model JSON file and print its stable identity summary."""

    try:
        if not path.is_file():
            raise FileNotFoundError(f"model JSON file does not exist: {path}")
        document = validate_model_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ModelJSONValidationError) as error:
        raise ModelJSONCommandError(
            f"invalid TwinForge model JSON '{path}': {error}"
        ) from error

    evidence = document["document"]
    target_type = evidence.get("target_type", "unknown")
    target_name = evidence.get("target_name", "")
    suffix = f" '{target_name}'" if target_name else ""
    stdout.write(
        f"Valid TwinForge model JSON {document['schema_version']}: "
        f"{target_type}{suffix}.\n"
    )
