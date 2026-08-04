"""Recognize canonical Rockwell timer groups for native OpenPLC lowering."""

from __future__ import annotations

from dataclasses import dataclass

from twinforge.exporters.plcopen_operands import PLCopenOperandPlan
from twinforge.exporters.plcopen_rll import parse_supported_rung, split_arguments
from twinforge.exporters.plcopen_xml import milliseconds_time_literal
from twinforge.model import Program

from .native_blocks import (
    block_connector,
    block_variable,
    block_variable_node,
    native_variable,
)
from .native_declarations import TF_RTO_BODY
from .native_errors import OpenPLCNativeUnsupportedError
from .native_graph import edge, instruction_node, numeric_id, rail_node, stable_uuid


@dataclass(frozen=True)
class NativeTimerGroup:
    """One canonical timer, done-output, and optional reset source group."""

    instruction: str
    enable_name: str
    timer_name: str
    preset_ms: int
    output_name: str
    comment: str
    reset_name: str | None = None
    source_rung_count: int = 2


def timer_instruction_types(
    program: Program,
    operands: PLCopenOperandPlan,
) -> dict[str, str]:
    """Resolve native timer instance types from evidenced source rungs."""

    routine = program.main_routine
    if routine is None:
        return {}
    resolved: dict[str, str] = {}
    index = 0
    while index < len(routine.ladder_rungs):
        group = match_timer_group(program, index, operands)
        if group is None:
            index += 1
            continue
        prior = resolved.get(group.timer_name)
        if prior is not None and prior != group.instruction:
            raise OpenPLCNativeUnsupportedError(
                f"timer {group.timer_name!r} is used by both {prior} and "
                f"{group.instruction}"
            )
        resolved[group.timer_name] = group.instruction
        index += group.source_rung_count
    return resolved


def match_timer_group(
    program: Program,
    index: int,
    operands: PLCopenOperandPlan,
) -> NativeTimerGroup | None:
    """Recognize canonical TON/TOF or RTO/DN/RES source groups."""

    routine = program.main_routine
    if routine is None or index + 1 >= len(routine.ladder_rungs):
        return None
    timer_rung = routine.ladder_rungs[index]
    done_rung = routine.ladder_rungs[index + 1]
    timer_parsed = parse_supported_rung(timer_rung.text)
    done_parsed = parse_supported_rung(done_rung.text)
    if timer_parsed is None or done_parsed is None:
        return None
    if (
        timer_parsed.branches
        or len(timer_parsed.tail_conditions) != 1
        or timer_parsed.tail_conditions[0][0] != "XIC"
        or len(timer_parsed.outputs) != 1
        or timer_parsed.outputs[0][0] not in {"TON", "TOF", "RTO"}
        or done_parsed.branches
        or len(done_parsed.tail_conditions) != 1
        or len(done_parsed.outputs) != 1
        or done_parsed.outputs[0][0] != "OTE"
    ):
        return None
    timer_arguments = split_arguments(timer_parsed.outputs[0][1])
    if len(timer_arguments) != 3:
        return None
    timer_name = timer_arguments[0]
    if done_parsed.tail_conditions[0] != ("XIC", f"{timer_name}.DN"):
        return None
    timer = operands.timers.get(timer_name)
    if timer is None:
        return None
    reset_name: str | None = None
    source_rung_count = 2
    if timer_parsed.outputs[0][0] == "RTO":
        if index + 2 >= len(routine.ladder_rungs):
            return None
        reset_parsed = parse_supported_rung(routine.ladder_rungs[index + 2].text)
        if (
            reset_parsed is None
            or reset_parsed.branches
            or len(reset_parsed.tail_conditions) != 1
            or reset_parsed.tail_conditions[0][0] != "XIC"
            or reset_parsed.outputs != (("RES", timer_name),)
        ):
            return None
        reset_name = reset_parsed.tail_conditions[0][1]
        source_rung_count = 3
    return NativeTimerGroup(
        instruction=timer_parsed.outputs[0][0],
        enable_name=timer_parsed.tail_conditions[0][1],
        timer_name=timer_name,
        preset_ms=timer.preset_ms,
        output_name=done_parsed.outputs[0][1],
        comment=timer_rung.comment or done_rung.comment or "",
        reset_name=reset_name,
        source_rung_count=source_rung_count,
    )


