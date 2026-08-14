"""Installed command handlers for neutral-model JSON documents."""

from __future__ import annotations

from pathlib import Path
import json
from typing import Any, TextIO

from twinforge.exporters import (
    ModelJSONValidationError,
    model_json_inventory,
    validate_model_json,
)


class ModelJSONCommandError(RuntimeError):
    """Raised when an installed model-JSON operation cannot complete."""


def validate_model_json_file(path: Path, *, stdout: TextIO) -> None:
    """Validate one model JSON file and print its stable identity summary."""

    document = _read_model_json_file(path)

    evidence = document["document"]
    target_type = evidence.get("target_type", "unknown")
    target_name = evidence.get("target_name", "")
    suffix = f" '{target_name}'" if target_name else ""
    stdout.write(
        f"Valid TwinForge model JSON {document['schema_version']}: "
        f"{target_type}{suffix}.\n"
    )


def inspect_model_json_file(
    path: Path,
    *,
    output_format: str,
    stdout: TextIO,
) -> None:
    """Inventory validated model evidence without reconstructing model objects."""

    inventory = model_json_inventory(_read_model_json_file(path))
    if output_format == "json":
        stdout.write(json.dumps(inventory, indent=2, sort_keys=True) + "\n")
        return

    target_name = inventory["target_name"] or "(unnamed)"
    stdout.write(
        f"TwinForge model JSON {inventory['schema_version']}\n"
        f"Source format: {inventory['source_format']}\n"
        f"Target: {inventory['target_type']} '{target_name}'\n"
        f"Typed records: {inventory['record_count']}\n"
        f"References: {inventory['reference_count']}\n"
        f"Source extensions: {inventory['source_extension_count']}\n"
        f"Byte sequences: {inventory['byte_sequence_count']}\n"
        f"Typed maps: {inventory['typed_map_count']}\n"
        "Record types:\n"
    )
    for record_type, count in inventory["record_types"].items():
        stdout.write(f"  {record_type}: {count}\n")


def _read_model_json_file(path: Path) -> dict[str, Any]:
    """Read and validate one model JSON file through the public boundary."""

    try:
        if not path.is_file():
            raise FileNotFoundError(f"model JSON file does not exist: {path}")
        return validate_model_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ModelJSONValidationError) as error:
        raise ModelJSONCommandError(
            f"invalid TwinForge model JSON '{path}': {error}"
        ) from error
