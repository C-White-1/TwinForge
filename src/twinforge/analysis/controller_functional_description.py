"""Assemble a vendor-neutral controller functional-description draft."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from twinforge.model import Controller, Module, Program

from .alarm_candidates import AlarmTripCandidateReport
from .cause_effect import CauseEffectCandidateReport
from .io_list import IOListReport
from .software_calls import extract_program_calls
from .tag_dependencies import TagDependencyGraph


@dataclass(frozen=True)
class TaskExecutionDescription:
    """Captured task configuration and scheduled-program evidence."""

    name: str
    task_type: str | None
    rate: int | None
    priority: int | None
    watchdog: int | None
    inhibited: bool | None
    scheduled_programs: tuple[str, ...]
    unresolved_programs: tuple[str, ...]


@dataclass(frozen=True)
class ProgramStructureDescription:
    """Captured program/routine inventory without inferred process purpose."""

    name: str
    disabled: bool | None
    main_routine: str | None
    routine_names: tuple[str, ...]
    routine_languages: tuple[str, ...]
    ladder_rung_count: int
    structured_text_line_count: int
    observed_call_targets: tuple[str, ...]
    program_tag_count: int


@dataclass(frozen=True)
class ControllerFunctionalDescription:
    """Evidence-backed overview of one captured controller application."""

    controller_name: str
    product_name: str | None
    vendor: str | None
    revision: str | None
    chassis_count: int
    module_count: int
    controller_tag_count: int
    datatype_count: int
    add_on_instruction_count: int
    tasks: tuple[TaskExecutionDescription, ...]
    programs: tuple[ProgramStructureDescription, ...]
    io_channel_count: int
    assigned_io_count: int
    alarm_trip_candidate_count: int
    cause_effect_candidate_count: int
    resolved_dependency_count: int
    unresolved_dependency_count: int
    boundaries: tuple[str, ...]


def build_controller_functional_description(
    controller: Controller,
    dependencies: TagDependencyGraph,
    io_list: IOListReport,
    alarms: AlarmTripCandidateReport,
    cause_effect: CauseEffectCandidateReport,
) -> ControllerFunctionalDescription:
    """Aggregate existing analyses into a controller-level review document."""
    resolved_programs = {
        task.name: {program.name for program in task.scheduled_programs}
        for task in controller.iter_tasks()
    }
    tasks = tuple(
        TaskExecutionDescription(
            name=task.name,
            task_type=task.task_type,
            rate=task.rate,
            priority=task.priority,
            watchdog=task.watchdog,
            inhibited=task.inhibited,
            scheduled_programs=tuple(
                program.name for program in task.scheduled_programs
            ),
            unresolved_programs=tuple(
                name
                for name in task.scheduled_program_names
                if name not in resolved_programs[task.name]
            ),
        )
        for task in sorted(controller.iter_tasks(), key=lambda item: item.name)
    )
    programs = tuple(
        _program_description(program)
        for program in sorted(controller.iter_programs(), key=lambda item: item.name)
    )
    identity = controller.identity
    return ControllerFunctionalDescription(
        controller_name=controller.name,
        product_name=identity.product_name,
        vendor=str(identity.vendor) if identity.vendor is not None else None,
        revision=str(identity.revision) if identity.revision is not None else None,
        chassis_count=len(controller.chassis),
        module_count=sum(1 for _ in _modules(controller)),
        controller_tag_count=len(controller.tags),
        datatype_count=len(controller.datatypes),
        add_on_instruction_count=len(controller.add_on_instructions),
        tasks=tasks,
        programs=programs,
        io_channel_count=len(io_list.channels),
        assigned_io_count=sum(
            item.assignment_status == "assigned" for item in io_list.channels
        ),
        alarm_trip_candidate_count=len(alarms.candidates),
        cause_effect_candidate_count=len(cause_effect.candidates),
        resolved_dependency_count=len(dependencies.references),
        unresolved_dependency_count=len(dependencies.unresolved_references),
        boundaries=(
            "Program and routine names are retained as evidence and are not "
            "treated as verified statements of process intent.",
            "Alarm/trip and cause-and-effect entries are candidates requiring "
            "engineering review.",
            "Unsupported routine languages and unresolved operands may contain "
            "additional behavior not represented in this draft.",
            "This software description does not establish mechanical, electrical, "
            "process-safety, or commissioning requirements.",
        ),
    )


def _program_description(program: Program) -> ProgramStructureDescription:
    routines = tuple(program.iter_routines())
    calls = extract_program_calls(program)
    return ProgramStructureDescription(
        name=program.name,
        disabled=program.disabled,
        main_routine=(program.main_routine.name if program.main_routine else None),
        routine_names=tuple(routine.name for routine in routines),
        routine_languages=tuple(
            sorted(
                {routine.language or "unknown" for routine in routines},
                key=str.casefold,
            )
        ),
        ladder_rung_count=sum(len(routine.ladder_rungs) for routine in routines),
        structured_text_line_count=sum(
            len(routine.structured_text_lines) for routine in routines
        ),
        observed_call_targets=tuple(
            sorted({call.callee for call in calls}, key=str.casefold)
        ),
        program_tag_count=len(program.tags),
    )


def _modules(controller: Controller) -> Iterator[Module]:
    pending = [
        module
        for chassis in controller.iter_chassis()
        for module in chassis.iter_modules()
    ] + list(controller.unplaced_modules)
    while pending:
        module = pending.pop(0)
        yield module
        pending.extend(module.child_modules)
