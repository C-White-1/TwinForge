from datetime import datetime, timezone

import pytest

from twinforge.assembly import (
    PromotionPersistenceStatus,
    PromotionRepositoryError,
    SqlitePromotionRepository,
    persist_promotions,
)
from twinforge.discovery import CorePromotionRecord, CorePromotionResult
from twinforge.model import Device, DeviceType


NOW = datetime(2026, 8, 9, tzinfo=timezone.utc)


def _record(
    asset_id: str = "controller-1",
    identity_key: str = "identity:1",
    generations: tuple[int, ...] = (1,),
) -> CorePromotionRecord:
    return CorePromotionRecord(
        core_asset=Device(
            id=asset_id,
            name="Controller",
            device_type=DeviceType.CONTROLLER,
            manufacturer="Example",
            model="Test",
        ),
        durable_identity_key=identity_key,
        generation_numbers=generations,
        target_keys=("192.168.1.10|",),
        promoted_by="lab.operator",
        promoted_at=NOW,
        rationale="Approved laboratory identity",
        evidence=(),
        acknowledged_conflict_override=False,
    )


def _result(*records: CorePromotionRecord) -> CorePromotionResult:
    return CorePromotionResult(records=records, unpromoted_identity_keys=())


def test_independent_repository_instances_observe_committed_state(tmp_path) -> None:
    path = tmp_path / "promotions.sqlite3"
    writer_one = SqlitePromotionRepository(path)
    writer_two = SqlitePromotionRepository(path)

    created = persist_promotions(_result(_record()), writer_one)
    replay = persist_promotions(_result(_record()), writer_two)

    assert created.items[0].status is PromotionPersistenceStatus.CREATED
    assert replay.items[0].status is PromotionPersistenceStatus.UNCHANGED
    stored = writer_two.get_by_identity_key("identity:1")
    assert stored is not None
    assert stored.core_asset.id == "controller-1"


def test_second_writer_can_only_advance_generation_history(tmp_path) -> None:
    path = tmp_path / "promotions.sqlite3"
    first = SqlitePromotionRepository(path)
    second = SqlitePromotionRepository(path)
    persist_promotions(_result(_record(generations=(1,))), first)

    updated = persist_promotions(_result(_record(generations=(1, 2))), second)

    assert updated.items[0].status is PromotionPersistenceStatus.UPDATED
    assert first.get_by_asset_id("controller-1").generation_numbers == (1, 2)  # type: ignore[union-attr]


def test_conflicting_batch_rolls_back_without_partial_rows(tmp_path) -> None:
    repository = SqlitePromotionRepository(tmp_path / "promotions.sqlite3")
    persist_promotions(_result(_record()), repository)

    with pytest.raises(PromotionRepositoryError, match="already linked"):
        persist_promotions(
            _result(
                _record("controller-2", "identity:2"),
                _record("controller-3", "identity:1"),
            ),
            repository,
        )

    assert repository.get_by_asset_id("controller-2") is None
    assert repository.get_by_asset_id("controller-3") is None


def test_identity_uniqueness_survives_repository_reopen(tmp_path) -> None:
    path = tmp_path / "promotions.sqlite3"
    persist_promotions(_result(_record()), SqlitePromotionRepository(path))

    with pytest.raises(PromotionRepositoryError, match="already linked"):
        persist_promotions(
            _result(_record("controller-2", "identity:1")),
            SqlitePromotionRepository(path),
        )
