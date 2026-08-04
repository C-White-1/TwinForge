"""Specification-driven Rockwell counter grouping for OpenPLC lowering."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from collections.abc import Mapping, Sequence

from twinforge.exporters.plcopen_rll import parse_supported_rung, split_arguments
from twinforge.exporters.plcopen_xml import decorated_member_integer
from twinforge.model import LadderRung, Program, Tag

from .native_blocks import (
    block_connector,
    block_variable,
    block_variable_node,
    native_variable,
)
from .native_errors import OpenPLCNativeUnsupportedError
from .native_graph import edge, instruction_node, numeric_id, rail_node, stable_uuid


TF_COUNTER_BODY = """IF NOT Initialized THEN
    CV := INITIAL_ACC;
    Q := INITIAL_DN;
    OV := INITIAL_OV;
    UN := INITIAL_UN;
    WasCU := CU;
    WasCD := CD;
    Initialized := TRUE;
END_IF;

CUEnabled := CU;
CDEnabled := CD;
UpEdge := CU AND NOT WasCU;
DownEdge := CD AND NOT WasCD;

IF RESET THEN
    CV := 0;
    Q := FALSE;
    OV := FALSE;
    UN := FALSE;
    CUEnabled := FALSE;
    CDEnabled := FALSE;
    WasCU := FALSE;
    WasCD := FALSE;
ELSE
    IF UP_FIRST THEN
        IF UpEdge THEN
            IF CV = 2147483647 THEN
                CV := -2147483647 - 1;
                OV := TRUE;
            ELSE
                CV := CV + 1;
            END_IF;
        END_IF;
        IF DownEdge THEN
            IF CV = -2147483647 - 1 THEN
                CV := 2147483647;
                UN := TRUE;
            ELSE
                CV := CV - 1;
            END_IF;
        END_IF;
    ELSE
        IF DownEdge THEN
            IF CV = -2147483647 - 1 THEN
                CV := 2147483647;
                UN := TRUE;
            ELSE
                CV := CV - 1;
            END_IF;
        END_IF;
        IF UpEdge THEN
            IF CV = 2147483647 THEN
                CV := -2147483647 - 1;
                OV := TRUE;
            ELSE
                CV := CV + 1;
            END_IF;
        END_IF;
    END_IF;
    IF UpEdge OR DownEdge THEN
        Q := CV >= PV;
    END_IF;
    WasCU := CU;
    WasCD := CD;
END_IF;"""
TF_COUNTER_SOURCE = f"""FUNCTION_BLOCK TF_COUNTER
VAR_INPUT
    CU : BOOL;
    CD : BOOL;
    RESET : BOOL;
    PV : DINT;
    INITIAL_ACC : DINT;
    INITIAL_DN : BOOL;
    INITIAL_OV : BOOL;
    INITIAL_UN : BOOL;
    UP_FIRST : BOOL;
END_VAR

VAR_OUTPUT
    Q : BOOL;
    CV : DINT;
    CUEnabled : BOOL;
    CDEnabled : BOOL;
    OV : BOOL;
    UN : BOOL;
END_VAR

VAR
    WasCU : BOOL := FALSE;
    WasCD : BOOL := FALSE;
    UpEdge : BOOL := FALSE;
    DownEdge : BOOL := FALSE;
    Initialized : BOOL := FALSE;
END_VAR

{TF_COUNTER_BODY}

END_FUNCTION_BLOCK
"""


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


def shared_counter_names(program: Program) -> set[str]:
    """Return counter tags represented by exactly one canonical state group."""

    routine = program.main_routine
    if routine is None:
        return set()
    names: set[str] = set()
    index = 0
    while index < len(routine.ladder_rungs):
        group = match_counter_group(program, index)
        if group is None:
            index += 1
            continue
        if group.counter_name in names:
            raise OpenPLCNativeUnsupportedError(
                f"COUNTER {group.counter_name!r} has multiple canonical groups"
            )
        names.add(group.counter_name)
        index += group.source_rung_count
    return names


def lower_counter_group(
    program_name: str,
    index: int,
    group: OpenPLCCounterGroup,
    *,
    accumulator_name: str | None = None,
    status_names: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Lower one canonical CTU/CTD group to a shared `TF_COUNTER` owner."""

    rung_id = f"rung_{program_name}_{stable_uuid(f'{program_name}/rung/{index}')}"
    left_id = f"left-rail-{rung_id}"
    contact_id = f"CONTACT_{stable_uuid(f'{rung_id}/contact/0')}"
    block_id = f"BLOCK_{stable_uuid(f'{rung_id}/shared-counter')}"
    coil_id = f"COIL_{stable_uuid(f'{rung_id}/coil')}"
    right_id = f"right-rail-{rung_id}"
    primary_handle = "CU" if group.count_up_name is not None else "CD"
    primary_name = group.count_up_name or group.count_down_name
    assert primary_name is not None
    inputs = _shared_counter_inputs(group, primary_handle)
    nodes: list[dict[str, object]] = [
        rail_node(left_id, left=True),
        instruction_node(contact_id, "contact", primary_name, 68, 38),
    ]
    edges = [
        edge(left_id, "left-rail", contact_id, "input"),
        edge(contact_id, "output", block_id, primary_handle),
    ]
    for offset, (handle, name, data_type) in enumerate(inputs):
        node_id = f"VARIABLE_{stable_uuid(f'{rung_id}/counter/{handle}')}"
        nodes.append(
            block_variable_node(
                node_id, block_id, handle, name, data_type, "input", 147,
                74 + offset * 40,
            )
        )
        edges.append(edge(node_id, "output", block_id, handle))
    resolved_status_names = dict(status_names or {})
    nodes.append(
        _shared_counter_block_node(
            block_id, group, accumulator_name, resolved_status_names
        )
    )
    if accumulator_name:
        accumulator_id = f"VARIABLE_{stable_uuid(f'{rung_id}/counter/CV')}"
        nodes.append(
            block_variable_node(
                accumulator_id, block_id, "CV", accumulator_name, "DINT",
                "output", 487, 74,
            )
        )
        edges.append(edge(block_id, "CV", accumulator_id, "input"))
    for offset, member in enumerate(("OV", "UN"), start=1):
        status_name = resolved_status_names.get(member)
        if status_name is None:
            continue
        status_id = f"VARIABLE_{stable_uuid(f'{rung_id}/counter/{member}')}"
        nodes.append(
            block_variable_node(
                status_id, block_id, member, status_name, "BOOL", "output",
                487, 74 + offset * 40,
            )
        )
        edges.append(edge(block_id, member, status_id, "input"))
    nodes.extend(
        [
            instruction_node(coil_id, "coil", group.output_name, 622, 38),
            rail_node(right_id, left=False, x=760),
        ]
    )
    edges.extend(
        [
            edge(block_id, "Q", coil_id, "input"),
            edge(coil_id, "output", right_id, "right-rail"),
        ]
    )
    return {
        "id": rung_id,
        "comment": group.comment,
        "defaultBounds": [300, 100],
        "reactFlowViewport": [763, 454],
        "nodes": nodes,
        "edges": edges,
    }