def lower_timer_group(
    program_name: str,
    index: int,
    group: NativeTimerGroup,
    *,
    elapsed_name: str | None = None,
) -> dict[str, object]:
    """Lower a canonical Rockwell timer group to one native timer network."""

    if group.instruction == "RTO":
        return _rto_rung(program_name, index, group)

    rung_id = f"rung_{program_name}_{stable_uuid(f'{program_name}/rung/{index}')}"
    left_id = f"left-rail-{rung_id}"
    contact_id = f"CONTACT_{stable_uuid(f'{rung_id}/contact/0')}"
    block_id = f"BLOCK_{stable_uuid(f'{rung_id}/timer')}"
    preset_id = f"VARIABLE_{stable_uuid(f'{rung_id}/timer/PT')}"
    elapsed_id = f"VARIABLE_{stable_uuid(f'{rung_id}/timer/ET')}"
    coil_id = f"COIL_{stable_uuid(f'{rung_id}/coil')}"
    right_id = f"right-rail-{rung_id}"
    coil_x = 488 if elapsed_name else 353
    right_x = 626 if elapsed_name else 491
    nodes = [
        rail_node(left_id, left=True),
        instruction_node(contact_id, "contact", group.enable_name, 68, 24),
        _timer_preset_node(preset_id, block_id, group.preset_ms),
        _timer_block_node(
            block_id,
            group.timer_name,
            group.preset_ms,
            group.instruction,
        ),
    ]
    if elapsed_name:
        nodes.append(
            block_variable_node(
                elapsed_id,
                block_id,
                "ET",
                elapsed_name,
                "TIME",
                "output",
                353,
                74,
            )
        )
    nodes.extend(
        [
            instruction_node(coil_id, "coil", group.output_name, coil_x, 28),
            rail_node(right_id, left=False, x=right_x),
        ]
    )
    edges = [
        edge(left_id, "left-rail", contact_id, "input"),
        edge(contact_id, "output", block_id, "IN"),
        edge(preset_id, "output", block_id, "PT"),
        edge(block_id, "Q", coil_id, "input"),
        edge(coil_id, "output", right_id, "right-rail"),
    ]
    if elapsed_name:
        edges.append(edge(block_id, "ET", elapsed_id, "input"))
    return {
        "id": rung_id,
        "comment": group.comment,
        "defaultBounds": [300, 100],
        "reactFlowViewport": [629 if elapsed_name else 491, 134],
        "nodes": nodes,
        "edges": edges,
    }


def elapsed_conversion_rung(
    program_name: str,
    index: int,
    timer_name: str,
    location: str,
) -> dict[str, object]:
    """Create the verified TIME_TO_DINT telemetry network for one timer."""

    rung_id = f"rung_{program_name}_{stable_uuid(f'{program_name}/rung/{index}')}"
    left_id = f"left-rail-{rung_id}"
    block_id = f"BLOCK_{stable_uuid(f'{rung_id}/TIME_TO_DINT')}"
    input_id = f"VARIABLE_{stable_uuid(f'{rung_id}/IN')}"
    output_id = f"VARIABLE_{stable_uuid(f'{rung_id}/OUT')}"
    right_id = f"right-rail-{rung_id}"
    input_name = f"{timer_name}_ET"
    output_name = f"{timer_name}_ElapsedSeconds"
    return {
        "id": rung_id,
        "comment": f"Expose {timer_name}.ET as whole elapsed seconds at {location}.",
        "defaultBounds": [300, 100],
        "reactFlowViewport": [550, 134],
        "nodes": [
            rail_node(left_id, left=True),
            block_variable_node(
                input_id, block_id, "IN", input_name, "TIME", "input", 33, 74
            ),
            _conversion_block_node(block_id, input_name, output_name, location),
            block_variable_node(
                output_id,
                block_id,
                "OUT",
                output_name,
                "DINT",
                "output",
                317,
                74,
                location=location,
            ),
            rail_node(right_id, left=False, x=547),
        ],
        "edges": [
            edge(left_id, "left-rail", block_id, "EN"),
            edge(block_id, "ENO", right_id, "right-rail"),
            edge(input_id, "output", block_id, "IN"),
            edge(block_id, "OUT", output_id, "input"),
        ],
    }


