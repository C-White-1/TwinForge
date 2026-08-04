"""Evidence-backed native OpenPLC Ladder project packaging."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from twinforge.exporters.plcopen_operands import PLCopenOperandPlanner
from twinforge.model import Controller

from .counter import shared_counter_names
from .native_declarations import (
    compatibility_block_documents,
    counter_names,
)
from .native_errors import OpenPLCNativeUnsupportedError
from .native_program import ladder_document
from .native_semantics import select_entrypoint, validate_program
from .native_timer import timer_instruction_types
from .native_packaging import (
    native_project_documents,
    write_native_project_documents,
)
from .native_validation import (
    validate_counter_accumulator_locations,
    validate_counter_status_locations,
    validate_locations,
    validate_timer_elapsed_locations,
)


OPENPLC_MAIN_PROGRAM = "main"


@dataclass(frozen=True)
class OpenPLCNativeProjectResult:
    """Files written for one native OpenPLC project directory."""

    destination: Path
    files: tuple[Path, ...]
    source_program_name: str
    native_program_name: str = OPENPLC_MAIN_PROGRAM


class OpenPLCNativeProjectExporter:
    """Package the proven local-BOOL, serial-XIC-to-OTE Ladder subset."""

    def export(
        self,
        controller: Controller,
        *,
        destination: str | Path,
        project_name: str | None = None,
        compile_only: bool = False,
        locations: Mapping[str, str] | None = None,
        timer_elapsed_locations: Mapping[str, str] | None = None,
        counter_accumulator_locations: Mapping[str, str] | None = None,
        counter_status_locations: Mapping[str, Mapping[str, str]] | None = None,
    ) -> OpenPLCNativeProjectResult:
        """Write a native OpenPLC project or reject unsupported semantics."""

        root = Path(destination)
        program, task_name, interval, priority = select_entrypoint(controller)
        operands = PLCopenOperandPlanner().prepare(controller)
        validate_program(controller, program, operands)
        routine = program.main_routine
        if routine is None:
            raise OpenPLCNativeUnsupportedError(
                f"program {program.name!r} has no main routine"
            )

        resolved_locations = dict(locations or {})
        validate_locations(program, resolved_locations)
        elapsed_locations = dict(timer_elapsed_locations or {})
        timer_types = timer_instruction_types(program, operands)
        validate_timer_elapsed_locations(
            operands,
            elapsed_locations,
            timer_types,
        )
        accumulator_locations = dict(counter_accumulator_locations or {})
        known_counter_names = counter_names(program)
        resolved_shared_counter_names = shared_counter_names(program)
        validate_counter_accumulator_locations(
            known_counter_names,
            accumulator_locations,
        )
        status_locations = {
            counter: {member.upper(): location for member, location in members.items()}
            for counter, members in (counter_status_locations or {}).items()
        }
        validate_counter_status_locations(
            resolved_shared_counter_names,
            status_locations,
        )
        ladder = ladder_document(
            program,
            OPENPLC_MAIN_PROGRAM,
            resolved_locations,
            operands,
            elapsed_locations,
            timer_types,
            accumulator_locations,
            resolved_shared_counter_names,
            status_locations,
        )
        documents = native_project_documents(
            project_name=project_name or controller.name or "TwinForge",
            task_name=task_name,
            interval=interval,
            priority=priority,
            native_program_name=OPENPLC_MAIN_PROGRAM,
            ladder=ladder,
            compile_only=compile_only,
        )
        documents.update(
            compatibility_block_documents(
                timer_types,
                resolved_shared_counter_names,
            )
        )
        written = write_native_project_documents(root, documents)
        return OpenPLCNativeProjectResult(
            root,
            written,
            source_program_name=program.name,
        )
