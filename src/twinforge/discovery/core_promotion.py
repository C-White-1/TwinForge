"""Explicit promotion of lifecycle identities into vendor-neutral core assets."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from twinforge.model import Asset, Device, DeviceType

from .identity_lifecycle import (
    DurableIdentityGeneration,
    IdentityLifecycleState,
)
from .topology import TopologyEvidenceReference


class CoreAssetKind(str, Enum):
    """Core types that can currently be created without inventing structure."""

    ASSET = "asset"
    DEVICE = "device"


class CorePromotionError(ValueError):
    """A requested promotion violates the explicit promotion policy."""


@dataclass(frozen=True)
class CorePromotionRequest:
    """Operator-supplied mapping from one active identity to one core asset."""

    durable_identity_key: str
    core_asset_id: str
    name: str
    asset_kind: CoreAssetKind
    promoted_by: str
    promoted_at: datetime
    rationale: str
    device_type: DeviceType | None = None
    manufacturer: str | None = None
    model: str | None = None
    catalog_number: str | None = None
    acknowledge_conflict_override: bool = False


@dataclass(frozen=True)
class CorePromotionRecord:
    """Reversible link between a core object and lifecycle evidence."""

    core_asset: Asset
    durable_identity_key: str
    generation_numbers: tuple[int, ...]
    target_keys: tuple[str, ...]
    promoted_by: str
    promoted_at: datetime
    rationale: str
    evidence: tuple[TopologyEvidenceReference, ...]
    acknowledged_conflict_override: bool


@dataclass(frozen=True)
class CorePromotionResult:
    """Promotions plus active lifecycle identities left unpromoted."""

    records: tuple[CorePromotionRecord, ...]
    unpromoted_identity_keys: tuple[str, ...]


def _validate_text(value: str, field: str) -> None:
    if not value.strip():
        raise CorePromotionError(f"{field} must not be blank")
    if value != value.strip():
        raise CorePromotionError(f"{field} must be trimmed")


def _validate_request(
    request: CorePromotionRequest,
    generations: tuple[DurableIdentityGeneration, ...],
) -> None:
    _validate_text(request.durable_identity_key, "durable_identity_key")
    _validate_text(request.core_asset_id, "core_asset_id")
    _validate_text(request.name, "name")
    _validate_text(request.promoted_by, "promoted_by")
    _validate_text(request.rationale, "rationale")
    if request.promoted_at.tzinfo is None:
        raise CorePromotionError("promoted_at must include a timezone")
    if request.promoted_at < max(item.observed_at for item in generations):
        raise CorePromotionError("promotion cannot predate its latest generation")
    conflict_overridden = any(item.conflict_overridden for item in generations)
    if conflict_overridden and not request.acknowledge_conflict_override:
        raise CorePromotionError(
            "promotion must acknowledge the accepted conflict override"
        )
    if request.asset_kind is CoreAssetKind.ASSET:
        device_values = (
            request.device_type,
            request.manufacturer,
            request.model,
            request.catalog_number,
        )
        if any(value is not None for value in device_values):
            raise CorePromotionError(
                "device fields are valid only when asset_kind is device"
            )


def _build_asset(request: CorePromotionRequest) -> Asset:
    if request.asset_kind is CoreAssetKind.DEVICE:
        return Device(
            id=request.core_asset_id,
            name=request.name,
            device_type=request.device_type or DeviceType.UNKNOWN,
            manufacturer=request.manufacturer,
            model=request.model,
            catalog_number=request.catalog_number,
        )
    return Asset(id=request.core_asset_id, name=request.name)


def _evidence_key(
    evidence: TopologyEvidenceReference,
) -> tuple[str, str, str, str]:
    return (
        evidence.protocol,
        evidence.observation_target,
        evidence.identifier,
        evidence.description,
    )


def promote_lifecycle_identities(
    state: IdentityLifecycleState,
    requests: tuple[CorePromotionRequest, ...],
) -> CorePromotionResult:
    """Create core assets only from explicitly requested active identities."""
    active = set(state.active_identity_keys)
    generations_by_identity: dict[str, list[DurableIdentityGeneration]] = {}
    for generation in state.generations:
        generations_by_identity.setdefault(generation.identity_key, []).append(
            generation
        )

    requested_identities: set[str] = set()
    requested_asset_ids: set[str] = set()
    records: list[CorePromotionRecord] = []
    for request in requests:
        if request.durable_identity_key not in active:
            raise CorePromotionError(
                f"identity {request.durable_identity_key!r} is not active"
            )
        if request.durable_identity_key in requested_identities:
            raise CorePromotionError(
                f"duplicate promotion for {request.durable_identity_key!r}"
            )
        if request.core_asset_id in requested_asset_ids:
            raise CorePromotionError(
                f"duplicate core asset ID {request.core_asset_id!r}"
            )
        generations = tuple(
            sorted(
                generations_by_identity[request.durable_identity_key],
                key=lambda item: item.generation,
            )
        )
        _validate_request(request, generations)
        requested_identities.add(request.durable_identity_key)
        requested_asset_ids.add(request.core_asset_id)
        evidence_by_key = {
            _evidence_key(item): item
            for generation in generations
            for item in generation.evidence
        }
        records.append(
            CorePromotionRecord(
                core_asset=_build_asset(request),
                durable_identity_key=request.durable_identity_key,
                generation_numbers=tuple(
                    item.generation for item in generations
                ),
                target_keys=tuple(
                    sorted(
                        {
                            target
                            for generation in generations
                            for target in generation.target_keys
                        }
                    )
                ),
                promoted_by=request.promoted_by,
                promoted_at=request.promoted_at,
                rationale=request.rationale,
                evidence=tuple(
                    evidence_by_key[key] for key in sorted(evidence_by_key)
                ),
                acknowledged_conflict_override=(
                    request.acknowledge_conflict_override
                ),
            )
        )

    return CorePromotionResult(
        records=tuple(sorted(records, key=lambda item: item.core_asset.id)),
        unpromoted_identity_keys=tuple(sorted(active - requested_identities)),
    )


def durable_identity_for_asset(
    result: CorePromotionResult,
    core_asset_id: str,
) -> str | None:
    """Resolve the lifecycle identity behind a promoted core asset."""
    return next(
        (
            item.durable_identity_key
            for item in result.records
            if item.core_asset.id == core_asset_id
        ),
        None,
    )


def core_promotion_data(result: CorePromotionResult) -> dict[str, Any]:
    """Return stable promotion data without serializing arbitrary object state."""
    return {
        "records": [
            {
                "core_asset": {
                    "id": item.core_asset.id,
                    "name": item.core_asset.name,
                    "kind": (
                        CoreAssetKind.DEVICE.value
                        if isinstance(item.core_asset, Device)
                        else CoreAssetKind.ASSET.value
                    ),
                    "device_type": (
                        item.core_asset.device_type.value
                        if isinstance(item.core_asset, Device)
                        else None
                    ),
                    "manufacturer": (
                        item.core_asset.manufacturer
                        if isinstance(item.core_asset, Device)
                        else None
                    ),
                    "model": (
                        item.core_asset.model
                        if isinstance(item.core_asset, Device)
                        else None
                    ),
                    "catalog_number": (
                        item.core_asset.catalog_number
                        if isinstance(item.core_asset, Device)
                        else None
                    ),
                },
                "durable_identity_key": item.durable_identity_key,
                "generation_numbers": list(item.generation_numbers),
                "target_keys": list(item.target_keys),
                "promoted_by": item.promoted_by,
                "promoted_at": item.promoted_at.isoformat(),
                "rationale": item.rationale,
                "evidence": [
                    {
                        "protocol": evidence.protocol,
                        "observation_target": evidence.observation_target,
                        "identifier": evidence.identifier,
                        "description": evidence.description,
                    }
                    for evidence in item.evidence
                ],
                "acknowledged_conflict_override": (
                    item.acknowledged_conflict_override
                ),
            }
            for item in result.records
        ],
        "unpromoted_identity_keys": list(result.unpromoted_identity_keys),
    }


def core_promotion_json(result: CorePromotionResult) -> str:
    """Serialize core promotion records deterministically."""
    return json.dumps(
        core_promotion_data(result), indent=2, ensure_ascii=False
    ) + "\n"
