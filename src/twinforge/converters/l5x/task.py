from __future__ import annotations

from collections.abc import Mapping

from twinforge.converters.diagnostics import (
    ConversionDiagnostic,
    DiagnosticSeverity,
)
from twinforge.model import Program, Task
from twinforge.parsers.l5x.capture import CapturedSection

from .source_extension import captured_to_source_extension


_KNOWN_TASK_TYPES = {"CONTINUOUS", "PERIODIC", "EVENT"}


def convert_task(
    section: CapturedSection,
    programs: Mapping[str, Program],
    *,
    diagnostics: list[ConversionDiagnostic] | None = None,
) -> Task:
    """Convert an L5X task and resolve its scheduled program references."""

    if section.tag != "Task":
        raise ValueError(f"expected a Task section, got {section.tag!r}")

    name = section.attributes.get("Name", "")
    task_type = section.attributes.get("Type")
    if not name:
        _emit(diagnostics, DiagnosticSeverity.ERROR, "task_missing_name", "task is missing its Name attribute")
    if task_type is not None and task_type not in _KNOWN_TASK_TYPES:
        _emit(
            diagnostics,
            DiagnosticSeverity.WARNING,
            "unknown_task_type",
            f"task {name!r} uses unknown type {task_type!r}",
            name,
            "Type",
            task_type,
        )

    task = Task(
        name=name,
        task_type=task_type,
        rate=_optional_int(section, "Rate", diagnostics),
        priority=_optional_int(section, "Priority", diagnostics),
        watchdog=_optional_int(section, "Watchdog", diagnostics),
        disable_update_outputs=_optional_bool(
            section, "DisableUpdateOutputs", diagnostics
        ),
        inhibited=_optional_bool(section, "InhibitTask", diagnostics),
        event_trigger=section.attributes.get("EventTrigger"),
        description=_description(section),
        source_extensions=[captured_to_source_extension(section)],
    )
    if task_type == "PERIODIC" and "Rate" not in section.attributes:
        _emit(
            diagnostics,
            DiagnosticSeverity.WARNING,
            "periodic_rate_missing",
            f"periodic task {name!r} does not specify Rate",
            name,
            "Rate",
        )

    for containers in section.elements.get("ScheduledPrograms", []):
        for reference in containers.elements.get("ScheduledProgram", []):
            program_name = reference.attributes.get("Name")
            if not program_name:
                _emit(
                    diagnostics,
                    DiagnosticSeverity.ERROR,
                    "scheduled_program_missing_name",
                    f"task {name!r} contains a scheduled program without a name",
                    name,
                )
                continue
            task.scheduled_program_names.append(program_name)
            program = programs.get(program_name)
            if program is None:
                _emit(
                    diagnostics,
                    DiagnosticSeverity.ERROR,
                    "unresolved_scheduled_program",
                    f"task {name!r} references unknown program {program_name!r}",
                    name,
                    "Name",
                    program_name,
                )
            else:
                task.scheduled_programs.append(program)

    return task


def _description(section: CapturedSection) -> str | None:
    descriptions = section.elements.get("Description", [])
    if not descriptions or descriptions[0].text is None:
        return None
    return descriptions[0].text.strip()


def _optional_int(
    section: CapturedSection,
    field: str,
    diagnostics: list[ConversionDiagnostic] | None,
) -> int | None:
    value = section.attributes.get(field)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        _emit(
            diagnostics,
            DiagnosticSeverity.WARNING,
            "invalid_integer",
            f"{field} must be an integer, got {value!r}",
            section.attributes.get("Name"),
            field,
            value,
        )
        return None


def _optional_bool(
    section: CapturedSection,
    field: str,
    diagnostics: list[ConversionDiagnostic] | None,
) -> bool | None:
    value = section.attributes.get(field)
    if value == "true":
        return True
    if value == "false":
        return False
    if value is not None:
        _emit(
            diagnostics,
            DiagnosticSeverity.WARNING,
            "invalid_boolean",
            f"{field} must be 'true' or 'false', got {value!r}",
            section.attributes.get("Name"),
            field,
            value,
        )
    return None


def _emit(
    diagnostics: list[ConversionDiagnostic] | None,
    severity: DiagnosticSeverity,
    code: str,
    message: str,
    object_name: str | None = None,
    field: str | None = None,
    raw_value: str | None = None,
) -> None:
    if diagnostics is None:
        return
    diagnostics.append(
        ConversionDiagnostic(
            severity=severity,
            code=code,
            message=message,
            object_name=object_name,
            field=field,
            raw_value=raw_value,
        )
    )
