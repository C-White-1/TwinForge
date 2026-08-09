"""Reconcile structural CIP inventory with an explicitly bound controller."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

from twinforge.model import Controller

from .software_inventory_capture import (
    CipSoftwareInventoryItem,
    CipSoftwareInventoryObservation,
)
from .software_inventory_plan import CipSoftwareInventoryCapability


class SoftwareInventoryComparisonStatus(str, Enum):
    """Outcome of comparing one shared structural software identity."""

    EXACT = "exact"
    PARTIAL = "partial"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class ConfiguredSoftwareBinding:
    """Explicit association between an observation and an L5X controller."""

    key: str
    controller: Controller

    def __post_init__(self) -> None:
        if not self.key or self.key != self.key.strip():
            raise ValueError("configured software binding key must be trimmed")


@dataclass(frozen=True)
class SoftwareInventoryComparison:
    """One name-scoped structural comparison without runtime values."""

    key: str
    status: SoftwareInventoryComparisonStatus
    matched_fields: tuple[str, ...]
    conflicting_fields: tuple[str, ...]
    unavailable_fields: tuple[str, ...]


@dataclass(frozen=True)
class SoftwareInventoryReconciliationResult:
    """Shared, configured-only, and discovered-only structural evidence."""

    binding_key: str
    comparisons: tuple[SoftwareInventoryComparison, ...]
    configured_only: tuple[str, ...]
    discovered_only: tuple[str, ...]


def reconcile_software_inventory(
    observation: CipSoftwareInventoryObservation,
    binding: ConfiguredSoftwareBinding,
) -> SoftwareInventoryReconciliationResult:
    """Compare only capabilities actually requested in the observation."""
    configured = _configured_items(binding.controller, observation.capabilities)
    discovered = {_item_key(item): item for item in observation.items}
    if len(discovered) != len(observation.items):
        raise ValueError("software inventory contains duplicate structural keys")
    shared = sorted(set(configured) & set(discovered))
    return SoftwareInventoryReconciliationResult(
        binding_key=binding.key,
        comparisons=tuple(
            _compare_item(key, configured[key], discovered[key]) for key in shared
        ),
        configured_only=tuple(sorted(set(configured) - set(discovered))),
        discovered_only=tuple(sorted(set(discovered) - set(configured))),
    )


def _configured_items(
    controller: Controller,
    capabilities: tuple[CipSoftwareInventoryCapability, ...],
) -> dict[str, CipSoftwareInventoryItem]:
    requested = set(capabilities)
    items: list[CipSoftwareInventoryItem] = []
    if CipSoftwareInventoryCapability.PROGRAMS in requested:
        items.extend(
            CipSoftwareInventoryItem(
                capability=CipSoftwareInventoryCapability.PROGRAMS,
                name=program.name,
            )
            for program in controller.programs.values()
        )
    if CipSoftwareInventoryCapability.ROUTINES in requested:
        for program in controller.programs.values():
            items.extend(
                CipSoftwareInventoryItem(
                    capability=CipSoftwareInventoryCapability.ROUTINES,
                    name=routine.name,
                    parent=program.name,
                    language=routine.language,
                )
                for routine in program.routines.values()
            )
    if CipSoftwareInventoryCapability.TASKS in requested:
        items.extend(
            CipSoftwareInventoryItem(
                capability=CipSoftwareInventoryCapability.TASKS,
                name=task.name,
            )
            for task in controller.tasks.values()
        )
    if CipSoftwareInventoryCapability.TAG_DEFINITIONS in requested:
        items.extend(
            CipSoftwareInventoryItem(
                capability=CipSoftwareInventoryCapability.TAG_DEFINITIONS,
                name=tag.name,
                data_type=tag.data_type,
            )
            for tag in controller.tags.values()
        )
        for program in controller.programs.values():
            items.extend(
                CipSoftwareInventoryItem(
                    capability=CipSoftwareInventoryCapability.TAG_DEFINITIONS,
                    name=tag.name,
                    parent=program.name,
                    data_type=tag.data_type,
                )
                for tag in program.tags.values()
            )
    return {_item_key(item): item for item in items}


def _item_key(item: CipSoftwareInventoryItem) -> str:
    parent = item.parent or "controller"
    return f"{item.capability.value}|{parent}|{item.name}"


def _compare_item(
    key: str,
    configured: CipSoftwareInventoryItem,
    discovered: CipSoftwareInventoryItem,
) -> SoftwareInventoryComparison:
    matched = ["name"]
    conflicting: list[str] = []
    unavailable: list[str] = []
    for field in ("data_type", "language"):
        configured_value = getattr(configured, field)
        discovered_value = getattr(discovered, field)
        if configured_value is None:
            continue
        if discovered_value is None:
            unavailable.append(field)
        elif configured_value == discovered_value:
            matched.append(field)
        else:
            conflicting.append(field)
    status = (
        SoftwareInventoryComparisonStatus.CONFLICT
        if conflicting
        else SoftwareInventoryComparisonStatus.PARTIAL
        if unavailable
        else SoftwareInventoryComparisonStatus.EXACT
    )
    return SoftwareInventoryComparison(
        key=key,
        status=status,
        matched_fields=tuple(matched),
        conflicting_fields=tuple(conflicting),
        unavailable_fields=tuple(unavailable),
    )


def software_inventory_reconciliation_data(
    result: SoftwareInventoryReconciliationResult,
) -> dict[str, Any]:
    """Return deterministic reconciliation data without runtime values."""
    return {
        "binding_key": result.binding_key,
        "runtime_values_included": False,
        "comparisons": [
            {
                "key": item.key,
                "status": item.status.value,
                "matched_fields": list(item.matched_fields),
                "conflicting_fields": list(item.conflicting_fields),
                "unavailable_fields": list(item.unavailable_fields),
            }
            for item in result.comparisons
        ],
        "configured_only": list(result.configured_only),
        "discovered_only": list(result.discovered_only),
    }


def software_inventory_reconciliation_json(
    result: SoftwareInventoryReconciliationResult,
) -> str:
    """Serialize structural software reconciliation deterministically."""
    return json.dumps(
        software_inventory_reconciliation_data(result),
        indent=2,
        ensure_ascii=False,
    ) + "\n"
