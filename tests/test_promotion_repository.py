from datetime import datetime, timezone

import pytest

from twinforge.assembly import (
    InMemoryPromotionRepository,
    PromotionPersistenceStatus,
    PromotionRepositoryError,
    persist_promotions,
)
from twinforge.discovery import CorePromotionRecord, CorePromotionResult
from twinforge.model import Asset, Device, DeviceType, Plant


PROMOTED_AT = datetime(2026, 8, 6, tzinfo=timezone.utc)


def _record(
    *,
    asset_id: str = "asset-1",
    identity_key: str = "identity:1",
    generations: tuple[int, ...] = (1,),
    name: str = "Controller",
) -> CorePromotionRecord:
    return CorePromotionRecord(
        core_asset=Device(
            id=asset_id,
            name=name,
            device_type=DeviceType.CONTROLLER,
        ),
        durable_identity_key=identity_key,
        generation_numbers=generations,
        target_keys=("192.0.2.120|",),
        promoted_by="operator@example.test",
        promoted_at=PROMOTED_AT,
        rationale="Approved for the plant asset inventory.",
        evidence=(),
        acknowledged_conflict_override=False,
    )


def _result(*records: CorePromotionRecord) -> CorePromotionResult:
    return CorePromotionResult(records=records, unpromoted_identity_keys=())


def test_creates_plant_asset_and_supports_reverse_repository_lookup() -> None:
    plant = Plant(id="plant-1", name="Laboratory")
    repository = InMemoryPromotionRepository(plant)
    record = _record()

    result = persist_promotions(_result(record), repository)

    assert result.items[0].status is PromotionPersistenceStatus.CREATED
    assert plant.assets == [record.core_asset]
    assert record.core_asset.parent is plant
    assert repository.get_by_asset_id("asset-1") is record
    assert repository.get_by_identity_key("identity:1") is record


def test_identical_replay_is_idempotent_and_does_not_duplicate_plant_asset() -> None:
    plant = Plant(id="plant-1", name="Laboratory")
    repository = InMemoryPromotionRepository(plant)
    record = _record()
    persist_promotions(_result(record), repository)

    replay = persist_promotions(_result(_record()), repository)

    assert replay.items[0].status is PromotionPersistenceStatus.UNCHANGED
    assert len(plant.assets) == 1


def test_forward_generation_update_replaces_evidence_record_not_core_asset() -> None:
    plant = Plant(id="plant-1", name="Laboratory")
    repository = InMemoryPromotionRepository(plant)
    original = _record()
    persist_promotions(_result(original), repository)

    advanced = _record(generations=(1, 2))
    result = persist_promotions(_result(advanced), repository)

    assert result.items[0].status is PromotionPersistenceStatus.UPDATED
    stored = repository.get_by_asset_id("asset-1")
    assert stored is not None
    assert stored.generation_numbers == (1, 2)
    assert stored.core_asset is original.core_asset
    assert plant.assets == [original.core_asset]


def test_rejects_existing_plant_id_and_identity_rebinding() -> None:
    plant = Plant(id="plant-1", name="Laboratory")
    plant.add_asset(Asset(id="asset-1", name="Existing"))
    repository = InMemoryPromotionRepository(plant)
    with pytest.raises(PromotionRepositoryError, match="already exists"):
        persist_promotions(_result(_record()), repository)

    repository = InMemoryPromotionRepository()
    persist_promotions(_result(_record()), repository)
    with pytest.raises(PromotionRepositoryError, match="already linked"):
        persist_promotions(
            _result(_record(asset_id="asset-2", identity_key="identity:1")),
            repository,
        )


def test_batch_validation_is_atomic_when_a_later_record_conflicts() -> None:
    plant = Plant(id="plant-1", name="Laboratory")
    plant.add_asset(Asset(id="collision", name="Existing"))
    repository = InMemoryPromotionRepository(plant)

    with pytest.raises(PromotionRepositoryError, match="already exists"):
        persist_promotions(
            _result(
                _record(asset_id="new-asset", identity_key="identity:new"),
                _record(asset_id="collision", identity_key="identity:collision"),
            ),
            repository,
        )

    assert repository.get_by_asset_id("new-asset") is None
    assert [asset.id for asset in plant.assets] == ["collision"]
