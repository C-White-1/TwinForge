"""Installed commands for validated CCW project interchange artifacts."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
from typing import TextIO

from twinforge.converters import ConversionDiagnostic
from twinforge.converters.ccw import lower_ccw_project
from twinforge.exporters import PLCopenExporter, PLCopenProfile
from twinforge.interchange import (
    CCWProjectArtifact,
    CCWProjectInterchangeError,
    ccw_project_inventory,
    ccw_project_schema_text,
    read_ccw_project,
)
from twinforge.model import Controller, IODirection, IOSignalType, Tag
from twinforge.targets.codesys import plan_ccw_codesys_project


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


def inspect_lowered_ccw_project(
    path: Path,
    *,
    output_format: str,
    stdout: TextIO,
) -> None:
    """Summarise neutral lowering without generating a target artifact."""

    result = lower_ccw_project(_read(path))
    controller = result.controller
    programs = tuple(controller.iter_programs())
    routines = tuple(
        routine for program in programs for routine in program.iter_routines()
    )
    summary = {
        "schema_version": result.artifact.schema_version,
        "controller_name": controller.name,
        "tag_count": len(controller.tags),
        "program_count": len(programs),
        "routine_count": len(routines),
        "rung_count": sum(len(routine.ladder_rungs) for routine in routines),
        "converted_instruction_count": result.converted_instruction_count,
        "unsupported_instruction_count": result.unsupported_instruction_count,
        "diagnostic_count": len(result.diagnostics),
    }
    if output_format == "json":
        stdout.write(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        return
    stdout.write(
        "Neutral CCW lowering (no target export)\n"
        f"Schema: {summary['schema_version']}\n"
        f"Controller: {summary['controller_name']}\n"
        f"Tags: {summary['tag_count']}\n"
        f"Programs: {summary['program_count']}\n"
        f"Routines: {summary['routine_count']}\n"
        f"Rungs: {summary['rung_count']}\n"
        f"Converted instructions: {summary['converted_instruction_count']}\n"
        f"Unsupported instructions: {summary['unsupported_instruction_count']}\n"
        f"Diagnostics: {summary['diagnostic_count']}\n"
    )


_CCW_IO_ADDRESS = re.compile(r"(?:^|_)(?P<code>DI|DO|AI|AO)_\d+$", re.IGNORECASE)
_CCW_IO_KINDS = {
    "DI": (IODirection.INPUT, IOSignalType.DIGITAL),
    "DO": (IODirection.OUTPUT, IOSignalType.DIGITAL),
    "AI": (IODirection.INPUT, IOSignalType.ANALOG),
    "AO": (IODirection.OUTPUT, IOSignalType.ANALOG),
}


def summarize_ccw_physical_io(
    path: Path,
    *,
    output_format: str,
    stdout: TextIO,
) -> None:
    """Size the physical I/O a CCW project requires, independent of any target.

    Reports direction/signal type using the same `IODirection`/`IOSignalType`
    vocabulary and `assigned`/`spare` status as the L5X `io_list` report
    (src/twinforge/analysis/io_list.py), so a human sizing hardware across a
    mixed CCW/L5X fleet reads both the same way. Unlike L5X's module capability
    decoding, CCW never declares a channel's nominal/configured count, so
    there is no `unavailable_by_configuration` status here. CCW's own
    buffer-program convention also makes `assigned` a weaker signal of actual
    use than in L5X, because CCW commonly auto-generates a buffer variable for
    every embedded point whether or not the logic uses it; `assigned_unaliased`
    below distinguishes a bound-but-unnamed point from a bound-and-named one.
    """

    artifact = _read(path)
    lowering = lower_ccw_project(artifact)
    document = artifact.to_document()
    points, unresolved = _physical_io_points(lowering.controller)
    status_counts = Counter(point["assignment_status"] for point in points)
    assigned_unaliased = sum(
        1
        for point in points
        if point["assignment_status"] == "assigned" and not point["aliases"]
    )
    signal_counts = Counter(
        (point["direction"] or "unknown", point["signal_type"] or "unknown")
        for point in points
    )
    summary = {
        "controller_catalog_number": document["controller"]["catalog_number"],
        "total_point_count": len(points),
        "counts_by_assignment_status": dict(sorted(status_counts.items())),
        "assigned_unaliased_point_count": assigned_unaliased,
        "counts_by_direction_and_signal_type": {
            f"{direction}/{signal_type}": count
            for (direction, signal_type), count in sorted(signal_counts.items())
        },
        "points": points,
        "unresolved_bindings": unresolved,
    }
    if output_format == "json":
        stdout.write(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        return
    stdout.write(
        "CCW physical I/O sizing summary (source evidence only; no target"
        " selected)\n"
        f"Controller: {summary['controller_catalog_number'] or '(unknown)'}\n"
        f"Total physical I/O points: {summary['total_point_count']}\n"
    )
    for status, count in summary["counts_by_assignment_status"].items():
        stdout.write(f"  {status}: {count}\n")
    stdout.write("By direction and signal type:\n")
    for key, count in summary["counts_by_direction_and_signal_type"].items():
        stdout.write(f"  {key}: {count}\n")
    stdout.write(
        "Assigned points with no recorded alias (likely auto-buffered "
        f"spares): {summary['assigned_unaliased_point_count']}\n"
    )
    if unresolved:
        stdout.write(
            f"Unresolved bindings (no matching physical_io variable): "
            f"{len(unresolved)}\n"
        )
        for item in unresolved:
            stdout.write(f"  {item['tag_name']} -> {item['physical_address']}\n")


def _physical_io_points(
    controller: Controller,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Report every known physical point plus any binding that matches none."""

    bindings: dict[str, list[tuple[Tag, str]]] = {}
    for tag in controller.iter_tags():
        source = tag.metadata.get("physical_source")
        if source:
            bindings.setdefault(source, []).append((tag, "input"))
        destination = tag.metadata.get("physical_destination")
        if destination:
            bindings.setdefault(destination, []).append((tag, "output"))

    physical_tags = {
        tag.name: tag
        for tag in controller.iter_tags()
        if tag.metadata.get("ccw_classification") == "physical_io"
    }

    points = [
        _physical_io_point(name, tag, bindings.get(name, []))
        for name, tag in sorted(physical_tags.items())
    ]
    unresolved: list[dict[str, object]] = [
        {
            "tag_name": tag.name,
            "physical_address": address,
            "reason": "no matching physical_io-classified CCW variable",
        }
        for address in sorted(set(bindings) - set(physical_tags))
        for tag, _ in bindings[address]
    ]
    return points, unresolved


