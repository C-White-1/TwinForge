"""Transactional SQLite adapter for concurrent promotion writers."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from twinforge.discovery import CorePromotionRecord, CorePromotionResult
from twinforge.discovery.topology import TopologyEvidenceReference
from twinforge.model import Asset, Device, DeviceType

from .promotion_repository import (
    InMemoryPromotionRepository,
    PromotionPersistenceResult,
    PromotionRepositoryError,
)


class SqlitePromotionRepository:
    """Serialize promotion batches with a SQLite ``BEGIN IMMEDIATE`` transaction."""

    def __init__(self, path: str | Path, *, timeout_seconds: float = 5.0) -> None:
        self._path = Path(path)
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._timeout_seconds = timeout_seconds
        self._initialize()

    def apply(self, result: CorePromotionResult) -> PromotionPersistenceResult:
        """Validate and commit one batch against the latest locked state."""
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                records = tuple(
                    _record(json.loads(row[0]))
                    for row in connection.execute(
                        "SELECT document FROM promotion ORDER BY asset_id"
                    )
                )
                reference = InMemoryPromotionRepository(initial_records=records)
                outcome = reference.apply(result)
                for record in reference.records():
                    connection.execute(
                        """
                        INSERT INTO promotion(asset_id, identity_key, document)
                        VALUES (?, ?, ?)
                        ON CONFLICT(asset_id) DO UPDATE SET
                            identity_key = excluded.identity_key,
                            document = excluded.document
                        """,
                        (
                            record.core_asset.id,
                            record.durable_identity_key,
                            json.dumps(_record_data(record), sort_keys=True),
                        ),
                    )
                connection.commit()
                return outcome
        except sqlite3.Error as error:
            raise PromotionRepositoryError(
                f"SQLite promotion transaction failed: {error}"
            ) from error

    def get_by_asset_id(self, asset_id: str) -> CorePromotionRecord | None:
        """Read one committed promotion by core asset ID."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT document FROM promotion WHERE asset_id = ?", (asset_id,)
            ).fetchone()
        return _record(json.loads(row[0])) if row is not None else None

    def get_by_identity_key(
        self, durable_identity_key: str
    ) -> CorePromotionRecord | None:
        """Read one committed promotion by durable identity key."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT document FROM promotion WHERE identity_key = ?",
                (durable_identity_key,),
            ).fetchone()
        return _record(json.loads(row[0])) if row is not None else None

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=self._timeout_seconds)

    def _initialize(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self._connect() as connection:
                connection.execute("PRAGMA journal_mode = WAL")
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS promotion (
                        asset_id TEXT PRIMARY KEY,
                        identity_key TEXT NOT NULL UNIQUE,
                        document TEXT NOT NULL
                    )
                    """
                )
        except sqlite3.Error as error:
            raise PromotionRepositoryError(
                f"SQLite promotion repository initialization failed: {error}"
            ) from error


def _record_data(record: CorePromotionRecord) -> dict[str, Any]:
    asset = record.core_asset
    return {
        "asset": {
            "kind": "device" if isinstance(asset, Device) else "asset",
            "id": asset.id,
            "name": asset.name,
            "device_type": asset.device_type.value if isinstance(asset, Device) else None,
            "manufacturer": asset.manufacturer if isinstance(asset, Device) else None,
            "model": asset.model if isinstance(asset, Device) else None,
            "catalog_number": asset.catalog_number if isinstance(asset, Device) else None,
        },
        "durable_identity_key": record.durable_identity_key,
        "generation_numbers": list(record.generation_numbers),
        "target_keys": list(record.target_keys),
        "promoted_by": record.promoted_by,
        "promoted_at": record.promoted_at.isoformat(),
        "rationale": record.rationale,
        "evidence": [
            {
                "protocol": item.protocol,
                "observation_target": item.observation_target,
                "identifier": item.identifier,
                "description": item.description,
            }
            for item in record.evidence
        ],
        "acknowledged_conflict_override": record.acknowledged_conflict_override,
    }


def _record(data: dict[str, Any]) -> CorePromotionRecord:
    asset_data = data["asset"]
    asset = (
        Device(
            id=asset_data["id"],
            name=asset_data["name"],
            device_type=DeviceType(asset_data["device_type"]),
            manufacturer=asset_data["manufacturer"],
            model=asset_data["model"],
            catalog_number=asset_data["catalog_number"],
        )
        if asset_data["kind"] == "device"
        else Asset(id=asset_data["id"], name=asset_data["name"])
    )
    return CorePromotionRecord(
        core_asset=asset,
        durable_identity_key=data["durable_identity_key"],
        generation_numbers=tuple(data["generation_numbers"]),
        target_keys=tuple(data["target_keys"]),
        promoted_by=data["promoted_by"],
        promoted_at=datetime.fromisoformat(data["promoted_at"]),
        rationale=data["rationale"],
        evidence=tuple(TopologyEvidenceReference(**item) for item in data["evidence"]),
        acknowledged_conflict_override=data["acknowledged_conflict_override"],
    )
