"""Serialize native OpenPLC function-block and variable primitives."""

from __future__ import annotations

from .native_graph import numeric_id


def block_variable(
    name: str,
    variable_class: str,
    data_type: str,
) -> dict[str, object]:
    """Describe one native function-block interface variable."""

    return {
        "name": name,
        "class": variable_class,
        "type": {"definition": "base-type", "value": data_type},
    }


def block_connector(
    identifier: str,
    x: int,
    y: int,
    position: str,
    connector_type: str,
    rel_x: int,
    rel_y: int,
) -> dict[str, object]:
    """Create one evidenced native function-block connector."""

    return {
        "glbPosition": {"x": x, "y": y},
        "relPosition": {"x": rel_x, "y": rel_y},
        "id": identifier,
        "position": position,
        "type": connector_type,
        "isConnectable": False,
        "style": {"top": rel_y, position: 0},
    }


def native_variable(
    name: str,
    data_type: str,
    location: str = "",
) -> dict[str, object]:
    """Describe one local variable connected to a native graph block."""

    return {
        "name": name,
        "class": "local",
        "type": {"definition": "base-type", "value": data_type},
        "location": location,
        "initialValue": None,
        "documentation": "",
        "debug": False,
    }


def block_variable_node(
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
    """Create an evidenced input or output variable node for one block pin."""

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
            "numericId": numeric_id(identifier),
            "variable": native_variable(name, data_type.lower(), location),
            "executionOrder": 0,
            "variant": variant,
            "block": {
                "id": block_id,
                "handleId": handle_id,
                "variableType": block_variable(handle_id, variant, data_type),
            },
            "draggable": False,
            "selectable": True,
            "deletable": False,
        },
    }
