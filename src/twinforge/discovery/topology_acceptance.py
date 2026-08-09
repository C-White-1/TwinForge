"""Auditable acceptance boundary for discovered topology relationships."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .acceptance import AcceptancePolicyError, CandidateDisposition
from .topology import (
    RelationshipEvidenceClass,
    TopologyCorrelationResult,
    TopologyEvidenceReference,
    TopologyRelationshipCandidate,
    TopologyRelationshipType,
)


@dataclass(frozen=True)
class TopologyRelationshipReview:
    """One operator decision and optional durable endpoint mapping."""

    candidate_key: str
    disposition: CandidateDisposition
    reviewed_by: str
    reviewed_at: datetime
    rationale: str
    source_asset_key: str | None = None
    target_asset_key: str | None = None


@dataclass(frozen=True)
class AcceptedTopologyRelationship:
    """Staged physical relationship without mutating the core model."""

    key: str
    candidate_key: str
    source_node_key: str
    target_node_key: str
    source_asset_key: str
    target_asset_key: str
    source_interface_index: int | None
    source_port_number: int | None
    target_port_id: str | None
    review: TopologyRelationshipReview
    evidence: tuple[TopologyEvidenceReference, ...]


@dataclass(frozen=True)
class TopologyAcceptanceResult:
    """Accepted relationships and complete review-state partition."""

    accepted_relationships: tuple[AcceptedTopologyRelationship, ...]
    rejected_candidate_keys: tuple[str, ...]
    deferred_candidate_keys: tuple[str, ...]
    unreviewed_candidate_keys: tuple[str, ...]


def apply_topology_reviews(
    topology: TopologyCorrelationResult,
    reviews: tuple[TopologyRelationshipReview, ...],
) -> TopologyAcceptanceResult:
    """Validate reviews and stage only protocol-reported relationships."""
    catalog = {item.key: item for item in topology.relationships}
    if len(catalog) != len(topology.relationships):
        raise AcceptancePolicyError("topology candidate keys must be unique")
    reviewed: set[str] = set()
    accepted: list[AcceptedTopologyRelationship] = []
    rejected: list[str] = []
    deferred: list[str] = []
    for review in reviews:
        candidate = catalog.get(review.candidate_key)
        if candidate is None:
            raise AcceptancePolicyError(
                f"unknown topology candidate {review.candidate_key!r}"
            )
        if review.candidate_key in reviewed:
            raise AcceptancePolicyError(
                f"duplicate topology review for {review.candidate_key!r}"
            )
        _validate_review(review, candidate)
        reviewed.add(review.candidate_key)
        if review.disposition is CandidateDisposition.ACCEPT:
            assert review.source_asset_key is not None
            assert review.target_asset_key is not None
            accepted.append(
                AcceptedTopologyRelationship(
                    key=(
                        f"source:{review.source_asset_key}|"
                        f"target:{review.target_asset_key}|"
                        f"candidate:{candidate.key}"
                    ),
                    candidate_key=candidate.key,
                    source_node_key=candidate.source_node_key,
                    target_node_key=candidate.target_node_key,
                    source_asset_key=review.source_asset_key,
                    target_asset_key=review.target_asset_key,
                    source_interface_index=candidate.source_interface_index,
                    source_port_number=candidate.source_port_number,
                    target_port_id=candidate.target_port_id,
                    review=review,
                    evidence=candidate.evidence,
                )
            )
        elif review.disposition is CandidateDisposition.REJECT:
            rejected.append(candidate.key)
        else:
            deferred.append(candidate.key)
    return TopologyAcceptanceResult(
        accepted_relationships=tuple(sorted(accepted, key=lambda item: item.key)),
        rejected_candidate_keys=tuple(sorted(rejected)),
        deferred_candidate_keys=tuple(sorted(deferred)),
        unreviewed_candidate_keys=tuple(sorted(set(catalog) - reviewed)),
    )


def _validate_review(
    review: TopologyRelationshipReview,
    candidate: TopologyRelationshipCandidate,
) -> None:
    for name, value in (
        ("reviewed_by", review.reviewed_by),
        ("rationale", review.rationale),
    ):
        if not value or value != value.strip():
            raise AcceptancePolicyError(f"{name} must be non-empty and trimmed")
    if review.reviewed_at.tzinfo is None:
        raise AcceptancePolicyError("reviewed_at must include a timezone")
    endpoint_keys = (review.source_asset_key, review.target_asset_key)
    if review.disposition is not CandidateDisposition.ACCEPT:
        if any(value is not None for value in endpoint_keys):
            raise AcceptancePolicyError(
                "rejected or deferred topology candidates cannot map endpoints"
            )
        return
    if candidate.relationship_type is not TopologyRelationshipType.REPORTED_NEIGHBOUR:
        raise AcceptancePolicyError(
            "indirect MAC reachability cannot be accepted as a connection"
        )
    if not candidate.evidence:
        raise AcceptancePolicyError(
            "accepted topology candidates require retained protocol evidence"
        )
    for name, value in (
        ("source_asset_key", review.source_asset_key),
        ("target_asset_key", review.target_asset_key),
    ):
        if value is None or not value or value != value.strip():
            raise AcceptancePolicyError(f"accepted relationships require {name}")
    if review.source_asset_key == review.target_asset_key:
        raise AcceptancePolicyError(
            "accepted relationship endpoints must be different assets"
        )


def topology_acceptance_data(result: TopologyAcceptanceResult) -> dict[str, Any]:
    """Return deterministic JSON-compatible topology acceptance evidence."""
    return {
        "accepted_relationships": [
            {
                "key": item.key,
                "evidence_class": RelationshipEvidenceClass.OPERATOR_ACCEPTED.value,
                "candidate_key": item.candidate_key,
                "source_node_key": item.source_node_key,
                "target_node_key": item.target_node_key,
                "source_asset_key": item.source_asset_key,
                "target_asset_key": item.target_asset_key,
                "source_interface_index": item.source_interface_index,
                "source_port_number": item.source_port_number,
                "target_port_id": item.target_port_id,
                "review": {
                    "reviewed_by": item.review.reviewed_by,
                    "reviewed_at": item.review.reviewed_at.isoformat(),
                    "rationale": item.review.rationale,
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
            for item in result.accepted_relationships
        ],
        "rejected_candidate_keys": list(result.rejected_candidate_keys),
        "deferred_candidate_keys": list(result.deferred_candidate_keys),
        "unreviewed_candidate_keys": list(result.unreviewed_candidate_keys),
    }


def topology_acceptance_json(result: TopologyAcceptanceResult) -> str:
    """Serialize topology acceptance evidence with a final newline."""
    return json.dumps(
        topology_acceptance_data(result),
        indent=2,
        ensure_ascii=False,
    ) + "\n"
