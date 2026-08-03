"""Specification-driven Rockwell counter grouping for OpenPLC lowering."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from collections.abc import Sequence

from twinforge.exporters.plcopen_rll import parse_supported_rung, split_arguments
from twinforge.exporters.plcopen_xml import decorated_member_integer
from twinforge.model import LadderRung, Program, Tag


class CounterOrder(str, Enum):
    """Source execution order when both counter directions occur."""

    UP_ONLY = "up_only"
    DOWN_ONLY = "down_only"
    UP_THEN_DOWN = "up_then_down"
    DOWN_THEN_UP = "down_then_up"


@dataclass(frozen=True)
class OpenPLCCounterGroup:
    """Canonical source rungs sharing one Rockwell COUNTER state owner."""

    counter_name: str
    count_up_name: str | None
    count_down_name: str | None
    reset_name: str
    output_name: str
    order: CounterOrder
    preset: int
    initial_accumulator: int
    initial_done: bool
    initial_overflow: bool
    initial_underflow: bool
    comment: str
    source_rung_count: int


def match_counter_group(program: Program, index: int) -> OpenPLCCounterGroup | None:
    """Match a canonical standalone or paired counter group at `index`."""

    routine = program.main_routine
    if routine is None:
        return None
    rungs = routine.ladder_rungs
    first = _count_instruction(rungs, index)
    if first is None:
        return None
    second = _count_instruction(rungs, index + 1)
    counts = [first]
    if second is not None and second[0] != first[0]:
        if second[2] != first[2]:
            return None
        counts.append(second)
    done_index = index + len(counts)
    reset_index = done_index + 1
    if reset_index >= len(rungs):
        return None
    counter_name = first[2]
    done = parse_supported_rung(rungs[done_index].text)
    reset = parse_supported_rung(rungs[reset_index].text)
    if (
        done is None
        or done.branches
        or done.tail_conditions != (("XIC", f"{counter_name}.DN"),)
        or len(done.outputs) != 1
        or done.outputs[0][0] != "OTE"
        or reset is None
        or reset.branches
        or len(reset.tail_conditions) != 1
        or reset.tail_conditions[0][0] != "XIC"
        or reset.outputs != (("RES", counter_name),)
    ):
        return None
    tag = program.tags.get(counter_name)
    if tag is None or (tag.data_type or "").upper() != "COUNTER":
        return None
    up_name = next((item[1] for item in counts if item[0] == "CTU"), None)
    down_name = next((item[1] for item in counts if item[0] == "CTD"), None)
    order = _counter_order(tuple(item[0] for item in counts))
    return OpenPLCCounterGroup(
        counter_name=counter_name,
        count_up_name=up_name,
        count_down_name=down_name,
        reset_name=reset.tail_conditions[0][1],
        output_name=done.outputs[0][1],
        order=order,
        preset=_required_member(tag, "PRE"),
        initial_accumulator=_member_or_default(tag, "ACC", 0),
        initial_done=bool(_member_or_default(tag, "DN", 0)),
        initial_overflow=bool(_member_or_default(tag, "OV", 0)),
        initial_underflow=bool(_member_or_default(tag, "UN", 0)),
        comment=next(
            (
                rung.comment
                for rung in rungs[index : reset_index + 1]
                if rung.comment
            ),
            "",
        ),
        source_rung_count=len(counts) + 2,
    )


def _count_instruction(
    rungs: Sequence[LadderRung],
    index: int,
) -> tuple[str, str, str] | None:
    if index >= len(rungs):
        return None
    parsed = parse_supported_rung(rungs[index].text)
    if (
        parsed is None
        or parsed.branches
        or len(parsed.tail_conditions) != 1
        or parsed.tail_conditions[0][0] != "XIC"
        or len(parsed.outputs) != 1
        or parsed.outputs[0][0] not in {"CTU", "CTD"}
    ):
        return None
    arguments = split_arguments(parsed.outputs[0][1])
    if len(arguments) != 3:
        return None
    return parsed.outputs[0][0], parsed.tail_conditions[0][1], arguments[0]


def _counter_order(instructions: tuple[str, ...]) -> CounterOrder:
    if instructions == ("CTU",):
        return CounterOrder.UP_ONLY
    if instructions == ("CTD",):
        return CounterOrder.DOWN_ONLY
    if instructions == ("CTU", "CTD"):
        return CounterOrder.UP_THEN_DOWN
    if instructions == ("CTD", "CTU"):
        return CounterOrder.DOWN_THEN_UP
    raise ValueError(f"unsupported counter instruction order: {instructions!r}")


def _required_member(tag: Tag, name: str) -> int:
    value = decorated_member_integer(tag, name)
    if value is None:
        raise ValueError(f"COUNTER {tag.name!r} has no readable decorated {name}")
    return value


def _member_or_default(tag: Tag, name: str, default: int) -> int:
    value = decorated_member_integer(tag, name)
    return default if value is None else value
