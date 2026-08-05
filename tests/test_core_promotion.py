from datetime import datetime, timezone

import pytest

from twinforge.discovery import (
    CandidateDisposition,
    CandidateReview,
    CoreAssetKind,
    CorePromotionError,
    CorePromotionRequest,
    DurableIdentityGeneration,
    IdentityLifecycleState,
    TopologyEvidenceReference,
    core_promotion_json,
    durable_identity_for_asset,
    promote_lifecycle_identities,
)
from twinforge.model import Asset, Device, DeviceType


OBSERVED_AT = datetime(2026, 8, 5, tzinfo=timezone.utc)
PROMOTED_AT = datetime(2026, 8, 6, tzinfo=timezone.utc)


def _state(*, conflict_overridden: bool = False) -> IdentityLifecycleState:
    review = CandidateReview(
        candidate_key="candidate:controller",
        disposition=CandidateDisposition.ACCEPT,
        reviewed_by="reviewer@example.test",
        reviewed_at=OBSERVED_AT,
        rationale="Accepted after authorized evidence review.",
        durable_identity_key="identity:controller-1",
        override_conflict=conflict_overridden,
    )
    return IdentityLifecycleState(
        generations=(
            DurableIdentityGeneration(
                identity_key="identity:controller-1",
                generation=1,
                observed_at=OBSERVED_AT,
                candidate_keys=("candidate:controller",),
                target_keys=("192.0.2.110|",),
                acceptance_reviews=(review,),
                evidence=(
                    TopologyEvidenceReference(
                        protocol="fixture",
                        observation_target="192.0.2.110|",
                        identifier="fixture.controller",
                        description="fixture promotion evidence",
                    ),
                ),
                conflict_overridden=conflict_overridden,
            ),
        ),
    )


def _request(**overrides: object) -> CorePromotionRequest:
    values: dict[str, object] = {
        "durable_identity_key": "identity:controller-1",
        "core_asset_id": "asset-controller-1",
        "name": "Laboratory Controller",
        "asset_kind": CoreAssetKind.DEVICE,
        "device_type": DeviceType.CONTROLLER,
        "manufacturer": "Example Corp",
        "model": "EX-1",
        "catalog_number": "EX-1-C",
        "promoted_by": "operator@example.test",
        "promoted_at": PROMOTED_AT,
        "rationale": "Approved for the maintained asset inventory.",
    }
    values.update(overrides)
    return CorePromotionRequest(**values)  # type: ignore[arg-type]


def test_promotes_active_identity_to_explicit_vendor_neutral_device() -> None:
    state = _state()
    result = promote_lifecycle_identities(state, (_request(),))

    assert len(result.records) == 1
    record = result.records[0]
    assert isinstance(record.core_asset, Device)
    assert record.core_asset.id == "asset-controller-1"
    assert record.core_asset.device_type is DeviceType.CONTROLLER
    assert record.durable_identity_key == "identity:controller-1"
    assert record.generation_numbers == (1,)
    assert record.target_keys == ("192.0.2.110|",)
    assert result.unpromoted_identity_keys == ()
    assert (
        durable_identity_for_asset(result, "asset-controller-1")
        == "identity:controller-1"
    )


def test_generic_asset_rejects_device_specific_fields() -> None:
    request = _request(
        asset_kind=CoreAssetKind.ASSET,
        device_type=DeviceType.CONTROLLER,
    )
    with pytest.raises(CorePromotionError, match="device fields"):
        promote_lifecycle_identities(_state(), (request,))


def test_conflict_override_requires_promotion_acknowledgement() -> None:
    with pytest.raises(CorePromotionError, match="acknowledge"):
        promote_lifecycle_identities(_state(conflict_overridden=True), (_request(),))

    result = promote_lifecycle_identities(
        _state(conflict_overridden=True),
        (_request(acknowledge_conflict_override=True),),
    )
    assert result.records[0].acknowledged_conflict_override is True


def test_inactive_identity_and_predated_promotion_are_rejected() -> None:
    inactive = IdentityLifecycleState(
        generations=_state().generations,
        inactive_identity_keys=("identity:controller-1",),
    )
    with pytest.raises(CorePromotionError, match="not active"):
        promote_lifecycle_identities(inactive, (_request(),))

    with pytest.raises(CorePromotionError, match="cannot predate"):
        promote_lifecycle_identities(
            _state(),
            (_request(promoted_at=datetime(2026, 8, 4, tzinfo=timezone.utc)),),
        )


def test_promotion_serialization_is_deterministic() -> None:
    result = promote_lifecycle_identities(_state(), (_request(),))

    assert core_promotion_json(result) == core_promotion_json(result)
    assert core_promotion_json(result).endswith("\n")
    assert isinstance(result.records[0].core_asset, Asset)
