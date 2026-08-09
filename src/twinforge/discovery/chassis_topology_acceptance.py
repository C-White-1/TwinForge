"""Auditable promotion mappings for routed chassis and module evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .acceptance import AcceptancePolicyError, CandidateDisposition
from .configured_module_reconciliation import (
    ConfiguredModuleComparisonStatus,
    RoutedConfiguredModuleBinding,
    RoutedConfiguredModuleReconciliationResult,
)
from .electronic_key_evaluation import ElectronicKeyVerdict
from .topology import TopologyEvidenceReference
from .topology import RelationshipEvidenceClass


@dataclass(frozen=True)
class ChassisModuleMappingReview:
    """Operator decision mapping one routed comparison to core asset IDs."""

    candidate_key: str
    disposition: CandidateDisposition
    reviewed_by: str
    reviewed_at: datetime
    rationale: str
    controller_asset_id: str | None = None
    chassis_asset_id: str | None = None
    module_asset_id: str | None = None
    override_conflict: bool = False


@dataclass(frozen=True)
class AcceptedChassisModuleMapping:
    """Approved, reversible route-and-slot mapping awaiting model mutation."""

    candidate_key: str
    configured_module_key: str
    chassis_route_key: str
    slot: int
    controller_asset_id: str
    chassis_asset_id: str
    module_asset_id: str
    review: ChassisModuleMappingReview
    evidence: tuple[TopologyEvidenceReference, ...]


@dataclass(frozen=True)
class ChassisTopologyAcceptanceResult:
    """Accepted mappings and the complete candidate review partition."""

    accepted_mappings: tuple[AcceptedChassisModuleMapping, ...]
    rejected_candidate_keys: tuple[str, ...]
    deferred_candidate_keys: tuple[str, ...]
    unreviewed_candidate_keys: tuple[str, ...]


def _text(value: str | None, field: str) -> str:
    if value is None or not value.strip():
        raise AcceptancePolicyError(f"accepted mapping requires {field}")
    if value != value.strip():
        raise AcceptancePolicyError(f"{field} must be trimmed")
    return value


def apply_chassis_module_mapping_reviews(
    reconciliation: RoutedConfiguredModuleReconciliationResult,
    bindings: tuple[RoutedConfiguredModuleBinding, ...],
    reviews: tuple[ChassisModuleMappingReview, ...],
) -> ChassisTopologyAcceptanceResult:
    """Approve explicit route-and-slot mappings without changing core objects."""
    candidates = {item.key: item for item in reconciliation.candidates}
    if len(candidates) != len(reconciliation.candidates):
        raise AcceptancePolicyError("routed candidate keys must be unique")
    bindings_by_key = {item.key: item for item in bindings}
    if len(bindings_by_key) != len(bindings):
        raise AcceptancePolicyError("routed binding keys must be unique")

    reviewed: set[str] = set()
    accepted: list[AcceptedChassisModuleMapping] = []
    rejected: list[str] = []
    deferred: list[str] = []
    module_assets: set[str] = set()
    chassis_parents: dict[str, str] = {}
    for review in reviews:
        candidate = candidates.get(review.candidate_key)
        if candidate is None:
            raise AcceptancePolicyError(
                f"unknown routed candidate key {review.candidate_key!r}"
            )
        if review.candidate_key in reviewed:
            raise AcceptancePolicyError(
                f"duplicate review for candidate {review.candidate_key!r}"
            )
        reviewed.add(review.candidate_key)
        _text(review.reviewed_by, "reviewed_by")
        _text(review.rationale, "rationale")
        if review.reviewed_at.tzinfo is None:
            raise AcceptancePolicyError("reviewed_at must include a timezone")

        asset_values = (
            review.controller_asset_id,
            review.chassis_asset_id,
            review.module_asset_id,
        )
        if review.disposition is not CandidateDisposition.ACCEPT:
            if any(value is not None for value in asset_values):
                raise AcceptancePolicyError(
                    "rejected or deferred mappings cannot name core assets"
                )
            if review.override_conflict:
                raise AcceptancePolicyError(
                    "override_conflict is valid only for accepted mappings"
                )
            (rejected if review.disposition is CandidateDisposition.REJECT else deferred).append(
                review.candidate_key
            )
            continue

        binding = bindings_by_key.get(candidate.configured_module_key)
        if binding is None:
            raise AcceptancePolicyError(
                f"candidate {candidate.key!r} has no supplied routed binding"
            )
        requires_override = candidate.status in {
            ConfiguredModuleComparisonStatus.CONFLICT,
            ConfiguredModuleComparisonStatus.INSUFFICIENT,
        }
        evaluation = candidate.electronic_key_evaluation
        if evaluation is not None and evaluation.verdict is ElectronicKeyVerdict.REJECTED:
            requires_override = True
        if requires_override and not review.override_conflict:
            raise AcceptancePolicyError(
                f"candidate {candidate.key!r} requires an explicit override"
            )
        controller_id = _text(review.controller_asset_id, "controller_asset_id")
        chassis_id = _text(review.chassis_asset_id, "chassis_asset_id")
        module_id = _text(review.module_asset_id, "module_asset_id")
        if module_id in module_assets:
            raise AcceptancePolicyError(f"duplicate module asset ID {module_id!r}")
        module_assets.add(module_id)
        parent = chassis_parents.setdefault(chassis_id, controller_id)
        if parent != controller_id:
            raise AcceptancePolicyError(
                f"chassis asset {chassis_id!r} has conflicting controller parents"
            )
        accepted.append(
            AcceptedChassisModuleMapping(
                candidate_key=candidate.key,
                configured_module_key=binding.key,
                chassis_route_key=binding.chassis_route_key,
                slot=binding.slot,
                controller_asset_id=controller_id,
                chassis_asset_id=chassis_id,
                module_asset_id=module_id,
                review=review,
                evidence=candidate.evidence,
            )
        )

    return ChassisTopologyAcceptanceResult(
        accepted_mappings=tuple(sorted(accepted, key=lambda item: item.candidate_key)),
        rejected_candidate_keys=tuple(sorted(rejected)),
        deferred_candidate_keys=tuple(sorted(deferred)),
        unreviewed_candidate_keys=tuple(sorted(set(candidates) - reviewed)),
    )


def chassis_topology_acceptance_data(
    result: ChassisTopologyAcceptanceResult,
) -> dict[str, Any]:
    """Return a deterministic JSON-compatible mapping review document."""
    return {
        "accepted_mappings": [
            {
                "candidate_key": item.candidate_key,
                "evidence_class": RelationshipEvidenceClass.OPERATOR_ACCEPTED.value,
                "configured_module_key": item.configured_module_key,
                "chassis_route_key": item.chassis_route_key,
                "slot": item.slot,
                "controller_asset_id": item.controller_asset_id,
                "chassis_asset_id": item.chassis_asset_id,
                "module_asset_id": item.module_asset_id,
                "review": {
                    "reviewed_by": item.review.reviewed_by,
                    "reviewed_at": item.review.reviewed_at.isoformat(),
                    "rationale": item.review.rationale,
                    "override_conflict": item.review.override_conflict,
                },
                "evidence": [
                    {
                        "protocol": evidence.protocol,
                        "observation_target": evidence.observation_target,
                        "identifier": evidence.identifier,
                        "description": evidence.description,
                    }
                    for evidence in item.evidence
                ],
            }
            for item in result.accepted_mappings
        ],
        "rejected_candidate_keys": list(result.rejected_candidate_keys),
        "deferred_candidate_keys": list(result.deferred_candidate_keys),
        "unreviewed_candidate_keys": list(result.unreviewed_candidate_keys),
    }


def chassis_topology_acceptance_json(
    result: ChassisTopologyAcceptanceResult,
) -> str:
    """Serialize approved chassis/module mappings deterministically."""
    return json.dumps(
        chassis_topology_acceptance_data(result), indent=2, ensure_ascii=False
    ) + "\n"
