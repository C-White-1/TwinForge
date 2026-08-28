"""Reconcile configured controller modules with a local EDS catalogue."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum

from twinforge.knowledge.catalog_reconciliation import (
    CatalogCandidateStatus,
    CatalogReconciliation,
    reconcile_catalog_candidates,
)
from twinforge.knowledge.device_catalog import BaseCatalogDeviceCatalog
from twinforge.model import Controller, Module


class ModuleCatalogStatus(str, Enum):
    """Summary outcome for one configured module."""

    NO_CANDIDATES = "no_candidates"
    SELECTED_EXACT = "selected_exact"
    ADVISORY = "advisory"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class ModuleCatalogAssessment:
    """Catalogue reconciliation for one configured module."""

    chassis: str | None
    module: Module
    status: ModuleCatalogStatus
    reconciliation: CatalogReconciliation


def assess_controller_eds_catalog(
    controller: Controller,
    catalog: BaseCatalogDeviceCatalog,
) -> tuple[ModuleCatalogAssessment, ...]:
    """Assess every configured module without selecting compatible guesses."""

    assessments: list[ModuleCatalogAssessment] = []
    for chassis_name, module in _controller_modules(controller):
        candidates = catalog.find_by_base_catalog_number(module.catalog)
        reconciliation = reconcile_catalog_candidates(
            module.electronic_key,
            candidates,
            fallback_identity=module.identity,
        )
        if not candidates:
            status = ModuleCatalogStatus.NO_CANDIDATES
        elif reconciliation.selected is not None:
            status = ModuleCatalogStatus.SELECTED_EXACT
        elif any(
            item.status is CatalogCandidateStatus.TYPICAL_COMPATIBLE
            for item in reconciliation.candidates
        ):
            status = ModuleCatalogStatus.ADVISORY
        else:
            status = ModuleCatalogStatus.UNRESOLVED
        assessments.append(
            ModuleCatalogAssessment(
                chassis=chassis_name,
                module=module,
                status=status,
                reconciliation=reconciliation,
            )
        )
    return tuple(assessments)


def _controller_modules(controller: Controller) -> Iterator[tuple[str | None, Module]]:
    for chassis in controller.iter_chassis():
        for module in chassis.iter_modules():
            yield from _module_tree(chassis.name, module)
    for module in controller.unplaced_modules:
        yield from _module_tree(None, module)


def _module_tree(
    chassis_name: str | None,
    module: Module,
) -> Iterator[tuple[str | None, Module]]:
    yield chassis_name, module
    for child in module.child_modules:
        yield from _module_tree(chassis_name, child)
