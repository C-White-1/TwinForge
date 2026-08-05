from datetime import datetime, timezone

import pytest

from twinforge.discovery import (
    AcceptancePolicyError,
    CandidateDisposition,
    CandidateReview,
    ConfiguredModuleComparisonStatus,
    ConfiguredModuleReconciliationCandidate,
    ConfiguredModuleReconciliationResult,
    IdentityReconciliationResult,
    SnmpPhysicalAssetCandidate,
    SnmpPhysicalCandidateResult,
    TopologyConfidence,
    TopologyEvidenceReference,
    acceptance_json,
    apply_candidate_reviews,
)


REVIEWED_AT = datetime(2026, 8, 5, 6, 7, 8, tzinfo=timezone.utc)
TARGET = "192.0.2.100|"


def _evidence(identifier: str) -> tuple[TopologyEvidenceReference, ...]:
    return (
        TopologyEvidenceReference(
            protocol="fixture",
            observation_target=TARGET,
            identifier=identifier,
            description="retained fixture evidence",
        ),
    )


def _results(
    status: ConfiguredModuleComparisonStatus = (
        ConfiguredModuleComparisonStatus.EXACT
    ),
) -> tuple[
    SnmpPhysicalCandidateResult,
    IdentityReconciliationResult,
    ConfiguredModuleReconciliationResult,
]:
    physical_key = f"target:{TARGET}|entity:1"
    physical = SnmpPhysicalCandidateResult(
        assets=(
            SnmpPhysicalAssetCandidate(
                key=physical_key,
                observation_target=TARGET,
                entity_index=1,
                physical_class=3,
                name="Controller",
                description=None,
                manufacturer_name="Example Corp",
                model_name="EX-1",
                serial_number="123",
                asset_id=None,
                uuid=None,
                confidence=TopologyConfidence.PROTOCOL_REPORTED,
                evidence=_evidence("entity.1"),
            ),
        ),
        containments=(),
        issues=(),
    )
    identity_key = f"cip:{TARGET}|matches:{physical_key}"
    from twinforge.discovery import CipPhysicalReconciliationCandidate

    identities = IdentityReconciliationResult(
        matches=(
            CipPhysicalReconciliationCandidate(
                key=identity_key,
                observation_target=TARGET,
                physical_asset_key=physical_key,
                matched_fields=("product_name",),
                confidence=TopologyConfidence.CORROBORATED,
                evidence=_evidence("cip.product_name"),
            ),
        ),
        unmatched_cip_targets=(),
        unmatched_physical_assets=(),
    )
    configured = ConfiguredModuleReconciliationResult(
        candidates=(
            ConfiguredModuleReconciliationCandidate(
                key="configured:controller/module|compares:192.0.2.100|",
                configured_module_key="controller/module",
                target_key=TARGET,
                status=status,
                matched_fields=("module_identity.vendor_id",),
                conflicting_fields=("module_identity.product_code",)
                if status is ConfiguredModuleComparisonStatus.CONFLICT
                else (),
                unavailable_fields=(),
                electronic_key_mode="compatible_module",
                physical_asset_keys=(physical_key,),
                confidence=TopologyConfidence.CORROBORATED,
                evidence=_evidence("configured.vendor_id"),
            ),
        ),
        targets_without_cip_identity=(),
    )
    return physical, identities, configured


def _review(
    candidate_key: str,
    disposition: CandidateDisposition,
    *,
    durable_key: str | None = None,
    override: bool = False,
) -> CandidateReview:
    return CandidateReview(
        candidate_key=candidate_key,
        disposition=disposition,
        reviewed_by="operator@example.test",
        reviewed_at=REVIEWED_AT,
        rationale="Reviewed against authorized laboratory evidence.",
        durable_identity_key=durable_key,
        override_conflict=override,
    )


def test_acceptance_groups_candidates_without_mutating_source_results() -> None:
    physical, identities, configured = _results()
    candidate_keys = (
        physical.assets[0].key,
        identities.matches[0].key,
        configured.candidates[0].key,
    )
    reviews = tuple(
        _review(
            key,
            CandidateDisposition.ACCEPT,
            durable_key="asset:lab-controller-1",
        )
        for key in candidate_keys
    )

    result = apply_candidate_reviews(physical, identities, configured, reviews)

    assert len(result.accepted_identities) == 1
    accepted = result.accepted_identities[0]
    assert accepted.key == "asset:lab-controller-1"
    assert accepted.candidate_keys == tuple(sorted(candidate_keys))
    assert accepted.target_keys == (TARGET,)
    assert {item.identifier for item in accepted.evidence} == {
        "entity.1",
        "cip.product_name",
        "configured.vendor_id",
    }
    assert accepted.conflict_overridden is False
    assert result.unreviewed_candidate_keys == ()


def test_conflicting_comparison_requires_an_explicit_recorded_override() -> None:
    physical, identities, configured = _results(
        ConfiguredModuleComparisonStatus.CONFLICT
    )
    candidate = configured.candidates[0]

    with pytest.raises(AcceptancePolicyError, match="explicit override"):
        apply_candidate_reviews(
            physical,
            identities,
            configured,
            (
                _review(
                    candidate.key,
                    CandidateDisposition.ACCEPT,
                    durable_key="asset:override",
                ),
            ),
        )

    result = apply_candidate_reviews(
        physical,
        identities,
        configured,
        (
            _review(
                candidate.key,
                CandidateDisposition.ACCEPT,
                durable_key="asset:override",
                override=True,
            ),
        ),
    )
    assert result.accepted_identities[0].conflict_overridden is True


def test_rejected_deferred_and_unreviewed_candidates_remain_partitioned() -> None:
    physical, identities, configured = _results()
    result = apply_candidate_reviews(
        physical,
        identities,
        configured,
        (
            _review(
                physical.assets[0].key,
                CandidateDisposition.REJECT,
            ),
            _review(
                identities.matches[0].key,
                CandidateDisposition.DEFER,
            ),
        ),
    )

    assert result.rejected_candidate_keys == (physical.assets[0].key,)
    assert result.deferred_candidate_keys == (identities.matches[0].key,)
    assert result.unreviewed_candidate_keys == (configured.candidates[0].key,)


def test_unknown_and_duplicate_reviews_are_rejected() -> None:
    physical, identities, configured = _results()
    unknown = _review("unknown", CandidateDisposition.REJECT)
    with pytest.raises(AcceptancePolicyError, match="unknown candidate"):
        apply_candidate_reviews(physical, identities, configured, (unknown,))

    review = _review(physical.assets[0].key, CandidateDisposition.REJECT)
    with pytest.raises(AcceptancePolicyError, match="duplicate review"):
        apply_candidate_reviews(
            physical, identities, configured, (review, review)
        )


def test_acceptance_serialization_is_deterministic() -> None:
    physical, identities, configured = _results()
    review = _review(physical.assets[0].key, CandidateDisposition.DEFER)

    first = acceptance_json(
        apply_candidate_reviews(physical, identities, configured, (review,))
    )
    second = acceptance_json(
        apply_candidate_reviews(physical, identities, configured, (review,))
    )

    assert first == second
    assert first.endswith("\n")
