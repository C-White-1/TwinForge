"""Evidence-backed native OpenPLC Ladder project packaging."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from collections.abc import Mapping
import uuid

from twinforge.exporters.plcopen_operands import (
    PLCopenOperandPlan,
    PLCopenOperandPlanner,
)
from twinforge.exporters.plcopen_rll import (
    ParsedBooleanRung,
    parse_supported_rung,
    split_arguments,
)
from twinforge.exporters.plcopen_xml import milliseconds_time_literal
from twinforge.model import Controller, Program


OPENPLC_ID_NAMESPACE = uuid.UUID("1be06132-d6f7-52dc-930d-b0ad9a554449")
OPENPLC_MAIN_PROGRAM = "main"
_EVIDENCED_BOOL_LOCATION = re.compile(r"%[IQ]X\d+\.\d+")
_EVIDENCED_DINT_MEMORY_LOCATION = re.compile(r"%MD\d+")


class OpenPLCNativeUnsupportedError(ValueError):
    """Raised when source behavior exceeds the evidenced native subset."""


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
    ) -> OpenPLCNativeProjectResult:
        """Write a native OpenPLC project or reject unsupported semantics."""

        root = Path(destination)
        program, task_name, interval, priority = _select_entrypoint(controller)
        operands = PLCopenOperandPlanner().prepare(controller)
        _validate_program(controller, program, operands)
        routine = program.main_routine
        if routine is None:
            raise OpenPLCNativeUnsupportedError(
                f"program {program.name!r} has no main routine"
            )

        project = _project_document(
            project_name or controller.name or "TwinForge",
            task_name,
            interval,
            priority,
        )
        resolved_locations = dict(locations or {})
        _validate_locations(program, resolved_locations)
        elapsed_locations = dict(timer_elapsed_locations or {})
        _validate_timer_elapsed_locations(operands, elapsed_locations)
        ladder = _ladder_document(
            program,
            OPENPLC_MAIN_PROGRAM,
            resolved_locations,
            operands,
            elapsed_locations,
        )
        device = _device_document(compile_only=compile_only)
        documents = {
            Path("project.json"): json.dumps(project, indent=2) + "\n",
            Path("devices/configuration.json"): json.dumps(device, indent=2) + "\n",
            Path("devices/pin-mapping.json"): "[]\n",
            Path(f"pous/programs/{OPENPLC_MAIN_PROGRAM}.ld"): ladder,
        }
        written: list[Path] = []
        for relative, text in documents.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
            written.append(path)
        for relative in ("pous/function-blocks", "pous/functions"):
            (root / relative).mkdir(parents=True, exist_ok=True)
        return OpenPLCNativeProjectResult(
            root,
            tuple(written),
            source_program_name=program.name,
        )


def _select_entrypoint(
    controller: Controller,
) -> tuple[Program, str, str, int]:
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


def _validate_program(
    controller: Controller,
    program: Program,
    operands: PLCopenOperandPlan,
) -> None:
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
        if (tag.data_type or "").casefold() not in {"bool", "timer"}
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
        if _timer_pair(program, rung_index, operands) is not None:
            rung_index += 2
            continue
        serial_supported = (
            not parsed.branches
            and bool(parsed.tail_conditions)
            and all(opcode == "XIC" for opcode, _ in parsed.tail_conditions)
        )
        parallel_supported = (
            len(parsed.branches) == 2
            and all(
                len(branch) == 1 and branch[0][0] == "XIC" for branch in parsed.branches
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
                f"rung {rung.number!r} is outside the evidenced serial/parallel-XIC-to-OTE subset"
            )
        rung_index += 1


def _validate_locations(program: Program, locations: Mapping[str, str]) -> None:
    unknown = sorted(set(locations).difference(program.tags))
    if unknown:
        raise OpenPLCNativeUnsupportedError(
            "locations reference unknown local variables: " + ", ".join(unknown)
        )
    unsupported = [
        f"{name}={location}"
        for name, location in locations.items()
        if _EVIDENCED_BOOL_LOCATION.fullmatch(location) is None
    ]
    if unsupported:
        raise OpenPLCNativeUnsupportedError(
            "only evidenced %IX/%QX byte.bit BOOL locations are supported: "
            + ", ".join(unsupported)
        )


def _validate_timer_elapsed_locations(
    operands: PLCopenOperandPlan,
    locations: Mapping[str, str],
) -> None:
    unknown = sorted(set(locations).difference(operands.timers))
    if unknown:
        raise OpenPLCNativeUnsupportedError(
            "elapsed locations reference unknown TIMER tags: " + ", ".join(unknown)
        )
    unsupported = [
        f"{name}={location}"
        for name, location in locations.items()
        if _EVIDENCED_DINT_MEMORY_LOCATION.fullmatch(location) is None
    ]
    if unsupported:
        raise OpenPLCNativeUnsupportedError(
            "timer elapsed telemetry requires evidenced %MD DINT locations: "
            + ", ".join(unsupported)
        )


def _project_document(
    project_name: str,
    task_name: str,
    interval: str,
    priority: int,
) -> dict[str, object]:
    return {
        "meta": {"name": project_name, "type": "plc-project"},
        "data": {
            "dataTypes": [],
            "pous": [],
            "configuration": {
                "resource": {
                    "tasks": [
                        {
                            "name": task_name,
                            "triggering": "Cyclic",
                            "interval": interval,
                            "priority": priority,
                        }
                    ],
                    "instances": [
                        {
                            "name": "instance0",
                            "task": task_name,
                            "program": OPENPLC_MAIN_PROGRAM,
                        }
                    ],
                    "globalVariables": [],
                }
            },
            "deletedPous": [],
        },
    }


def _device_document(*, compile_only: bool) -> dict[str, object]:
    return {
        "deviceBoard": "OpenPLC Runtime v3",
        "communicationPort": "",
        "runtimeIpAddress": "",
        "compileOnly": compile_only,
        "communicationConfiguration": {
            "modbusRTU": {
                "rtuInterface": "Serial",
                "rtuBaudRate": "115200",
                "rtuSlaveId": None,
                "rtuRS485ENPin": None,
            },
            "modbusTCP": {
                "tcpInterface": "Ethernet",
                "tcpMacAddress": "DE:AD:BE:EF:DE:AD",
                "tcpStaticHostConfiguration": {
                    "ipAddress": "",
                    "dns": "",
                    "gateway": "",
                    "subnet": "",
                },
            },
            "communicationPreferences": {
                "enabledRTU": False,
                "enabledTCP": False,
                "enabledDHCP": True,
            },
        },
    }


def _ladder_document(
    program: Program,
    native_name: str,
    locations: Mapping[str, str],
    operands: PLCopenOperandPlan,
    elapsed_locations: Mapping[str, str],
) -> str:
    declaration_lines = [
        _variable_declaration(tag.name, tag.data_type, locations.get(tag.name))
        for tag in program.iter_tags()
    ]
    for timer_name, location in elapsed_locations.items():
        declaration_lines.extend(
            [
                f"\t{timer_name}_ET : TIME;",
                f"\t{timer_name}_ElapsedSeconds : DINT AT {location};",
            ]
        )
    declarations = "\n".join(declaration_lines)
    header = f"PROGRAM {native_name}\nVAR\n{declarations}\nEND_VAR\n\n"
    routine = program.main_routine
    assert routine is not None
    rungs: list[dict[str, object]] = []
    source_index = 0
    while source_index < len(routine.ladder_rungs):
        pair = _timer_pair(program, source_index, operands)
        if pair is not None:
            elapsed_location = elapsed_locations.get(pair[1])
            elapsed_name = f"{pair[1]}_ET" if elapsed_location else None
            rungs.append(
                _native_timer_rung(
                    native_name,
                    len(rungs),
                    *pair,
                    elapsed_name=elapsed_name,
                )
            )
            if elapsed_location:
                rungs.append(
                    _native_elapsed_conversion_rung(
                        native_name,
                        len(rungs),
                        pair[1],
                        elapsed_location,
                    )
                )
            source_index += 2
            continue
        rung = routine.ladder_rungs[source_index]
        rungs.append(
            _native_rung(native_name, len(rungs), rung.text or "", rung.comment or "")
        )
        source_index += 1
    body = json.dumps({"name": native_name, "rungs": rungs}, indent=2)
    return f"{header}{body}\nEND_PROGRAM\n"


def _variable_declaration(
    name: str,
    data_type: str | None,
    location: str | None,
) -> str:
    if (data_type or "").upper() == "TIMER":
        return f"\t{name} : TON;"
    if location is None:
        return f"\t{name} : BOOL;"
    return f"\t{name} : bool AT {location};"


def _timer_pair(
    program: Program,
    index: int,
    operands: PLCopenOperandPlan,
) -> tuple[str, str, int, str, str] | None:
    """Recognize one canonical TON rung followed by its DN output rung."""

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
        or timer_parsed.outputs[0][0] != "TON"
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
    return (
        timer_parsed.tail_conditions[0][1],
        timer_name,
        timer.preset_ms,
        done_parsed.outputs[0][1],
        timer_rung.comment or done_rung.comment or "",
    )


def _native_timer_rung(
    program_name: str,
    index: int,
    enable_name: str,
    timer_name: str,
    preset_ms: int,
    output_name: str,
    comment: str,
    *,
    elapsed_name: str | None = None,
) -> dict[str, object]:
    """Lower a canonical Rockwell TON/DN pair to one IEC TON network."""

    rung_id = f"rung_{program_name}_{_stable_uuid(f'{program_name}/rung/{index}')}"
    left_id = f"left-rail-{rung_id}"
    contact_id = f"CONTACT_{_stable_uuid(f'{rung_id}/contact/0')}"
    block_id = f"BLOCK_{_stable_uuid(f'{rung_id}/timer')}"
    preset_id = f"VARIABLE_{_stable_uuid(f'{rung_id}/timer/PT')}"
    elapsed_id = f"VARIABLE_{_stable_uuid(f'{rung_id}/timer/ET')}"
    coil_id = f"COIL_{_stable_uuid(f'{rung_id}/coil')}"
    right_id = f"right-rail-{rung_id}"
    coil_x = 488 if elapsed_name else 353
    right_x = 626 if elapsed_name else 491
    nodes = [
        _rail_node(left_id, left=True),
        _instruction_node(contact_id, "contact", enable_name, 68, 24),
        _timer_preset_node(preset_id, block_id, preset_ms),
        _timer_block_node(block_id, timer_name, preset_ms),
    ]
    if elapsed_name:
        nodes.append(
            _block_variable_node(
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
            _instruction_node(coil_id, "coil", output_name, coil_x, 28),
            _rail_node(right_id, left=False, x=right_x),
        ]
    )
    edges = [
        _edge(left_id, "left-rail", contact_id, "input"),
        _edge(contact_id, "output", block_id, "IN"),
        _edge(preset_id, "output", block_id, "PT"),
        _edge(block_id, "Q", coil_id, "input"),
        _edge(coil_id, "output", right_id, "right-rail"),
    ]
    if elapsed_name:
        edges.append(_edge(block_id, "ET", elapsed_id, "input"))
    return {
        "id": rung_id,
        "comment": comment,
        "defaultBounds": [300, 100],
        "reactFlowViewport": [629 if elapsed_name else 491, 134],
        "nodes": nodes,
        "edges": edges,
    }


def _timer_block_node(
    identifier: str,
    timer_name: str,
    preset_ms: int,
) -> dict[str, object]:
    """Create the native IEC TON block metadata required by OpenPLC Editor."""

    handles = [
        _block_connector("IN", 257, 50, "left", "target", 0, 36),
        _block_connector("PT", 257, 90, "left", "target", 0, 76),
        _block_connector("Q", 323, 50, "right", "source", 66, 36),
        _block_connector("ET", 323, 90, "right", "source", 66, 76),
    ]
    variables = [
        _block_variable("IN", "input", "BOOL"),
        _block_variable("PT", "input", "TIME"),
        _block_variable("Q", "output", "BOOL"),
        _block_variable("ET", "output", "TIME"),
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
            "numericId": _numeric_id(identifier),
            "variant": {
                "name": "TON",
                "type": "function-block",
                "language": "st",
                "variables": variables,
                "documentation": "IEC on-delay timer",
            },
            "variable": {
                "name": timer_name,
                "type": {"definition": "derived", "value": "TON"},
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


def _block_variable(
    name: str, variable_class: str, data_type: str
) -> dict[str, object]:
    return {
        "name": name,
        "class": variable_class,
        "type": {"definition": "base-type", "value": data_type},
    }


def _block_connector(
    identifier: str,
    x: int,
    y: int,
    position: str,
    connector_type: str,
    rel_x: int,
    rel_y: int,
) -> dict[str, object]:
    return {
        "glbPosition": {"x": x, "y": y},
        "relPosition": {"x": rel_x, "y": rel_y},
        "id": identifier,
        "position": position,
        "type": connector_type,
        "isConnectable": False,
        "style": {"top": rel_y, position: 0},
    }


def _timer_preset_node(
    identifier: str, block_id: str, preset_ms: int
) -> dict[str, object]:
    literal = milliseconds_time_literal(preset_ms)
    connector = {
        "glbPosition": {"x": 227, "y": 90},
        "relPosition": {"x": 80, "y": 16},
        "id": "output",
        "position": "right",
        "isConnectable": False,
        "type": "source",
    }
    return {
        "id": identifier,
        "type": "variable",
        "position": {"x": 147, "y": 74},
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
            "numericId": _numeric_id(identifier),
            "variable": {"name": literal},
            "executionOrder": 0,
            "variant": "input",
            "block": {
                "id": block_id,
                "handleId": "PT",
                "variableType": _block_variable("PT", "input", "TIME"),
            },
            "draggable": False,
            "selectable": True,
            "deletable": False,
        },
    }


def _native_elapsed_conversion_rung(
    program_name: str,
    index: int,
    timer_name: str,
    location: str,
) -> dict[str, object]:
    """Create the verified TIME_TO_DINT telemetry network for one timer."""

    rung_id = f"rung_{program_name}_{_stable_uuid(f'{program_name}/rung/{index}')}"
    left_id = f"left-rail-{rung_id}"
    block_id = f"BLOCK_{_stable_uuid(f'{rung_id}/TIME_TO_DINT')}"
    input_id = f"VARIABLE_{_stable_uuid(f'{rung_id}/IN')}"
    output_id = f"VARIABLE_{_stable_uuid(f'{rung_id}/OUT')}"
    right_id = f"right-rail-{rung_id}"
    input_name = f"{timer_name}_ET"
    output_name = f"{timer_name}_ElapsedSeconds"
    return {
        "id": rung_id,
        "comment": f"Expose {timer_name}.ET as whole elapsed seconds at {location}.",
        "defaultBounds": [300, 100],
        "reactFlowViewport": [550, 134],
        "nodes": [
            _rail_node(left_id, left=True),
            _block_variable_node(
                input_id, block_id, "IN", input_name, "TIME", "input", 33, 74
            ),
            _conversion_block_node(block_id, input_name, output_name, location),
            _block_variable_node(
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
            _rail_node(right_id, left=False, x=547),
        ],
        "edges": [
            _edge(left_id, "left-rail", block_id, "EN"),
            _edge(block_id, "ENO", right_id, "right-rail"),
            _edge(input_id, "output", block_id, "IN"),
            _edge(block_id, "OUT", output_id, "input"),
        ],
    }


def _conversion_block_node(
    identifier: str,
    input_name: str,
    output_name: str,
    location: str,
) -> dict[str, object]:
    handles = [
        _block_connector("EN", 143, 50, "left", "target", 0, 36),
        _block_connector("IN", 143, 90, "left", "target", 0, 76),
        _block_connector("ENO", 287, 50, "right", "source", 144, 36),
        _block_connector("OUT", 287, 90, "right", "source", 144, 76),
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
            "numericId": _numeric_id(identifier),
            "variant": {
                "name": "TIME_TO_DINT",
                "type": "function",
                "language": "st",
                "variables": [
                    _block_variable("EN", "input", "BOOL"),
                    _block_variable("ENO", "output", "BOOL"),
                    _block_variable("OUT", "output", "DINT"),
                    _block_variable("IN", "input", "TIME"),
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
                    "variable": _native_variable(input_name, "time"),
                },
                {
                    "handleId": "OUT",
                    "type": "output",
                    "variable": _native_variable(output_name, "dint", location),
                },
            ],
            "draggable": True,
            "selectable": True,
            "deletable": True,
            "hasDivergence": False,
        },
    }


def _native_variable(
    name: str, data_type: str, location: str = ""
) -> dict[str, object]:
    return {
        "name": name,
        "class": "local",
        "type": {"definition": "base-type", "value": data_type},
        "location": location,
        "initialValue": None,
        "documentation": "",
        "debug": False,
    }


def _block_variable_node(
    identifier: str,
    block_id: str,
    handle_id: str,
    name: str,
    data_type: str,
    variant: str,
    x: int,
    y: int,
    *,
    location: str = "",
) -> dict[str, object]:
    is_input = variant == "input"
    connector_id = "output" if is_input else "input"
    connector = {
        "glbPosition": {"x": x + (80 if is_input else 0), "y": y + 16},
        "relPosition": {"x": 80 if is_input else 0, "y": 16},
        "id": connector_id,
        "position": "right" if is_input else "left",
        "isConnectable": False,
        "type": "source" if is_input else "target",
    }
    return {
        "id": identifier,
        "type": "variable",
        "position": {"x": x, "y": y},
        "height": 32,
        "width": 80,
        "measured": {"width": 80, "height": 32},
        "draggable": False,
        "selectable": True,
        "data": {
            "handles": [connector],
            "inputHandles": [] if is_input else [connector],
            "outputHandles": [connector] if is_input else [],
            ("outputConnector" if is_input else "inputConnector"): connector,
            "numericId": _numeric_id(identifier),
            "variable": _native_variable(name, data_type.lower(), location),
            "executionOrder": 0,
            "variant": variant,
            "block": {
                "id": block_id,
                "handleId": handle_id,
                "variableType": _block_variable(handle_id, variant, data_type),
            },
            "draggable": False,
            "selectable": True,
            "deletable": False,
        },
    }


def _native_rung(
    program_name: str,
    index: int,
    text: str,
    comment: str,
) -> dict[str, object]:
    parsed = parse_supported_rung(text)
    assert parsed is not None
    if parsed.branches:
        return _native_parallel_rung(program_name, index, parsed, comment)
    contact_names = [operand for _, operand in parsed.tail_conditions]
    coil_name = parsed.outputs[0][1]
    rung_uuid = _stable_uuid(f"{program_name}/rung/{index}")
    rung_id = f"rung_{program_name}_{rung_uuid}"
    left_id = f"left-rail-{rung_id}"
    contact_ids = [
        f"CONTACT_{_stable_uuid(f'{rung_id}/contact/{contact_index}')}"
        for contact_index in range(len(contact_names))
    ]
    coil_id = f"COIL_{_stable_uuid(f'{rung_id}/coil')}"
    right_id = f"right-rail-{rung_id}"
    contact_nodes = [
        _instruction_node(
            identifier,
            "contact",
            name,
            68 + contact_index * 114,
            24,
        )
        for contact_index, (identifier, name) in enumerate(
            zip(contact_ids, contact_names, strict=True)
        )
    ]
    coil_x = 68 + len(contact_ids) * 114
    instruction_ids = [*contact_ids, coil_id]
    edges = [
        _edge(left_id, "left-rail", instruction_ids[0], "input"),
        *[
            _edge(source, "output", target, "input")
            for source, target in zip(
                instruction_ids,
                instruction_ids[1:],
                strict=False,
            )
        ],
        _edge(coil_id, "output", right_id, "right-rail"),
    ]
    return {
        "id": rung_id,
        "comment": comment,
        "defaultBounds": [300, 100],
        "reactFlowViewport": [323, 120],
        "nodes": [
            _rail_node(left_id, left=True),
            *contact_nodes,
            _instruction_node(coil_id, "coil", coil_name, coil_x, 28),
            _rail_node(right_id, left=False, x=coil_x + 138),
        ],
        "edges": edges,
    }


def _native_parallel_rung(
    program_name: str,
    index: int,
    parsed: ParsedBooleanRung,
    comment: str,
) -> dict[str, object]:
    """Create the evidenced two-path OR graph used by native OpenPLC Ladder."""

    # Validation guarantees the compact two-single-contact branch shape.
    branches = parsed.branches
    outputs = parsed.outputs
    names = [branch[0][1] for branch in branches]
    coil_name = outputs[0][1]
    has_tail_contact = bool(parsed.tail_conditions)
    rung_id = f"rung_{program_name}_{_stable_uuid(f'{program_name}/rung/{index}')}"
    left_id = f"left-rail-{rung_id}"
    open_id = f"PARALLEL_OPEN_{_stable_uuid(f'{rung_id}/parallel/open')}"
    close_id = f"PARALLEL_CLOSE_{_stable_uuid(f'{rung_id}/parallel/close')}"
    contact_ids = [
        f"CONTACT_{_stable_uuid(f'{rung_id}/branch/{branch_index}/contact')}"
        for branch_index in range(2)
    ]
    stop_id = f"CONTACT_{_stable_uuid(f'{rung_id}/tail/stop')}"
    coil_id = f"COIL_{_stable_uuid(f'{rung_id}/coil')}"
    right_id = f"right-rail-{rung_id}"
    open_x = 137 if has_tail_contact else 23
    branch_x = 186 if has_tail_contact else 72
    close_x = 255 if has_tail_contact else 141
    coil_x = 304 if has_tail_contact else 190
    right_x = 442 if has_tail_contact else 328
    nodes = [_rail_node(left_id, left=True)]
    if has_tail_contact:
        tail_opcode, tail_operand = parsed.tail_conditions[0]
        nodes.append(
            _instruction_node(
                stop_id,
                "contact",
                tail_operand,
                68,
                24,
                variant="negated" if tail_opcode == "XIO" else "default",
            )
        )
    nodes.extend(
        [
            _parallel_node(
                open_id,
                counterpart_id=close_id,
                open_node=True,
                x=open_x,
            ),
            _instruction_node(contact_ids[0], "contact", names[0], branch_x, 24),
            _instruction_node(contact_ids[1], "contact", names[1], branch_x, 24, y=130),
            _parallel_node(
                close_id,
                counterpart_id=open_id,
                open_node=False,
                x=close_x,
            ),
            _instruction_node(coil_id, "coil", coil_name, coil_x, 28),
            _rail_node(right_id, left=False, x=right_x),
        ]
    )
    first_id = stop_id if has_tail_contact else open_id
    edges = [_edge(left_id, "left-rail", first_id, "input")]
    if has_tail_contact:
        edges.append(_edge(stop_id, "output", open_id, "input"))
    edges.extend(
        [
            _edge(open_id, "output-right", contact_ids[0], "input"),
            _edge(contact_ids[0], "output", close_id, "input"),
            _edge(open_id, "output-down", contact_ids[1], "input"),
            _edge(contact_ids[1], "output", close_id, "input-down"),
            _edge(close_id, "output-right", coil_id, "input"),
            _edge(coil_id, "output", right_id, "right-rail"),
        ]
    )
    return {
        "id": rung_id,
        "comment": comment,
        "defaultBounds": [300, 100],
        "reactFlowViewport": [331, 212],
        "nodes": nodes,
        "edges": edges,
    }


def _stable_uuid(value: str) -> str:
    return str(uuid.uuid5(OPENPLC_ID_NAMESPACE, value))


def _numeric_id(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    return str(1_000_000 + int.from_bytes(digest[:4], "big") % 9_000_000)


def _connector(
    *,
    identifier: str,
    x: int,
    y: int,
    rel_x: int,
    rel_y: int,
    position: str,
    connector_type: str,
) -> dict[str, object]:
    style = {position: -3}
    return {
        "glbPosition": {"x": x, "y": y},
        "relPosition": {"x": rel_x, "y": rel_y},
        "id": identifier,
        "position": position,
        "isConnectable": False,
        "type": connector_type,
        "style": style,
    }


def _rail_node(
    identifier: str,
    *,
    left: bool,
    x: int | None = None,
) -> dict[str, object]:
    """Create a rail node, allowing rung width to grow with its instructions."""

    resolved_x = 0 if left else (320 if x is None else x)
    connector = _connector(
        identifier="left-rail" if left else "right-rail",
        x=3 if left else resolved_x - 23,
        y=50,
        rel_x=3,
        rel_y=20,
        position="right" if left else "left",
        connector_type="source" if left else "target",
    )
    connector["style"] = {
        "top": 20,
        "right" if left else "left": -3,
    }
    inputs = [] if left else [connector]
    outputs = [connector] if left else []
    data: dict[str, object] = {
        "handles": [connector],
        "inputHandles": inputs,
        "outputHandles": outputs,
        "numericId": _numeric_id(identifier),
        "variant": "left" if left else "right",
        "variable": {"name": ""},
        "executionOrder": 0,
        "draggable": False,
        "selectable": False,
        "deletable": False,
        "hasDivergence": False,
    }
    data["outputConnector" if left else "inputConnector"] = connector
    return {
        "id": identifier,
        "type": "powerRail",
        "position": {"x": resolved_x, "y": 30},
        "height": 40,
        "width": 3,
        "measured": {"width": 3, "height": 40},
        "draggable": False,
        "selectable": False,
        "data": data,
    }


def _instruction_node(
    identifier: str,
    node_type: str,
    variable_name: str,
    x: int,
    width: int,
    *,
    y: int = 38,
    variant: str = "default",
) -> dict[str, object]:
    input_connector = _connector(
        identifier="input",
        x=x,
        y=50,
        rel_x=0,
        rel_y=12,
        position="left",
        connector_type="target",
    )
    output_connector = _connector(
        identifier="output",
        x=x + width,
        y=50,
        rel_x=width,
        rel_y=12,
        position="right",
        connector_type="source",
    )
    data: dict[str, object] = {
        "handles": [input_connector, output_connector],
        "variant": variant,
        "inputHandles": [input_connector],
        "outputHandles": [output_connector],
        "inputConnector": input_connector,
        "outputConnector": output_connector,
        "numericId": _numeric_id(identifier),
        "variable": {
            "name": variable_name,
            "class": "local",
            "type": {"definition": "base-type", "value": "bool"},
            "location": "",
            "initialValue": None,
            "documentation": "",
            "debug": False,
        },
        "executionOrder": 0,
        "draggable": True,
        "selectable": True,
        "deletable": True,
    }
    if node_type == "contact":
        data["hasDivergence"] = False
    return {
        "id": identifier,
        "type": node_type,
        "position": {"x": x, "y": y},
        "height": 24,
        "width": width,
        "measured": {"width": width, "height": 24},
        "draggable": node_type == "contact",
        "selectable": True,
        "data": data,
    }


def _parallel_node(
    identifier: str,
    *,
    counterpart_id: str,
    open_node: bool,
    x: int | None = None,
) -> dict[str, object]:
    """Create one evidenced branch divergence or convergence node."""

    resolved_x = (23 if open_node else 141) if x is None else x
    parallel_input_id = "input-top" if open_node else "input-down"
    parallel_output_id = "output-down" if open_node else "output-top"
    input_connector = _parallel_connector("input", resolved_x, "left", "target")
    parallel_input = _parallel_connector(
        parallel_input_id,
        resolved_x + 4,
        "top" if open_node else "bottom",
        "target",
    )
    output_connector = _parallel_connector(
        "output-right", resolved_x + 4, "right", "source"
    )
    parallel_output = _parallel_connector(
        parallel_output_id,
        resolved_x + 4,
        "bottom" if open_node else "top",
        "source",
    )
    data: dict[str, object] = {
        "handles": [
            input_connector,
            parallel_input,
            output_connector,
            parallel_output,
        ],
        "inputHandles": [input_connector, parallel_input],
        "outputHandles": [output_connector, parallel_output],
        "inputConnector": input_connector,
        "outputConnector": output_connector,
        "numericId": _numeric_id(identifier),
        "parallelInputConnector": parallel_input,
        "parallelOutputConnector": parallel_output,
        "type": "open" if open_node else "close",
        "variable": {"name": ""},
        "executionOrder": 0,
        "draggable": False,
        "selectable": False,
        "deletable": False,
        "hasDivergence": False,
    }
    data["parallelCloseReference" if open_node else "parallelOpenReference"] = (
        counterpart_id
    )
    return {
        "id": identifier,
        "type": "parallel",
        "position": {"x": resolved_x, "y": 49},
        "height": 2,
        "width": 4,
        "measured": {"width": 4, "height": 2},
        "draggable": False,
        "selectable": False,
        "data": data,
    }


def _parallel_connector(
    identifier: str,
    x: int,
    position: str,
    connector_type: str,
) -> dict[str, object]:
    """Create a connector using the compact native parallel-node geometry."""

    vertical = position in {"top", "bottom"}
    style: dict[str, object] = {position: 1 if vertical else 3}
    if not vertical:
        style["visibility"] = "hidden"
    return {
        "glbPosition": {"x": x, "y": 50},
        "relPosition": {
            "x": 2 if vertical else (0 if position == "left" else 4),
            "y": 0 if position == "top" else (2 if position == "bottom" else 1),
        },
        "id": identifier,
        "position": position,
        "type": connector_type,
        "isConnectable": False,
        "style": style,
    }


def _edge(
    source: str,
    source_handle: str,
    target: str,
    target_handle: str,
) -> dict[str, str]:
    return {
        "id": f"e_{source}_{target}__{source_handle}_{target_handle}",
        "source": source,
        "sourceHandle": source_handle,
        "target": target,
        "targetHandle": target_handle,
    }
