"""Installed command handlers for neutral-model JSON documents."""

from __future__ import annotations

from pathlib import Path
import json
from typing import Any, TextIO

from twinforge.exporters import (
    compare_model_json,
    ModelJSONValidationError,
    ModelJSONPointerError,
    model_json_inventory,
    model_json_records,
    model_json_schema_text,
    resolve_model_json_pointer,
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


def export_model_json_schema(path: Path, *, stdout: TextIO) -> None:
    """Write the packaged neutral-model JSON Schema to a user path."""

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(model_json_schema_text(), encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ModelJSONCommandError(
            f"could not write TwinForge model JSON schema '{path}': {error}"
        ) from error
    stdout.write(f"Exported TwinForge model JSON 1.0 schema to {path}\n")


def query_model_json_file(
    path: Path,
    pointer: str,
    *,
    resolve_reference: bool,
    compact: bool,
    stdout: TextIO,
) -> None:
    """Write one validated evidence node selected by JSON Pointer."""

    try:
        selected = resolve_model_json_pointer(
            _read_model_json_file(path),
            pointer,
            resolve_reference=resolve_reference,
        )
    except ModelJSONPointerError as error:
        raise ModelJSONCommandError(
            f"could not query TwinForge model JSON '{path}': {error}"
        ) from error
    if compact:
        stdout.write(
            json.dumps(selected, ensure_ascii=False, separators=(",", ":"))
            + "\n"
        )
    else:
        stdout.write(
            json.dumps(selected, indent=2, sort_keys=True, ensure_ascii=False)
            + "\n"
        )


def list_model_json_records(
    path: Path,
    *,
    record_type: str | None,
    output_format: str,
    stdout: TextIO,
) -> None:
    """List typed evidence records and their stable JSON Pointers."""

    records = model_json_records(
        _read_model_json_file(path),
        record_type=record_type,
    )
    if output_format == "json":
        stdout.write(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "record_type": record_type,
                    "count": len(records),
                    "records": records,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        return

    heading = f"Typed records ({record_type or 'all'}): {len(records)}\n"
    stdout.write(heading)
    for record in records:
        name = f" '{record['name']}'" if "name" in record else ""
        stdout.write(f"  {record['type']}{name}: {record['pointer']}\n")


def compare_model_json_files(
    before_path: Path,
    after_path: Path,
    *,
    output_format: str,
    stdout: TextIO,
) -> None:
    """Compare two validated model artifacts without semantic inference."""

    changes = compare_model_json(
        _read_model_json_file(before_path),
        _read_model_json_file(after_path),
    )
    if output_format == "json":
        stdout.write(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "before": str(before_path),
                    "after": str(after_path),
                    "change_count": len(changes),
                    "changes": changes,
                },
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            + "\n"
        )
        return

    stdout.write(f"Model evidence changes: {len(changes)}\n")
    for change in changes:
        stdout.write(f"  {change['operation']} {change['pointer']}\n")


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