def _timer_block_node(
    identifier: str,
    timer_name: str,
    preset_ms: int,
    timer_type: str,
) -> dict[str, object]:
    """Create native IEC timer metadata required by OpenPLC Editor."""

    handles = [
        block_connector("IN", 257, 50, "left", "target", 0, 36),
        block_connector("PT", 257, 90, "left", "target", 0, 76),
        block_connector("Q", 323, 50, "right", "source", 66, 36),
        block_connector("ET", 323, 90, "right", "source", 66, 76),
    ]
    variables = [
        block_variable("IN", "input", "BOOL"),
        block_variable("PT", "input", "TIME"),
        block_variable("Q", "output", "BOOL"),
        block_variable("ET", "output", "TIME"),
    ]
    return {
        "id": identifier,
        "type": "block",
        "position": {"x": 257, "y": 14},
        "height": 100,
        "width": 66,
        "measured": {"width": 66, "height": 100},
        "draggable": True,
        "selectable": True,
        "data": {
            "handles": handles,
            "inputHandles": handles[:2],
            "outputHandles": handles[2:],
            "inputConnector": handles[0],
            "outputConnector": handles[2],
            "numericId": numeric_id(identifier),
            "variant": {
                "name": timer_type,
                "type": "function-block",
                "language": "st",
                "variables": variables,
                "documentation": (
                    "IEC on-delay timer"
                    if timer_type == "TON"
                    else "IEC off-delay timer"
                ),
            },
            "variable": {
                "name": timer_name,
                "type": {"definition": "derived", "value": timer_type},
                "class": "local",
                "location": "",
                "documentation": "",
                "debug": False,
            },
            "executionOrder": 0,
            "executionControl": False,
            "lockExecutionControl": False,
            "connectedVariables": [
                {
                    "handleId": "PT",
                    "type": "input",
                    "variable": {"name": milliseconds_time_literal(preset_ms)},
                }
            ],
            "draggable": True,
            "selectable": True,
            "deletable": True,
            "hasDivergence": False,
        },
    }


def _rto_rung(
    program_name: str,
    index: int,
    group: NativeTimerGroup,
) -> dict[str, object]:
    """Lower the evidenced RTO/DN/RES group to the TF_RTO wrapper."""

    assert group.reset_name is not None
    rung_id = f"rung_{program_name}_{stable_uuid(f'{program_name}/rung/{index}')}"
    left_id = f"left-rail-{rung_id}"
    contact_id = f"CONTACT_{stable_uuid(f'{rung_id}/contact/0')}"
    block_id = f"BLOCK_{stable_uuid(f'{rung_id}/timer')}"
    reset_id = f"VARIABLE_{stable_uuid(f'{rung_id}/timer/RESET')}"
    preset_id = f"VARIABLE_{stable_uuid(f'{rung_id}/timer/PT')}"
    coil_id = f"COIL_{stable_uuid(f'{rung_id}/coil')}"
    right_id = f"right-rail-{rung_id}"
    return {
        "id": rung_id,
        "comment": group.comment,
        "defaultBounds": [300, 100],
        "reactFlowViewport": [725, 214],
        "nodes": [
            rail_node(left_id, left=True),
            instruction_node(contact_id, "contact", group.enable_name, 68, 38),
            block_variable_node(
                reset_id,
                block_id,
                "RESET",
                group.reset_name,
                "BOOL",
                "input",
                147,
                74,
            ),
            _timer_preset_node(preset_id, block_id, group.preset_ms, y=114),
            _rto_block_node(block_id, group),
            instruction_node(coil_id, "coil", group.output_name, 584, 38),
            rail_node(right_id, left=False, x=722),
        ],
        "edges": [
            edge(left_id, "left-rail", contact_id, "input"),
            edge(contact_id, "output", block_id, "IN"),
            edge(reset_id, "output", block_id, "RESET"),
            edge(preset_id, "output", block_id, "PT"),
            edge(block_id, "Q", coil_id, "input"),
            edge(coil_id, "output", right_id, "right-rail"),
        ],
    }


