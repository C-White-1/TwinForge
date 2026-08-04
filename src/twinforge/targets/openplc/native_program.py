"""Assemble a native OpenPLC Ladder program from admitted source groups."""

from __future__ import annotations

from collections.abc import Mapping
import json

from twinforge.exporters.plcopen_operands import PLCopenOperandPlan
from twinforge.model import Program

from .counter import lower_counter_group, match_counter_group
from .native_declarations import variable_declaration
from .native_ladder import lower_boolean_rung
from .native_timer import elapsed_conversion_rung, lower_timer_group, match_timer_group


def ladder_document(
    program: Program,
    native_name: str,
    locations: Mapping[str, str],
    operands: PLCopenOperandPlan,
    elapsed_locations: Mapping[str, str],
    timer_types: Mapping[str, str],
    accumulator_locations: Mapping[str, str],
    shared_counter_names: set[str],
    status_locations: Mapping[str, Mapping[str, str]],
) -> str:
    """Render declarations and ordered native Ladder rungs for one program."""

    routine = program.main_routine
    assert routine is not None
    declaration_lines = [
        variable_declaration(
            tag.name,
            tag.data_type,
            locations.get(tag.name),
            timer_types.get(tag.name, "TON"),
            tag.name in shared_counter_names,
        )
        for tag in program.iter_tags()
    ]
    for timer_name, location in elapsed_locations.items():
        declaration_lines.extend(
            [
                f"\t{timer_name}_ET : TIME;",
                f"\t{timer_name}_ElapsedSeconds : DINT AT {location};",
            ]
        )
    for counter_name, location in accumulator_locations.items():
        declaration_lines.append(f"\t{counter_name}_ACC : DINT AT {location};")
    for counter_name, members in status_locations.items():
        declaration_lines.extend(
            f"\t{counter_name}_{member} : BOOL AT {location};"
            for member, location in members.items()
        )
    declarations = "\n".join(declaration_lines)
    header = f"PROGRAM {native_name}\nVAR\n{declarations}\nEND_VAR\n\n"
    rungs: list[dict[str, object]] = []
    source_index = 0
    while source_index < len(routine.ladder_rungs):
        counter_group = match_counter_group(program, source_index)
        if counter_group is not None:
            rungs.append(
                lower_counter_group(
                    native_name,
                    len(rungs),
                    counter_group,
                    accumulator_name=(
                        f"{counter_group.counter_name}_ACC"
                        if counter_group.counter_name in accumulator_locations
                        else None
                    ),
                    status_names={
                        member: f"{counter_group.counter_name}_{member}"
                        for member in status_locations.get(
                            counter_group.counter_name,
                            {},
                        )
                    },
                )
            )
            source_index += counter_group.source_rung_count
            continue
        timer_group = match_timer_group(program, source_index, operands)
        if timer_group is not None:
            elapsed_location = elapsed_locations.get(timer_group.timer_name)
            elapsed_name = (
                f"{timer_group.timer_name}_ET" if elapsed_location else None
            )
            rungs.append(
                lower_timer_group(
                    native_name,
                    len(rungs),
                    timer_group,
                    elapsed_name=elapsed_name,
                )
            )
            if elapsed_location:
                rungs.append(
                    elapsed_conversion_rung(
                        native_name,
                        len(rungs),
                        timer_group.timer_name,
                        elapsed_location,
                    )
                )
            source_index += timer_group.source_rung_count
            continue
        rung = routine.ladder_rungs[source_index]
        rungs.append(
            lower_boolean_rung(
                native_name,
                len(rungs),
                rung.text or "",
                rung.comment or "",
            )
        )
        source_index += 1
    body = json.dumps({"name": native_name, "rungs": rungs}, indent=2)
    return f"{header}{body}\nEND_PROGRAM\n"
