"""Build a module and spare-I/O schedule from modeled controller evidence."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from twinforge.model import Controller, Module

from .io_list import IOListReport


@dataclass(frozen=True)
class ModuleScheduleEntry:
    """One controller module with explicit capacity and assignment counts."""

    chassis: str | None
    parent_module: str | None
    slot: int | None
    address: str | None
    module_name: str
    catalog_number: str
    vendor: str | None
    signal_type: str | None
    direction: str | None
    nominal_channels: int | None
    configured_channels: int | None
    assigned_channels: int
    spare_candidates: int
    unavailable_by_configuration: int
    capability_status: str
    capability_source: str | None
    inhibited: bool | None
    major_fault_on_connection_loss: bool | None
    electronic_keying: str | None


@dataclass(frozen=True)
class ModuleScheduleReport:
    """Deterministic module inventory and spare-I/O summary."""

    controller_name: str
    modules: tuple[ModuleScheduleEntry, ...]


def build_module_schedule_report(
    controller: Controller,
    io_list: IOListReport,
) -> ModuleScheduleReport:
    """Aggregate channel evidence while retaining modules of unknown capability."""
    channels_by_module: dict[tuple[str | None, int | None, str], list[str]] = {}
    for channel in io_list.channels:
        key = (channel.chassis, channel.slot, channel.module_name)
        channels_by_module.setdefault(key, []).append(channel.assignment_status)
    entries: list[ModuleScheduleEntry] = []
    for chassis, parent, module in _modules(controller):
        capability = module.capability
        statuses = channels_by_module.get((chassis, module.slot, module.name), [])
        entries.append(
            ModuleScheduleEntry(
                chassis=chassis,
                parent_module=parent,
                slot=module.slot,
                address=module.address,
                module_name=module.name,
                catalog_number=module.catalog,
                vendor=(
                    str(module.identity.vendor)
                    if module.identity.vendor is not None
                    else None
                ),
                signal_type=(
                    capability.signal_type.value if capability is not None else None
                ),
                direction=(
                    capability.direction.value if capability is not None else None
                ),
                nominal_channels=(
                    capability.nominal_channel_count if capability is not None else None
                ),
                configured_channels=(
                    capability.configured_channel_count
                    if capability is not None
                    else None
                ),
                assigned_channels=statuses.count("assigned"),
                spare_candidates=statuses.count("spare"),
                unavailable_by_configuration=statuses.count(
                    "unavailable_by_configuration"
                ),
                capability_status=("known" if capability is not None else "unknown"),
                capability_source=(
                    capability.source if capability is not None else None
                ),
                inhibited=module.inhibited,
                major_fault_on_connection_loss=(module.major_fault_on_connection_loss),
                electronic_keying=(
                    module.electronic_key.mode.value
                    if module.electronic_key is not None
                    and module.electronic_key.mode is not None
                    else None
                ),
            )
        )
    return ModuleScheduleReport(
        controller_name=controller.name,
        modules=tuple(sorted(entries, key=_entry_key)),
    )


def module_schedule_report_data(
    report: ModuleScheduleReport,
) -> dict[str, object]:
    """Return deterministic JSON-compatible schedule data."""
    return {
        "controller_name": report.controller_name,
        "modules": [asdict(item) for item in report.modules],
    }


def module_schedule_report_json(report: ModuleScheduleReport) -> str:
    """Serialize a module schedule deterministically."""
    return json.dumps(module_schedule_report_data(report), indent=2) + "\n"


def _modules(
    controller: Controller,
) -> tuple[tuple[str | None, str | None, Module], ...]:
    found: list[tuple[str | None, str | None, Module]] = []
    pending: list[tuple[str | None, str | None, Module]] = []
    for chassis in controller.iter_chassis():
        pending.extend(
            (chassis.name, None, module) for module in chassis.iter_modules()
        )
    pending.extend((None, None, module) for module in controller.unplaced_modules)
    while pending:
        chassis, parent, module = pending.pop(0)
        found.append((chassis, parent, module))
        pending.extend((chassis, module.name, child) for child in module.child_modules)
    return tuple(found)


def _entry_key(item: ModuleScheduleEntry) -> tuple[object, ...]:
    return (
        item.chassis or "",
        item.slot if item.slot is not None else -1,
        item.parent_module or "",
        item.module_name,
    )