def _shared_counter_inputs(
    group: OpenPLCCounterGroup,
    primary_handle: str,
) -> list[tuple[str, str, str]]:
    values = {
        "CU": group.count_up_name or "FALSE",
        "CD": group.count_down_name or "FALSE",
        "RESET": group.reset_name,
        "PV": str(group.preset),
        "INITIAL_ACC": str(group.initial_accumulator),
        "INITIAL_DN": str(group.initial_done).upper(),
        "INITIAL_OV": str(group.initial_overflow).upper(),
        "INITIAL_UN": str(group.initial_underflow).upper(),
        "UP_FIRST": str(
            group.order in {CounterOrder.UP_ONLY, CounterOrder.UP_THEN_DOWN}
        ).upper(),
    }
    bool_handles = {
        "CU", "CD", "RESET", "INITIAL_DN", "INITIAL_OV", "INITIAL_UN",
        "UP_FIRST",
    }
    return [
        (handle, value, "BOOL" if handle in bool_handles else "DINT")
        for handle, value in values.items()
        if handle != primary_handle
    ]


def _shared_counter_block_node(
    identifier: str,
    group: OpenPLCCounterGroup,
    accumulator_name: str | None,
    status_names: Mapping[str, str],
) -> dict[str, object]:
    input_names = [
        "CU", "CD", "RESET", "PV", "INITIAL_ACC", "INITIAL_DN",
        "INITIAL_OV", "INITIAL_UN", "UP_FIRST",
    ]
    output_names = ["Q", "CV", "CUEnabled", "CDEnabled", "OV", "UN"]
    handles = [
        *[
            block_connector(name, 257, 50 + i * 40, "left", "target", 0, 36 + i * 40)
            for i, name in enumerate(input_names)
        ],
        *[
            block_connector(name, 457, 50 + i * 40, "right", "source", 200, 36 + i * 40)
            for i, name in enumerate(output_names)
        ],
    ]
    variables = [
        *[
            block_variable(
                name, "input", "DINT" if name in {"PV", "INITIAL_ACC"} else "BOOL"
            )
            for name in input_names
        ],
        *[
            block_variable(name, "output", "DINT" if name == "CV" else "BOOL")
            for name in output_names
        ],
    ]
    primary_handle = "CU" if group.count_up_name is not None else "CD"
    connected = [
        {
            "handleId": handle,
            "type": "input",
            "variable": native_variable(value, data_type),
        }
        for handle, value, data_type in _shared_counter_inputs(group, primary_handle)
    ]
    if accumulator_name:
        connected.append(
            {
                "handleId": "CV",
                "type": "output",
                "variable": native_variable(accumulator_name, "DINT"),
            }
        )
    connected.extend(
        {
            "handleId": member,
            "type": "output",
            "variable": native_variable(name, "BOOL"),
        }
        for member, name in status_names.items()
    )
    return {
        "id": identifier,
        "type": "block",
        "position": {"x": 257, "y": 14},
        "height": 380,
        "width": 200,
        "measured": {"width": 200, "height": 380},
        "draggable": True,
        "selectable": True,
        "data": {
            "handles": handles,
            "inputHandles": handles[: len(input_names)],
            "outputHandles": handles[len(input_names) :],
            "inputConnector": handles[0],
            "outputConnector": handles[len(input_names)],
            "numericId": numeric_id(identifier),
            "variant": {
                "name": "TF_COUNTER",
                "type": "function-block",
                "language": "st",
                "variables": variables,
                "body": TF_COUNTER_BODY,
                "documentation": "TwinForge shared Rockwell counter state",
            },
            "variable": {
                "name": group.counter_name,
                "type": {"definition": "derived", "value": "TF_COUNTER"},
                "class": "local",
                "location": "",
                "documentation": "",
                "debug": False,
            },
            "executionOrder": 0,
            "executionControl": False,
            "lockExecutionControl": False,
            "connectedVariables": connected,
            "draggable": True,
            "selectable": True,
            "deletable": True,
            "hasDivergence": False,
        },
    }


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
