"""Serialize deterministic native OpenPLC ladder graph primitives."""

from __future__ import annotations

import hashlib
import uuid


OPENPLC_ID_NAMESPACE = uuid.UUID("1be06132-d6f7-52dc-930d-b0ad9a554449")


def stable_uuid(value: str) -> str:
    """Return the established deterministic UUID for a native graph path."""

    return str(uuid.uuid5(OPENPLC_ID_NAMESPACE, value))


def numeric_id(value: str) -> str:
    """Return the stable seven-digit identifier used by OpenPLC nodes."""

    digest = hashlib.sha256(value.encode("utf-8")).digest()
    return str(1_000_000 + int.from_bytes(digest[:4], "big") % 9_000_000)


def connector(
    *,
    identifier: str,
    x: int,
    y: int,
    rel_x: int,
    rel_y: int,
    position: str,
    connector_type: str,
) -> dict[str, object]:
    """Create an evidenced ordinary node connector."""

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


def rail_node(
    identifier: str,
    *,
    left: bool,
    x: int | None = None,
) -> dict[str, object]:
    """Create a rail node, allowing rung width to grow with its instructions."""

    resolved_x = 0 if left else (320 if x is None else x)
    rail_connector = connector(
        identifier="left-rail" if left else "right-rail",
        x=3 if left else resolved_x - 23,
        y=50,
        rel_x=3,
        rel_y=20,
        position="right" if left else "left",
        connector_type="source" if left else "target",
    )
    rail_connector["style"] = {
        "top": 20,
        "right" if left else "left": -3,
    }
    inputs = [] if left else [rail_connector]
    outputs = [rail_connector] if left else []
    data: dict[str, object] = {
        "handles": [rail_connector],
        "inputHandles": inputs,
        "outputHandles": outputs,
        "numericId": numeric_id(identifier),
        "variant": "left" if left else "right",
        "variable": {"name": ""},
        "executionOrder": 0,
        "draggable": False,
        "selectable": False,
        "deletable": False,
        "hasDivergence": False,
    }
    data["outputConnector" if left else "inputConnector"] = rail_connector
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


def instruction_node(
    identifier: str,
    node_type: str,
    variable_name: str,
    x: int,
    width: int,
    *,
    y: int = 38,
    variant: str = "default",
) -> dict[str, object]:
    """Create an evidenced Boolean contact or coil node."""

    input_connector = connector(
        identifier="input",
        x=x,
        y=50,
        rel_x=0,
        rel_y=12,
        position="left",
        connector_type="target",
    )
    output_connector = connector(
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
        "numericId": numeric_id(identifier),
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


def parallel_node(
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
    input_connector = parallel_connector("input", resolved_x, "left", "target")
    parallel_input = parallel_connector(
        parallel_input_id,
        resolved_x + 4,
        "top" if open_node else "bottom",
        "target",
    )
    output_connector = parallel_connector(
        "output-right", resolved_x + 4, "right", "source"
    )
    parallel_output = parallel_connector(
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
        "numericId": numeric_id(identifier),
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


def parallel_connector(
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


def edge(
    source: str,
    source_handle: str,
    target: str,
    target_handle: str,
) -> dict[str, str]:
    """Create one deterministic native graph edge."""

    return {
        "id": f"e_{source}_{target}__{source_handle}_{target_handle}",
        "source": source,
        "sourceHandle": source_handle,
        "target": target,
        "targetHandle": target_handle,
    }
