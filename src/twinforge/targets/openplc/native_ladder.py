"""Lower evidenced ordinary Boolean rungs to native OpenPLC graphs."""

from __future__ import annotations

from twinforge.exporters.plcopen_rll import ParsedBooleanRung, parse_supported_rung

from .native_graph import edge, instruction_node, parallel_node, rail_node, stable_uuid


def lower_boolean_rung(
    program_name: str,
    index: int,
    text: str,
    comment: str,
) -> dict[str, object]:
    """Lower one already-validated serial or parallel Boolean rung."""

    parsed = parse_supported_rung(text)
    assert parsed is not None
    if parsed.branches:
        return _parallel_rung(program_name, index, parsed, comment)
    contact_names = [operand for _, operand in parsed.tail_conditions]
    coil_name = parsed.outputs[0][1]
    rung_uuid = stable_uuid(f"{program_name}/rung/{index}")
    rung_id = f"rung_{program_name}_{rung_uuid}"
    left_id = f"left-rail-{rung_id}"
    contact_ids = [
        f"CONTACT_{stable_uuid(f'{rung_id}/contact/{contact_index}')}"
        for contact_index in range(len(contact_names))
    ]
    coil_id = f"COIL_{stable_uuid(f'{rung_id}/coil')}"
    right_id = f"right-rail-{rung_id}"
    contact_nodes = [
        instruction_node(
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
        edge(left_id, "left-rail", instruction_ids[0], "input"),
        *[
            edge(source, "output", target, "input")
            for source, target in zip(
                instruction_ids,
                instruction_ids[1:],
                strict=False,
            )
        ],
        edge(coil_id, "output", right_id, "right-rail"),
    ]
    return {
        "id": rung_id,
        "comment": comment,
        "defaultBounds": [300, 100],
        "reactFlowViewport": [323, 120],
        "nodes": [
            rail_node(left_id, left=True),
            *contact_nodes,
            instruction_node(coil_id, "coil", coil_name, coil_x, 28),
            rail_node(right_id, left=False, x=coil_x + 138),
        ],
        "edges": edges,
    }


def _parallel_rung(
    program_name: str,
    index: int,
    parsed: ParsedBooleanRung,
    comment: str,
) -> dict[str, object]:
    """Create the evidenced two-path OR graph used by native OpenPLC Ladder."""

    # Validation guarantees the compact two-single-contact branch shape.
    names = [branch[0][1] for branch in parsed.branches]
    coil_name = parsed.outputs[0][1]
    has_tail_contact = bool(parsed.tail_conditions)
    rung_id = f"rung_{program_name}_{stable_uuid(f'{program_name}/rung/{index}')}"
    left_id = f"left-rail-{rung_id}"
    open_id = f"PARALLEL_OPEN_{stable_uuid(f'{rung_id}/parallel/open')}"
    close_id = f"PARALLEL_CLOSE_{stable_uuid(f'{rung_id}/parallel/close')}"
    contact_ids = [
        f"CONTACT_{stable_uuid(f'{rung_id}/branch/{branch_index}/contact')}"
        for branch_index in range(2)
    ]
    stop_id = f"CONTACT_{stable_uuid(f'{rung_id}/tail/stop')}"
    coil_id = f"COIL_{stable_uuid(f'{rung_id}/coil')}"
    right_id = f"right-rail-{rung_id}"
    open_x = 137 if has_tail_contact else 23
    branch_x = 186 if has_tail_contact else 72
    close_x = 255 if has_tail_contact else 141
    coil_x = 304 if has_tail_contact else 190
    right_x = 442 if has_tail_contact else 328
    nodes = [rail_node(left_id, left=True)]
    if has_tail_contact:
        tail_opcode, tail_operand = parsed.tail_conditions[0]
        nodes.append(
            instruction_node(
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
            parallel_node(
                open_id,
                counterpart_id=close_id,
                open_node=True,
                x=open_x,
            ),
            instruction_node(contact_ids[0], "contact", names[0], branch_x, 24),
            instruction_node(
                contact_ids[1], "contact", names[1], branch_x, 24, y=130
            ),
            parallel_node(
                close_id,
                counterpart_id=open_id,
                open_node=False,
                x=close_x,
            ),
            instruction_node(coil_id, "coil", coil_name, coil_x, 28),
            rail_node(right_id, left=False, x=right_x),
        ]
    )
    first_id = stop_id if has_tail_contact else open_id
    edges = [edge(left_id, "left-rail", first_id, "input")]
    if has_tail_contact:
        edges.append(edge(stop_id, "output", open_id, "input"))
    edges.extend(
        [
            edge(open_id, "output-right", contact_ids[0], "input"),
            edge(contact_ids[0], "output", close_id, "input"),
            edge(open_id, "output-down", contact_ids[1], "input"),
            edge(contact_ids[1], "output", close_id, "input-down"),
            edge(close_id, "output-right", coil_id, "input"),
            edge(coil_id, "output", right_id, "right-rail"),
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
