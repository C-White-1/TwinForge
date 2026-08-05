"""Auditable operator acceptance of discovery reconciliation candidates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from .configured_module_reconciliation import (
    ConfiguredModuleComparisonStatus,
    ConfiguredModuleReconciliationResult,
)
from .identity_reconciliation import IdentityReconciliationResult
from .snmp_entity_candidates import SnmpPhysicalCandidateResult
from .topology import TopologyEvidenceReference


class CandidateDisposition(str, Enum):
    """Explicit operator decision for a reconciliation candidate."""

    ACCEPT = "accept"
    REJECT = "reject"
    DEFER = "defer"


class AcceptancePolicyError(ValueError):
    """A review violates the explicit acceptance policy."""


@dataclass(frozen=True)
class CandidateReview:
    """One attributable and time-qualified operator decision."""

    candidate_key: str
    disposition: CandidateDisposition
    reviewed_by: str
    reviewed_at: datetime
    rationale: str
    durable_identity_key: str | None = None
    override_conflict: bool = False


@dataclass(frozen=True)
class AcceptedIdentityRecord:
    """Durable staging identity assembled without mutating the core model."""

    key: str
    candidate_keys: tuple[str, ...]
    target_keys: tuple[str, ...]
    reviews: tuple[CandidateReview, ...]
    evidence: tuple[TopologyEvidenceReference, ...]
    conflict_overridden: bool


@dataclass(frozen=True)
class AcceptanceResult:
    """Accepted identities and the complete review-state partition."""

    accepted_identities: tuple[AcceptedIdentityRecord, ...]
    rejected_candidate_keys: tuple[str, ...]
    deferred_candidate_keys: tuple[str, ...]
    unreviewed_candidate_keys: tuple[str, ...]


@dataclass(frozen=True)
class _CandidateDescriptor:
    key: str
    target_key: str
    evidence: tuple[TopologyEvidenceReference, ...]
    requires_override: bool = False


def _candidate_catalog(
    physical: SnmpPhysicalCandidateResult,
    identities: IdentityReconciliationResult,
    configured: ConfiguredModuleReconciliationResult,
) -> dict[str, _CandidateDescriptor]:
    descriptors: list[_CandidateDescriptor] = []
    descriptors.extend(
        _CandidateDescriptor(
            key=item.key,
            target_key=item.observation_target,
            evidence=item.evidence,
        )
        for item in physical.assets
    )
    descriptors.extend(
        _CandidateDescriptor(
            key=item.key,
            target_key=item.observation_target,
            evidence=item.evidence,
        )
        for item in identities.matches
    )
    descriptors.extend(
        _CandidateDescriptor(
            key=item.key,
            target_key=item.target_key,
            evidence=item.evidence,
            requires_override=item.status
            in {
                ConfiguredModuleComparisonStatus.CONFLICT,
                ConfiguredModuleComparisonStatus.INSUFFICIENT,
            },
        )
        for item in configured.candidates
    )
    catalog = {item.key: item for item in descriptors}
    if len(catalog) != len(descriptors):
        raise AcceptancePolicyError("candidate keys must be unique")
    return catalog


def _validate_review(
    review: CandidateReview,
    descriptor: _CandidateDescriptor,
) -> None:
    if review.reviewed_at.tzinfo is None:
        raise AcceptancePolicyError("reviewed_at must include a timezone")
    if not review.reviewed_by.strip():
        raise AcceptancePolicyError("reviewed_by must not be blank")
    if review.reviewed_by != review.reviewed_by.strip():
        raise AcceptancePolicyError("reviewed_by must be trimmed")
    if not review.rationale.strip():
        raise AcceptancePolicyError("rationale must not be blank")
    if review.rationale != review.rationale.strip():
        raise AcceptancePolicyError("rationale must be trimmed")
    if review.disposition is CandidateDisposition.ACCEPT:
        if not review.durable_identity_key:
            raise AcceptancePolicyError(
                "accepted candidates require a durable_identity_key"
            )
        if review.durable_identity_key != review.durable_identity_key.strip():
            raise AcceptancePolicyError("durable_identity_key must be trimmed")
        if descriptor.requires_override and not review.override_conflict:
            raise AcceptancePolicyError(
                f"candidate {review.candidate_key!r} requires an explicit override"
            )
        return
    if review.durable_identity_key is not None:
        raise AcceptancePolicyError(
            "rejected or deferred candidates cannot name a durable identity"
        )
    if review.override_conflict:
        raise AcceptancePolicyError(
            "override_conflict is valid only for accepted candidates"
        )


def _evidence_key(
    evidence: TopologyEvidenceReference,
) -> tuple[str, str, str, str]:
    return (
        evidence.protocol,
        evidence.observation_target,
        evidence.identifier,
        evidence.description,
    )


def apply_candidate_reviews(
    physical: SnmpPhysicalCandidateResult,
    identities: IdentityReconciliationResult,
    configured: ConfiguredModuleReconciliationResult,
    reviews: tuple[CandidateReview, ...],
) -> AcceptanceResult:
    """Apply explicit reviews and return durable staging identities."""
    catalog = _candidate_catalog(physical, identities, configured)
    by_candidate: dict[str, CandidateReview] = {}
    for review in reviews:
        descriptor = catalog.get(review.candidate_key)
        if descriptor is None:
            raise AcceptancePolicyError(
                f"unknown candidate key {review.candidate_key!r}"
            )
        if review.candidate_key in by_candidate:
            raise AcceptancePolicyError(
                f"duplicate review for candidate {review.candidate_key!r}"
            )
        _validate_review(review, descriptor)
        by_candidate[review.candidate_key] = review

    accepted: dict[str, list[CandidateReview]] = {}
    rejected: list[str] = []
    deferred: list[str] = []
    for review in reviews:
        if review.disposition is CandidateDisposition.ACCEPT:
            assert review.durable_identity_key is not None
            accepted.setdefault(review.durable_identity_key, []).append(review)
        elif review.disposition is CandidateDisposition.REJECT:
            rejected.append(review.candidate_key)
        else:
            deferred.append(review.candidate_key)

    records: list[AcceptedIdentityRecord] = []
    for durable_key, identity_reviews in accepted.items():
        ordered_reviews = tuple(
            sorted(identity_reviews, key=lambda item: item.candidate_key)
        )
        descriptors = [catalog[item.candidate_key] for item in ordered_reviews]
        evidence_by_key = {
            _evidence_key(item): item
            for descriptor in descriptors
            for item in descriptor.evidence
        }
        records.append(
            AcceptedIdentityRecord(
                key=durable_key,
                candidate_keys=tuple(item.candidate_key for item in ordered_reviews),
                target_keys=tuple(
                    sorted({descriptor.target_key for descriptor in descriptors})
                ),
                reviews=ordered_reviews,
                evidence=tuple(
                    evidence_by_key[key] for key in sorted(evidence_by_key)
                ),
                conflict_overridden=any(
                    item.override_conflict for item in ordered_reviews
                ),
            )
        )

    return AcceptanceResult(
        accepted_identities=tuple(sorted(records, key=lambda item: item.key)),
        rejected_candidate_keys=tuple(sorted(rejected)),
        deferred_candidate_keys=tuple(sorted(deferred)),
        unreviewed_candidate_keys=tuple(sorted(set(catalog) - set(by_candidate))),
    )


def acceptance_data(result: AcceptanceResult) -> dict[str, Any]:
    """Return a stable JSON-compatible acceptance representation."""

    def review_data(review: CandidateReview) -> dict[str, Any]:
        return {
            "candidate_key": review.candidate_key,
            "disposition": review.disposition.value,
            "reviewed_by": review.reviewed_by,
            "reviewed_at": review.reviewed_at.isoformat(),
            "rationale": review.rationale,
            "durable_identity_key": review.durable_identity_key,
            "override_conflict": review.override_conflict,
        }

    return {
        "accepted_identities": [
            {
                "key": item.key,
                "candidate_keys": list(item.candidate_keys),
                "target_keys": list(item.target_keys),
                "reviews": [review_data(review) for review in item.reviews],
                "evidence": [
                    {
                        "protocol": evidence.protocol,
                        "observation_target": evidence.observation_target,
                        "identifier": evidence.identifier,
                        "description": evidence.description,
                    }
                    for evidence in item.evidence
                ],
                "conflict_overridden": item.conflict_overridden,
            }
            for item in result.accepted_identities
        ],
        "rejected_candidate_keys": list(result.rejected_candidate_keys),
        "deferred_candidate_keys": list(result.deferred_candidate_keys),
        "unreviewed_candidate_keys": list(result.unreviewed_candidate_keys),
    }


def acceptance_json(result: AcceptanceResult) -> str:
    """Serialize acceptance records deterministically with a final newline."""
    return json.dumps(acceptance_data(result), indent=2, ensure_ascii=False) + "\n"
