from datetime import datetime, timezone
import json

import pytest

from twinforge.discovery import (
    CandidateDisposition,
    CandidateReview,
    CorePromotionRecord,
    CorePromotionResult,
    DiscoveryStateFileStore,
    DiscoveryStatePersistenceError,
    DurableIdentityGeneration,
    IdentityLifecycleState,
    TopologyEvidenceReference,
)
from twinforge.model import Device, DeviceType


OBSERVED_AT = datetime(2026, 8, 5, tzinfo=timezone.utc)
PROMOTED_AT = datetime(2026, 8, 6, tzinfo=timezone.utc)


def _state(
    generations: tuple[int, ...] = (1,),
) -> tuple[IdentityLifecycleState, CorePromotionResult]:
    lifecycle_generations: list[DurableIdentityGeneration] = []
    evidence: list[TopologyEvidenceReference] = []
    for number in generations:
        item_evidence = TopologyEvidenceReference(
            protocol="fixture",
            observation_target="192.0.2.130|",
            identifier=f"fixture.generation.{number}",
            description="fixture persisted evidence",
        )
        review = CandidateReview(
            candidate_key=f"candidate:{number}",
            disposition=CandidateDisposition.ACCEPT,
            reviewed_by="operator@example.test",
            reviewed_at=OBSERVED_AT,
            rationale="Accepted for persistence testing.",
            durable_identity_key="identity:controller",
        )
        lifecycle_generations.append(
            DurableIdentityGeneration(
                identity_key="identity:controller",
                generation=number,
                observed_at=OBSERVED_AT,
                candidate_keys=(f"candidate:{number}",),
                target_keys=("192.0.2.130|",),
                acceptance_reviews=(review,),
                evidence=(item_evidence,),
                conflict_overridden=False,
            )
        )
        evidence.append(item_evidence)
    lifecycle = IdentityLifecycleState(generations=tuple(lifecycle_generations))
    promotions = CorePromotionResult(
        records=(
            CorePromotionRecord(
                core_asset=Device(
                    id="asset-controller",
                    name="Controller",
                    device_type=DeviceType.CONTROLLER,
                    manufacturer="Example Corp",
                ),
                durable_identity_key="identity:controller",
                generation_numbers=generations,
                target_keys=("192.0.2.130|",),
                promoted_by="operator@example.test",
                promoted_at=PROMOTED_AT,
                rationale="Approved for persistent inventory.",
                evidence=tuple(evidence),
                acknowledged_conflict_override=False,
            ),
        ),
        unpromoted_identity_keys=(),
    )
    return lifecycle, promotions


def test_round_trips_versioned_lifecycle_and_promotions(tmp_path) -> None:
    store = DiscoveryStateFileStore(tmp_path / "state/discovery.json")
    lifecycle, promotions = _state()

    saved = store.save(
        lifecycle, promotions, expected_revision=0
    )
    loaded = store.load()

    assert saved.revision == 1
    assert loaded.revision == 1
    assert loaded.lifecycle == lifecycle
    assert loaded.promotions.records[0].durable_identity_key == (
        "identity:controller"
    )
    asset = loaded.promotions.records[0].core_asset
    assert isinstance(asset, Device)
    assert asset.device_type is DeviceType.CONTROLLER
    assert json.loads(store.path.read_text(encoding="utf-8"))[
        "schema_version"
    ] == "1.0"
    assert list(store.path.parent.glob("*.tmp")) == []


def test_identical_save_is_idempotent_and_stale_revision_is_rejected(
    tmp_path,
) -> None:
    store = DiscoveryStateFileStore(tmp_path / "discovery.json")
    lifecycle, promotions = _state()
    first = store.save(lifecycle, promotions, expected_revision=0)
    replay = store.save(lifecycle, promotions, expected_revision=1)

    assert replay.revision == first.revision
    with pytest.raises(DiscoveryStatePersistenceError, match="stale"):
        store.save(lifecycle, promotions, expected_revision=0)


def test_forward_generation_update_is_persisted(tmp_path) -> None:
    store = DiscoveryStateFileStore(tmp_path / "discovery.json")
    lifecycle, promotions = _state()
    store.save(lifecycle, promotions, expected_revision=0)
    advanced_lifecycle, advanced_promotions = _state((1, 2))

    saved = store.save(
        advanced_lifecycle,
        advanced_promotions,
        expected_revision=1,
    )

    assert saved.revision == 2
    assert store.load().promotions.records[0].generation_numbers == (1, 2)


def test_history_loss_and_unknown_schema_are_rejected(tmp_path) -> None:
    store = DiscoveryStateFileStore(tmp_path / "discovery.json")
    lifecycle, promotions = _state((1, 2))
    store.save(lifecycle, promotions, expected_revision=0)
    regressed_lifecycle, regressed_promotions = _state((2,))

    with pytest.raises(DiscoveryStatePersistenceError, match="discard lifecycle"):
        store.save(
            regressed_lifecycle,
            regressed_promotions,
            expected_revision=1,
        )

    document = json.loads(store.path.read_text(encoding="utf-8"))
    document["schema_version"] = "99.0"
    store.path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(DiscoveryStatePersistenceError, match="invalid"):
        store.load()