def _rto_block_node(
    identifier: str,
    group: NativeTimerGroup,
) -> dict[str, object]:
    handles = [
        block_connector("IN", 257, 50, "left", "target", 0, 36),
        block_connector("RESET", 257, 90, "left", "target", 0, 76),
        block_connector("PT", 257, 130, "left", "target", 0, 116),
        block_connector("Q", 419, 50, "right", "source", 162, 36),
        block_connector("ET", 419, 90, "right", "source", 162, 76),
        block_connector("Enabled", 419, 130, "right", "source", 162, 116),
        block_connector("TT", 419, 170, "right", "source", 162, 156),
    ]
    variables = [
        block_variable("IN", "input", "BOOL"),
        block_variable("RESET", "input", "BOOL"),
        block_variable("PT", "input", "TIME"),
        block_variable("Q", "output", "BOOL"),
        block_variable("ET", "output", "TIME"),
        block_variable("Enabled", "output", "BOOL"),
        block_variable("TT", "output", "BOOL"),
    ]
    return {
        "id": identifier,
        "type": "block",
        "position": {"x": 257, "y": 14},
        "height": 180,
        "width": 162,
        "measured": {"width": 162, "height": 180},
        "draggable": True,
        "selectable": True,
        "data": {
            "handles": handles,
            "inputHandles": handles[:3],
            "outputHandles": handles[3:],
            "inputConnector": handles[0],
            "outputConnector": handles[3],
            "numericId": numeric_id(identifier),
            "variant": {
                "name": "TF_RTO",
                "type": "function-block",
                "language": "st",
                "variables": variables,
                "body": TF_RTO_BODY,
                "documentation": "TwinForge Rockwell-compatible retentive timer",
            },
            "variable": {
                "name": group.timer_name,
                "type": {"definition": "derived", "value": "TF_RTO"},
                "class": "local",
                "location": "",
                "documentation": "",
                "debug": False,
            },
            "executionOrder": 0,
            "executionControl": False,
            "lockExecutionControl": False,
            "connectedVariables": [
                {
                    "handleId": "RESET",
                    "type": "input",
                    "variable": native_variable(group.reset_name or "", "bool"),
                },
                {
                    "handleId": "PT",
                    "type": "input",
                    "variable": {
                        "name": milliseconds_time_literal(group.preset_ms)
                    },
                },
            ],
            "draggable": True,
            "selectable": True,
            "deletable": True,
            "hasDivergence": False,
        },
    }


def _timer_preset_node(
    identifier: str,
    block_id: str,
    preset_ms: int,
    *,
    y: int = 74,
) -> dict[str, object]:
    literal = milliseconds_time_literal(preset_ms)
    connector = {
        "glbPosition": {"x": 227, "y": y + 16},
        "relPosition": {"x": 80, "y": 16},
        "id": "output",
        "position": "right",
        "isConnectable": False,
        "type": "source",
    }
    return {
        "id": identifier,
        "type": "variable",
        "position": {"x": 147, "y": y},
        "height": 32,
        "width": 80,
        "measured": {"width": 80, "height": 32},
        "draggable": False,
        "selectable": True,
        "data": {
            "handles": [connector],
            "inputHandles": [],
            "outputHandles": [connector],
            "outputConnector": connector,
            "numericId": numeric_id(identifier),
            "variable": {"name": literal},
            "executionOrder": 0,
            "variant": "input",
            "block": {
                "id": block_id,
                "handleId": "PT",
                "variableType": block_variable("PT", "input", "TIME"),
            },
            "draggable": False,
            "selectable": True,
            "deletable": False,
        },
    }


def _conversion_block_node(
    identifier: str,
    input_name: str,
    output_name: str,
    location: str,
) -> dict[str, object]:
    handles = [
        block_connector("EN", 143, 50, "left", "target", 0, 36),
        block_connector("IN", 143, 90, "left", "target", 0, 76),
        block_connector("ENO", 287, 50, "right", "source", 144, 36),
        block_connector("OUT", 287, 90, "right", "source", 144, 76),
    ]
    return {
        "id": identifier,
        "type": "block",
        "position": {"x": 143, "y": 14},
        "height": 100,
        "width": 144,
        "measured": {"width": 144, "height": 100},
        "draggable": True,
        "selectable": True,
        "data": {
            "handles": handles,
            "inputHandles": handles[:2],
            "outputHandles": handles[2:],
            "inputConnector": handles[0],
            "outputConnector": handles[2],
            "numericId": numeric_id(identifier),
            "variant": {
                "name": "TIME_TO_DINT",
                "type": "function",
                "language": "st",
                "variables": [
                    block_variable("EN", "input", "BOOL"),
                    block_variable("ENO", "output", "BOOL"),
                    block_variable("OUT", "output", "DINT"),
                    block_variable("IN", "input", "TIME"),
                ],
                "body": "Data type conversion",
                "documentation": "(IN: TIME) => OUT: DINT",
                "extensible": False,
            },
            "variable": {"name": ""},
            "executionOrder": 0,
            "executionControl": True,
            "lockExecutionControl": True,
            "connectedVariables": [
                {
                    "handleId": "IN",
                    "type": "input",
                    "variable": native_variable(input_name, "time"),
                },
                {
                    "handleId": "OUT",
                    "type": "output",
                    "variable": native_variable(output_name, "dint", location),
                },
            ],
            "draggable": True,
            "selectable": True,
            "deletable": True,
            "hasDivergence": False,
        },
    }
