"""Build a vendor-neutral, evidence-bound controller I/O schedule."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass

from twinforge.model import Controller, IODirection, IOSignalType, Module, Tag


@dataclass(frozen=True)
class IOChannel:
    """One known physical channel and its observed software assignments."""

    chassis: str | None
    module_name: str
    slot: int | None
    catalog_number: str
    vendor: str | None
    signal_type: IOSignalType
    direction: IODirection
    channel: int
    member: str
    source_operand: str | None
    assignment_status: str
    assigned_tags: tuple[str, ...]
    descriptions: tuple[str, ...]
    engineering_unit: str | None
    lower_range: float | None
    upper_range: float | None
    capability_source: str


@dataclass(frozen=True)
class UnresolvedIOAlias:
    """An explicit local I/O alias not matched to a known physical channel."""

    tag_name: str
    alias_for: str
    reason: str


@dataclass(frozen=True)
class IOListReport:
    """Deterministic I/O channels plus unresolved alias evidence."""

    controller_name: str
    channels: tuple[IOChannel, ...]
    unresolved_aliases: tuple[UnresolvedIOAlias, ...]


_LOCAL_IO = re.compile(
    r"Local:(?P<slot>\d+):(?P<direction>[IO])\."
    r"(?:(?:Data\.(?P<bit>\d+))|(?:Ch(?P<channel>\d+)Data))",
    re.IGNORECASE,
)


def build_io_list_report(controller: Controller) -> IOListReport:
    """Build channels only from modeled capability and explicit alias evidence."""
    assignments, unresolved = _alias_assignments(controller)
    channels: list[IOChannel] = []
    matched: set[tuple[int, str, int]] = set()
    for chassis_name, module in _modules(controller):
        capability = module.capability
        if capability is None:
            continue
        for channel in range(capability.nominal_channel_count):
            if module.slot is None:
                tags: tuple[Tag, ...] = ()
            else:
                key = (module.slot, capability.direction.value, channel)
                tags = assignments.get(key, ())
                if tags:
                    matched.add(key)
            member = _member(capability.signal_type, capability.direction, channel)
            unit = module.engineering_units.get(member)
            engineering_range = module.engineering_ranges.get(member)
            status = "assigned" if tags else "spare"
            configured = capability.configured_channel_count
            if configured is not None and channel >= configured:
                status = "unavailable_by_configuration"
            channels.append(
                IOChannel(
                    chassis=chassis_name,
                    module_name=module.name,
                    slot=module.slot,
                    catalog_number=module.catalog,
                    vendor=(
                        str(module.identity.vendor)
                        if module.identity.vendor is not None
                        else None
                    ),
                    signal_type=capability.signal_type,
                    direction=capability.direction,
                    channel=channel,
                    member=member,
                    source_operand=(
                        _operand(module.slot, member)
                        if module.slot is not None
                        else None
                    ),
                    assignment_status=status,
                    assigned_tags=tuple(tag.name for tag in tags),
                    descriptions=tuple(
                        tag.description
                        for tag in tags
                        if tag.description is not None
                    ),
                    engineering_unit=unit.symbol if unit is not None else None,
                    lower_range=(
                        engineering_range.lower
                        if engineering_range is not None
                        else None
                    ),
                    upper_range=(
                        engineering_range.upper
                        if engineering_range is not None
                        else None
                    ),
                    capability_source=capability.source,
                )
            )
    for key, tags in assignments.items():
        if key in matched:
            continue
        unresolved.extend(
            UnresolvedIOAlias(
                tag_name=tag.name,
                alias_for=tag.alias_for or "",
                reason="no matching modeled physical channel",
            )
            for tag in tags
        )
    return IOListReport(
        controller_name=controller.name,
        channels=tuple(
            sorted(
                channels,
                key=lambda item: (
                    item.chassis or "",
                    item.slot if item.slot is not None else -1,
                    item.module_name,
                    item.channel,
                ),
            )
        ),
        unresolved_aliases=tuple(
            sorted(unresolved, key=lambda item: (item.tag_name, item.alias_for))
        ),
    )


def io_list_report_data(report: IOListReport) -> dict[str, object]:
    """Return deterministic JSON-compatible I/O report data."""
    return {
        "controller_name": report.controller_name,
        "channels": [
            {
                **asdict(item),
                "signal_type": item.signal_type.value,
                "direction": item.direction.value,
            }
            for item in report.channels
        ],
        "unresolved_aliases": [asdict(item) for item in report.unresolved_aliases],
    }


def io_list_report_json(report: IOListReport) -> str:
    """Serialize an I/O list deterministically."""
    return json.dumps(io_list_report_data(report), indent=2) + "\n"


def _alias_assignments(
    controller: Controller,
) -> tuple[dict[tuple[int, str, int], tuple[Tag, ...]], list[UnresolvedIOAlias]]:
    found: dict[tuple[int, str, int], list[Tag]] = {}
    unresolved: list[UnresolvedIOAlias] = []
    tags = list(controller.tags.values())
    for program in controller.iter_programs():
        tags.extend(program.tags.values())
    for tag in tags:
        if not tag.alias_for or not tag.alias_for.casefold().startswith("local:"):
            continue
        match = _LOCAL_IO.fullmatch(tag.alias_for)
        if match is None:
            unresolved.append(
                UnresolvedIOAlias(tag.name, tag.alias_for, "unsupported local I/O address")
            )
            continue
        channel = match.group("bit") or match.group("channel")
        key = (
            int(match.group("slot")),
            "Input" if match.group("direction").casefold() == "i" else "Output",
            int(channel),
        )
        found.setdefault(key, []).append(tag)
    return (
        {key: tuple(sorted(value, key=lambda tag: tag.name)) for key, value in found.items()},
        unresolved,
    )


def _modules(controller: Controller) -> tuple[tuple[str | None, Module], ...]:
    found: list[tuple[str | None, Module]] = []
    pending: list[tuple[str | None, Module]] = []
    for chassis in controller.iter_chassis():
        pending.extend((chassis.name, module) for module in chassis.iter_modules())
    pending.extend((None, module) for module in controller.unplaced_modules)
    while pending:
        chassis_name, module = pending.pop(0)
        found.append((chassis_name, module))
        pending.extend((chassis_name, child) for child in module.child_modules)
    return tuple(found)


def _member(
    signal_type: IOSignalType,
    direction: IODirection,
    channel: int,
) -> str:
    prefix = "i" if direction is IODirection.INPUT else "o"
    if signal_type is IOSignalType.DIGITAL:
        return f"{prefix}.data.{channel}"
    return f"{prefix}.ch{channel}data"


def _operand(slot: int, member: str) -> str:
    direction, _, path = member.partition(".")
    if path.startswith("data."):
        suffix = f"Data.{path.removeprefix('data.')}"
    else:
        match = re.fullmatch(r"ch(\d+)data", path)
        suffix = f"Ch{match.group(1)}Data" if match is not None else path
    return f"Local:{slot}:{direction.upper()}.{suffix}"
