"""Physical I/O evidence extraction for CCW-lowered controllers."""

from __future__ import annotations

import re

from twinforge.model import Controller, IODirection, IOSignalType, Tag

CCW_IO_ADDRESS = re.compile(r"(?:^|_)(?P<code>DI|DO|AI|AO)_\d+$", re.IGNORECASE)
CCW_IO_KINDS = {
    "DI": (IODirection.INPUT, IOSignalType.DIGITAL),
    "DO": (IODirection.OUTPUT, IOSignalType.DIGITAL),
    "AI": (IODirection.INPUT, IOSignalType.ANALOG),
    "AO": (IODirection.OUTPUT, IOSignalType.ANALOG),
}


def physical_io_points(
    controller: Controller,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Report every known physical point plus any binding that matches none."""

    bindings: dict[str, list[tuple[Tag, str]]] = {}
    for tag in controller.iter_tags():
        source = tag.metadata.get("physical_source")
        if source:
            bindings.setdefault(source, []).append((tag, "input"))
        destination = tag.metadata.get("physical_destination")
        if destination:
            bindings.setdefault(destination, []).append((tag, "output"))

    physical_tags = {
        tag.name: tag
        for tag in controller.iter_tags()
        if tag.metadata.get("ccw_classification") == "physical_io"
    }

    points = [
        physical_io_point(name, tag, bindings.get(name, []))
        for name, tag in sorted(physical_tags.items())
    ]
    unresolved: list[dict[str, object]] = [
        {
            "tag_name": tag.name,
            "physical_address": address,
            "reason": "no matching physical_io-classified CCW variable",
        }
        for address in sorted(set(bindings) - set(physical_tags))
        for tag, _ in bindings[address]
    ]
    return points, unresolved


def physical_io_point(
    address: str,
    physical_tag: Tag,
    linked: list[tuple[Tag, str]],
) -> dict[str, object]:
    direction, signal_type = classify_ccw_address(address)
    if direction is None:
        bound_directions = {value for _, value in linked}
        if len(bound_directions) == 1:
            direction = (
                IODirection.INPUT
                if bound_directions.pop() == "input"
                else IODirection.OUTPUT
            )
    if signal_type is None:
        data_type = physical_tag.data_type or next(
            (tag.data_type for tag, _ in linked if tag.data_type), None
        )
        if data_type is not None:
            signal_type = (
                IOSignalType.DIGITAL
                if data_type.upper() == "BOOL"
                else IOSignalType.ANALOG
            )
    alias_sources = [tag for tag, _ in linked]
    alias_sources.append(physical_tag)
    aliases = sorted(
        {alias for tag in alias_sources for alias in tag.metadata.get("aliases", [])}
    )
    variable_names = sorted({tag.name for tag, _ in linked})
    return {
        "physical_address": address,
        "direction": direction.value if direction is not None else None,
        "signal_type": signal_type.value if signal_type is not None else None,
        "data_type": physical_tag.data_type,
        "assignment_status": "assigned" if linked else "spare",
        "variable_names": variable_names,
        "aliases": aliases,
    }


def classify_ccw_address(
    address: str,
) -> tuple[IODirection | None, IOSignalType | None]:
    match = CCW_IO_ADDRESS.search(address)
    if match is None:
        return None, None
    return CCW_IO_KINDS[match.group("code").upper()]