def _physical_io_point(
    address: str,
    physical_tag: Tag,
    linked: list[tuple[Tag, str]],
) -> dict[str, object]:
    direction, signal_type = _classify_ccw_address(address)
    if direction is None:
        bound_directions = {value for _, value in linked}
        if len(bound_directions) == 1:
            direction = (
                IODirection.INPUT
                if bound_directions.pop() == "input"
                else IODirection.OUTPUT
            )
    if signal_type is None:
        data_type = physical_tag.data_type or next(
            (tag.data_type for tag, _ in linked if tag.data_type), None
        )
        if data_type is not None:
            signal_type = (
                IOSignalType.DIGITAL
                if data_type.upper() == "BOOL"
                else IOSignalType.ANALOG
            )
    alias_sources = [tag for tag, _ in linked]
    alias_sources.append(physical_tag)
    aliases = sorted(
        {alias for tag in alias_sources for alias in tag.metadata.get("aliases", [])}
    )
    variable_names = sorted({tag.name for tag, _ in linked})
    return {
        "physical_address": address,
        "direction": direction.value if direction is not None else None,
        "signal_type": signal_type.value if signal_type is not None else None,
        "data_type": physical_tag.data_type,
        "assignment_status": "assigned" if linked else "spare",
        "variable_names": variable_names,
        "aliases": aliases,
    }


def _classify_ccw_address(
    address: str,
) -> tuple[IODirection | None, IOSignalType | None]:
    match = _CCW_IO_ADDRESS.search(address)
    if match is None:
        return None, None
    return _CCW_IO_KINDS[match.group("code").upper()]


def export_ccw_codesys_project(
    path: Path,
    *,
    destination: Path,
    coverage_path: Path,
    task_rate_ms: int,
    stdout: TextIO,
) -> None:
    """Export validated CCW evidence through the neutral CODESYS boundary."""

    if task_rate_ms <= 0:
        raise CCWProjectCommandError("--task-rate-ms must be greater than zero")
    lowering = lower_ccw_project(_read(path))
    plan = plan_ccw_codesys_project(
        lowering.controller,
        task_rate_ms=task_rate_ms,
    )
    exported = PLCopenExporter(PLCopenProfile.CODESYS).export(
        plan.controller,
        project_name=plan.controller.name,
    )
    classification_counts = Counter(
        tag.metadata.get("ccw_classification") for tag in plan.controller.iter_tags()
    )
    user_count = classification_counts["user"]
    physical_io_count = classification_counts["physical_io"]
    other_count = len(plan.controller.tags) - user_count - physical_io_count
    coverage = {
        "schema_version": lowering.artifact.schema_version,
        "source_reference": lowering.artifact.source_reference,
        "source_sha256": lowering.artifact.source_sha256,
        "target": "codesys-plcopen-xml",
        "task_rate_ms": task_rate_ms,
        "global_variable_count": len(plan.controller.tags),
        "user_variable_count": user_count,
        "physical_io_variable_count": physical_io_count,
        "other_classification_variable_count": other_count,
        "physical_io_binding_status": (
            "requires_codesys_device_mapping" if physical_io_count else "not_applicable"
        ),
        "converted_instruction_count": lowering.converted_instruction_count,
        "unsupported_instruction_count": lowering.unsupported_instruction_count,
        "converted_rung_count": plan.converted_rung_count,
        "preserved_rung_count": plan.preserved_rung_count,
        "empty_rung_count": plan.empty_rung_count,
        "rungs": [
            {
                "program": item.program,
                "rung": item.rung,
                "status": item.status,
                "reason": item.reason,
            }
            for item in plan.coverage
        ],
        "diagnostics": [
            _diagnostic_record(item)
            for item in (
                *lowering.diagnostics,
                *plan.diagnostics,
                *exported.diagnostics,
            )
        ],
    }
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(exported.xml, encoding="utf-8")
        coverage_path.parent.mkdir(parents=True, exist_ok=True)
        coverage_path.write_text(
            json.dumps(coverage, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except (OSError, UnicodeError) as error:
        raise CCWProjectCommandError(
            f"could not write CCW CODESYS export: {error}"
        ) from error
    stdout.write(
        f"Exported CODESYS PLCopen XML to {destination}\n"
        f"Wrote conversion coverage to {coverage_path}\n"
        f"Converted rungs: {plan.converted_rung_count}\n"
        f"Empty no-op rungs: {plan.empty_rung_count}\n"
        f"Preserved rungs: {plan.preserved_rung_count}\n"
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


def _diagnostic_record(diagnostic: ConversionDiagnostic) -> dict[str, object]:
    return {
        "severity": diagnostic.severity.value,
        "code": diagnostic.code,
        "message": diagnostic.message,
        "object_name": diagnostic.object_name,
        "raw_value": diagnostic.raw_value,
    }
