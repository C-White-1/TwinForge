"""Read-only summaries of losslessly captured L5X documents."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any, TextIO

from twinforge.model import AddOnInstruction, Controller, Module, Program
from twinforge.parsers.l5x import L5XParser
from twinforge.parsers.l5x.document import L5XDocument


class L5XInspectionError(RuntimeError):
    """Raised when an L5X document cannot be inspected."""


def inspect_l5x(
    path: Path,
    *,
    output_format: str,
    stdout: TextIO,
) -> None:
    """Parse ``path`` and emit a stable text or JSON model summary."""
    try:
        document = L5XParser().parse_document(path, report_mode=None)
    except (ET.ParseError, OSError, ValueError) as error:
        raise L5XInspectionError(f"cannot inspect L5X '{path}': {error}") from error

    result = _document_summary(document, source=path)
    if output_format == "json":
        json.dump(result, stdout, indent=2)
        stdout.write("\n")
        return
    _write_text(result, stdout)


def _document_summary(document: L5XDocument, *, source: Path) -> dict[str, Any]:
    diagnostics = [
        {
            "severity": diagnostic.severity.value,
            "code": diagnostic.code,
            "message": diagnostic.message,
            "object_name": diagnostic.object_name,
            "field": diagnostic.field,
            "raw_value": diagnostic.raw_value,
        }
        for diagnostic in document.diagnostics
    ]
    return {
        "source": str(source),
        "target_type": document.target_type.value,
        "target_name": document.target_name,
        "context_controller_names": list(document.context_controller_names),
        "context_controller_tag_count": len(document.context_controller_tags),
        "summary": _target_summary(document.target),
        "diagnostics": diagnostics,
    }


def _target_summary(target: object) -> dict[str, Any]:
    if isinstance(target, Controller):
        modules = [
            module
            for chassis in target.chassis.values()
            for root in chassis.modules.values()
            for module in _walk_modules(root)
        ]
        routines = [
            routine
            for program in target.programs.values()
            for routine in program.routines.values()
        ]
        return {
            "name": target.name,
            "processor_type": target.identity.product_name,
            "chassis_count": len(target.chassis),
            "module_count": len(modules),
            "unplaced_module_count": len(target.unplaced_modules),
            "datatype_count": len(target.datatypes),
            "tag_count": len(target.tags),
            "program_count": len(target.programs),
            "task_count": len(target.tasks),
            "add_on_instruction_count": len(target.add_on_instructions),
            "routine_count": len(routines),
            "routine_languages": dict(
                sorted(Counter(routine.language or "unknown" for routine in routines).items())
            ),
        }
    if isinstance(target, Module):
        identity = target.identity
        key = target.electronic_key
        return {
            "name": target.name,
            "catalog_number": target.catalog,
            "slot": target.slot,
            "address": target.address,
            "vendor_id": identity.vendor.id if identity.vendor else None,
            "vendor_name": identity.vendor.name if identity.vendor else None,
            "product_type": identity.product_type,
            "product_code": identity.product_code,
            "revision": str(identity.revision) if identity.revision else None,
            "electronic_key_mode": key.mode.value if key and key.mode else None,
            "connection_count": len(target.connections),
            "child_module_count": len(target.child_modules),
        }
    if isinstance(target, Program):
        return {
            "name": target.name,
            "tag_count": len(target.tags),
            "routine_count": len(target.routines),
            "main_routine": target.main_routine.name if target.main_routine else None,
            "routine_languages": dict(
                sorted(
                    Counter(
                        routine.language or "unknown"
                        for routine in target.routines.values()
                    ).items()
                )
            ),
        }
    if isinstance(target, AddOnInstruction):
        return {
            "name": target.name,
            "revision": target.revision,
            "vendor": target.vendor,
            "parameter_count": len(target.parameters),
            "local_tag_count": len(target.local_tags),
            "routine_count": len(target.routines),
            "scan_mode_routine_count": len(target.scan_mode_routines),
            "dependency_count": len(target.dependencies),
            "execute_prescan": target.execute_prescan,
            "execute_postscan": target.execute_postscan,
            "execute_enable_in_false": target.execute_enable_in_false,
        }
    raise TypeError(f"unsupported L5X target model: {type(target).__name__}")


def _walk_modules(module: Module):
    yield module
    for child in module.child_modules:
        yield from _walk_modules(child)


def _write_text(result: dict[str, Any], stdout: TextIO) -> None:
    stdout.write(f"L5X target: {result['target_type']} {result['target_name']}\n")
    stdout.write(f"Source: {result['source']}\n")
    for key, value in result["summary"].items():
        stdout.write(f"{key.replace('_', ' ').title()}: {value}\n")
    counts = Counter(item["severity"] for item in result["diagnostics"])
    stdout.write(
        "Diagnostics: "
        f"{len(result['diagnostics'])} "
        f"(errors {counts['error']}, warnings {counts['warning']}, "
        f"info {counts['info']})\n"
    )
