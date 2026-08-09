"""Atomic repository boundary for approved core-asset promotions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Protocol

from twinforge.discovery import CorePromotionRecord, CorePromotionResult
from twinforge.model import Asset, Device, Plant


class PromotionPersistenceStatus(str, Enum):
    """Outcome of applying one promotion record to a repository."""

    CREATED = "created"
    UPDATED = "updated"
    UNCHANGED = "unchanged"


class PromotionRepositoryError(ValueError):
    """A promotion conflicts with durable repository state."""


@dataclass(frozen=True)
class PromotionPersistenceItem:
    """Persistence outcome for one core asset and lifecycle identity."""

    core_asset_id: str
    durable_identity_key: str
    status: PromotionPersistenceStatus


@dataclass(frozen=True)
class PromotionPersistenceResult:
    """Deterministically ordered results from one atomic repository operation."""

    items: tuple[PromotionPersistenceItem, ...]


class PromotionRepository(Protocol):
    """Atomic persistence port implemented by memory or database adapters."""

    def apply(self, result: CorePromotionResult) -> PromotionPersistenceResult:
        """Validate and persist one complete promotion batch atomically."""
        ...


def _asset_signature(asset: Asset) -> tuple[object, ...]:
    if isinstance(asset, Device):
        return (
            "device",
            asset.id,
            asset.name,
            asset.device_type.value,
            asset.manufacturer,
            asset.model,
            asset.catalog_number,
        )
    return ("asset", asset.id, asset.name)


def _evidence_keys(record: CorePromotionRecord) -> set[tuple[str, str, str, str]]:
    return {
        (
            item.protocol,
            item.observation_target,
            item.identifier,
            item.description,
        )
        for item in record.evidence
    }


def _is_prefix(previous: tuple[int, ...], current: tuple[int, ...]) -> bool:
    return len(previous) <= len(current) and current[: len(previous)] == previous


class InMemoryPromotionRepository:
    """Atomic reference repository optionally backed by a ``Plant`` asset list.

    The adapter is useful for tests and in-process applications. A database
    adapter can implement the same collision and forward-generation rules in a
    transaction without changing discovery or core-model classes.
    """

    def __init__(
        self,
        plant: Plant | None = None,
        *,
        initial_records: tuple[CorePromotionRecord, ...] = (),
    ) -> None:
        self._plant = plant
        self._by_asset_id: dict[str, CorePromotionRecord] = {
            record.core_asset.id: record for record in initial_records
        }
        self._asset_id_by_identity: dict[str, str] = {
            record.durable_identity_key: record.core_asset.id
            for record in initial_records
        }
        if len(self._by_asset_id) != len(initial_records):
            raise PromotionRepositoryError("initial records contain duplicate assets")
        if len(self._asset_id_by_identity) != len(initial_records):
            raise PromotionRepositoryError(
                "initial records contain duplicate durable identities"
            )

    def records(self) -> tuple[CorePromotionRecord, ...]:
        """Return the complete deterministic repository state."""
        return tuple(self._by_asset_id[key] for key in sorted(self._by_asset_id))

    def get_by_asset_id(self, asset_id: str) -> CorePromotionRecord | None:
        """Return the retained promotion record for a core asset ID."""
        return self._by_asset_id.get(asset_id)

    def get_by_identity_key(
        self, durable_identity_key: str
    ) -> CorePromotionRecord | None:
        """Return the retained promotion record for a lifecycle identity."""
        asset_id = self._asset_id_by_identity.get(durable_identity_key)
        return self._by_asset_id.get(asset_id) if asset_id is not None else None

    def apply(self, result: CorePromotionResult) -> PromotionPersistenceResult:
        """Validate the complete batch, then create or advance records atomically."""
        planned: list[
            tuple[CorePromotionRecord, PromotionPersistenceStatus]
        ] = []
        batch_asset_ids: set[str] = set()
        batch_identity_keys: set[str] = set()

        for record in result.records:
            asset_id = record.core_asset.id
            identity_key = record.durable_identity_key
            if asset_id in batch_asset_ids:
                raise PromotionRepositoryError(
                    f"duplicate core asset ID in batch: {asset_id!r}"
                )
            if identity_key in batch_identity_keys:
                raise PromotionRepositoryError(
                    f"duplicate durable identity in batch: {identity_key!r}"
                )
            batch_asset_ids.add(asset_id)
            batch_identity_keys.add(identity_key)

            identity_asset_id = self._asset_id_by_identity.get(identity_key)
            if identity_asset_id is not None and identity_asset_id != asset_id:
                raise PromotionRepositoryError(
                    f"identity {identity_key!r} is already linked to "
                    f"asset {identity_asset_id!r}"
                )
            existing = self._by_asset_id.get(asset_id)
            if existing is None:
                self._validate_new_asset_id(asset_id)
                planned.append((record, PromotionPersistenceStatus.CREATED))
                continue
            if existing.durable_identity_key != identity_key:
                raise PromotionRepositoryError(
                    f"asset {asset_id!r} is already linked to identity "
                    f"{existing.durable_identity_key!r}"
                )
            if _asset_signature(existing.core_asset) != _asset_signature(
                record.core_asset
            ):
                raise PromotionRepositoryError(
                    f"asset {asset_id!r} core fields differ from stored promotion"
                )
            if not _is_prefix(
                existing.generation_numbers, record.generation_numbers
            ):
                raise PromotionRepositoryError(
                    f"asset {asset_id!r} generations do not advance stored history"
                )
            if not _evidence_keys(existing).issubset(_evidence_keys(record)):
                raise PromotionRepositoryError(
                    f"asset {asset_id!r} update would discard retained evidence"
                )
            status = (
                PromotionPersistenceStatus.UNCHANGED
                if existing.generation_numbers == record.generation_numbers
                else PromotionPersistenceStatus.UPDATED
            )
            planned.append(
                (
                    replace(record, core_asset=existing.core_asset),
                    status,
                )
            )

        for record, status in planned:
            if status is PromotionPersistenceStatus.UNCHANGED:
                continue
            asset_id = record.core_asset.id
            self._by_asset_id[asset_id] = record
            self._asset_id_by_identity[record.durable_identity_key] = asset_id
            if status is PromotionPersistenceStatus.CREATED and self._plant is not None:
                self._plant.add_asset(record.core_asset)

        return PromotionPersistenceResult(
            items=tuple(
                sorted(
                    (
                        PromotionPersistenceItem(
                            core_asset_id=record.core_asset.id,
                            durable_identity_key=record.durable_identity_key,
                            status=status,
                        )
                        for record, status in planned
                    ),
                    key=lambda item: item.core_asset_id,
                )
            )
        )

    def _validate_new_asset_id(self, asset_id: str) -> None:
        if self._plant is None:
            return
        existing_ids = {
            asset.id
            for asset in (
                *self._plant.assets,
                *self._plant.controllers,
                *self._plant.networks,
            )
        }
        if asset_id in existing_ids:
            raise PromotionRepositoryError(
                f"core asset ID {asset_id!r} already exists in the plant"
            )


def persist_promotions(
    result: CorePromotionResult,
    repository: PromotionRepository,
) -> PromotionPersistenceResult:
    """Apply promotions through the repository's atomic policy boundary."""
    return repository.apply(result)
