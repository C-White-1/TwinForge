"""Admit only source semantics evidenced by the native OpenPLC target."""

from __future__ import annotations

from twinforge.exporters.plcopen_operands import PLCopenOperandPlan
from twinforge.exporters.plcopen_rll import parse_supported_rung
from twinforge.model import Controller, Program

from .counter import match_counter_group
from .native_errors import OpenPLCNativeUnsupportedError
from .native_timer import match_timer_group


def select_entrypoint(controller: Controller) -> tuple[Program, str, str, int]:
    """Select the single task and program supported by the evidenced format."""

    if len(controller.tasks) != 1:
        raise OpenPLCNativeUnsupportedError(
            "the evidenced native subset requires exactly one task"
        )
    task = next(iter(controller.tasks.values()))
    if len(task.scheduled_programs) != 1:
        raise OpenPLCNativeUnsupportedError(
            "the evidenced native subset requires one scheduled program"
        )
    program = task.scheduled_programs[0]
    rate = task.rate if task.rate is not None else 20
    priority = task.priority if task.priority is not None else 1
    return program, task.name or "task0", f"T#{rate}ms", priority


def validate_program(
    controller: Controller,
    program: Program,
    operands: PLCopenOperandPlan,
) -> None:
    """Reject source constructs outside the runtime-evidenced native subset."""

    if controller.tags:
        raise OpenPLCNativeUnsupportedError(
            "native OpenPLC global-variable representation is not yet evidenced"
        )
    if len(program.routines) != 1:
        raise OpenPLCNativeUnsupportedError(
            "the evidenced native subset requires exactly one routine"
        )
    unsupported = [
        tag.name
        for tag in program.iter_tags()
        if (tag.data_type or "").casefold() not in {"bool", "timer", "counter"}
    ]
    if unsupported:
        raise OpenPLCNativeUnsupportedError(
            "only local BOOL variables are evidenced: " + ", ".join(unsupported)
        )
    routine = program.main_routine
    if routine is None:
        return
    rung_index = 0
    while rung_index < len(routine.ladder_rungs):
        rung = routine.ladder_rungs[rung_index]
        parsed = parse_supported_rung(rung.text)
        if parsed is None:
            raise OpenPLCNativeUnsupportedError(
                f"rung {rung.number!r} is outside the evidenced XIC-to-OTE subset"
            )
        timer_group = match_timer_group(program, rung_index, operands)
        if timer_group is not None:
            rung_index += timer_group.source_rung_count
            continue
        counter_group = match_counter_group(program, rung_index)
        if counter_group is not None:
            rung_index += counter_group.source_rung_count
            continue
        serial_supported = (
            not parsed.branches
            and bool(parsed.tail_conditions)
            and all(opcode == "XIC" for opcode, _ in parsed.tail_conditions)
        )
        parallel_supported = (
            len(parsed.branches) == 2
            and all(
                len(branch) == 1 and branch[0][0] == "XIC"
                for branch in parsed.branches
            )
            and (
                not parsed.tail_conditions
                or (
                    len(parsed.tail_conditions) == 1
                    and parsed.tail_conditions[0][0] in {"XIC", "XIO"}
                )
            )
        )
        if (
            not (serial_supported or parallel_supported)
            or len(parsed.outputs) != 1
            or parsed.outputs[0][0] != "OTE"
        ):
            raise OpenPLCNativeUnsupportedError(
                f"rung {rung.number!r} is outside the evidenced "
                "serial/parallel-XIC-to-OTE subset"
            )
        rung_index += 1
