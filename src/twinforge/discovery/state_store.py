"""Versioned, atomic file persistence for accepted discovery state."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError

from twinforge.model import Asset, Device, DeviceType

from .acceptance import CandidateDisposition, CandidateReview
from .core_promotion import (
    CorePromotionRecord,
    CorePromotionResult,
    core_promotion_data,
)
from .identity_lifecycle import (
    DurableIdentityGeneration,
    IdentityLifecycleEvent,
    IdentityLifecycleEventType,
    IdentityLifecycleState,
    identity_lifecycle_data,
)
from .topology import TopologyEvidenceReference


STATE_SCHEMA_VERSION = "1.0"


class DiscoveryStatePersistenceError(ValueError):
    """Stored discovery state is invalid, stale, or cannot be persisted."""


class _Document(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class _EvidenceDocument(_Document):
    protocol: str
    observation_target: str
    identifier: str
    description: str


class _ReviewDocument(_Document):
    candidate_key: str
    disposition: CandidateDisposition
    reviewed_by: str
    reviewed_at: AwareDatetime
    rationale: str
    durable_identity_key: str | None
    override_conflict: bool


class _GenerationDocument(_Document):
    identity_key: str
    generation: int = Field(ge=1)
    observed_at: AwareDatetime
    candidate_keys: tuple[str, ...]
    target_keys: tuple[str, ...]
    acceptance_reviews: tuple[_ReviewDocument, ...]
    evidence: tuple[_EvidenceDocument, ...]
    conflict_overridden: bool


class _EventDocument(_Document):
    event_type: IdentityLifecycleEventType
    occurred_at: AwareDatetime
    source_keys: tuple[str, ...]
    target_keys: tuple[str, ...]
    actor: str
    rationale: str


class _LifecycleDocument(_Document):
    active_identity_keys: tuple[str, ...]
    inactive_identity_keys: tuple[str, ...]
    generations: tuple[_GenerationDocument, ...]
    events: tuple[_EventDocument, ...]


class _AssetDocument(_Document):
    id: str
    name: str
    kind: Literal["asset", "device"]
    device_type: DeviceType | None
    manufacturer: str | None
    model: str | None
    catalog_number: str | None


class _PromotionDocument(_Document):
    core_asset: _AssetDocument
    durable_identity_key: str
    generation_numbers: tuple[int, ...]
    target_keys: tuple[str, ...]
    promoted_by: str
    promoted_at: AwareDatetime
    rationale: str
    evidence: tuple[_EvidenceDocument, ...]
    acknowledged_conflict_override: bool


class _PromotionsDocument(_Document):
    records: tuple[_PromotionDocument, ...]
    unpromoted_identity_keys: tuple[str, ...]


class _StateDocument(_Document):
    schema_version: Literal["1.0"]
    revision: int = Field(ge=1)
    lifecycle: _LifecycleDocument
    promotions: _PromotionsDocument


@dataclass(frozen=True)
class PersistedDiscoveryState:
    """Validated state loaded from or ready for one versioned document."""

    revision: int
    lifecycle: IdentityLifecycleState
    promotions: CorePromotionResult


def _evidence(document: _EvidenceDocument) -> TopologyEvidenceReference:
    return TopologyEvidenceReference(
        protocol=document.protocol,
        observation_target=document.observation_target,
        identifier=document.identifier,
        description=document.description,
    )


def _review(document: _ReviewDocument) -> CandidateReview:
    return CandidateReview(
        candidate_key=document.candidate_key,
        disposition=document.disposition,
        reviewed_by=document.reviewed_by,
        reviewed_at=document.reviewed_at,
        rationale=document.rationale,
        durable_identity_key=document.durable_identity_key,
        override_conflict=document.override_conflict,
    )


def _lifecycle(document: _LifecycleDocument) -> IdentityLifecycleState:
    state = IdentityLifecycleState(
        generations=tuple(
            DurableIdentityGeneration(
                identity_key=item.identity_key,
                generation=item.generation,
                observed_at=item.observed_at,
                candidate_keys=item.candidate_keys,
                target_keys=item.target_keys,
                acceptance_reviews=tuple(
                    _review(review) for review in item.acceptance_reviews
                ),
                evidence=tuple(_evidence(value) for value in item.evidence),
                conflict_overridden=item.conflict_overridden,
            )
            for item in document.generations
        ),
        events=tuple(
            IdentityLifecycleEvent(
                event_type=item.event_type,
                occurred_at=item.occurred_at,
                source_keys=item.source_keys,
                target_keys=item.target_keys,
                actor=item.actor,
                rationale=item.rationale,
            )
            for item in document.events
        ),
        inactive_identity_keys=document.inactive_identity_keys,
    )
    if state.active_identity_keys != document.active_identity_keys:
        raise DiscoveryStatePersistenceError(
            "stored active identity keys do not match lifecycle derivation"
        )
    return state


def _asset(document: _AssetDocument) -> Asset:
    if document.kind == "device":
        if document.device_type is None:
            raise DiscoveryStatePersistenceError(
                "stored device is missing its device_type"
            )
        return Device(
            id=document.id,
            name=document.name,
            device_type=document.device_type,
            manufacturer=document.manufacturer,
            model=document.model,
            catalog_number=document.catalog_number,
        )
    if any(
        value is not None
        for value in (
            document.device_type,
            document.manufacturer,
            document.model,
            document.catalog_number,
        )
    ):
        raise DiscoveryStatePersistenceError(
            "stored generic asset contains device-specific fields"
        )
    return Asset(id=document.id, name=document.name)


def _promotions(document: _PromotionsDocument) -> CorePromotionResult:
    return CorePromotionResult(
        records=tuple(
            CorePromotionRecord(
                core_asset=_asset(item.core_asset),
                durable_identity_key=item.durable_identity_key,
                generation_numbers=item.generation_numbers,
                target_keys=item.target_keys,
                promoted_by=item.promoted_by,
                promoted_at=item.promoted_at,
                rationale=item.rationale,
                evidence=tuple(_evidence(value) for value in item.evidence),
                acknowledged_conflict_override=(
                    item.acknowledged_conflict_override
                ),
            )
            for item in document.records
        ),
        unpromoted_identity_keys=document.unpromoted_identity_keys,
    )


def _document_data(
    lifecycle: IdentityLifecycleState,
    promotions: CorePromotionResult,
    revision: int,
) -> dict[str, object]:
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "revision": revision,
        "lifecycle": identity_lifecycle_data(lifecycle),
        "promotions": core_promotion_data(promotions),
    }


def _validate_cross_links(
    lifecycle: IdentityLifecycleState,
    promotions: CorePromotionResult,
) -> None:
    generations_by_identity: dict[str, list[int]] = {}
    for item in lifecycle.generations:
        generations_by_identity.setdefault(item.identity_key, []).append(
            item.generation
        )
    for key, numbers in generations_by_identity.items():
        ordered = sorted(numbers)
        if ordered != list(range(1, len(ordered) + 1)):
            raise DiscoveryStatePersistenceError(
                f"lifecycle generations for {key!r} must be consecutive from 1"
            )

    asset_ids: set[str] = set()
    identity_keys: set[str] = set()
    for record in promotions.records:
        asset_id = record.core_asset.id
        identity_key = record.durable_identity_key
        if asset_id in asset_ids:
            raise DiscoveryStatePersistenceError(
                f"duplicate promoted core asset ID {asset_id!r}"
            )
        if identity_key in identity_keys:
            raise DiscoveryStatePersistenceError(
                f"duplicate promoted durable identity {identity_key!r}"
            )
        asset_ids.add(asset_id)
        identity_keys.add(identity_key)
        available = tuple(sorted(generations_by_identity.get(identity_key, [])))
        if not available:
            raise DiscoveryStatePersistenceError(
                f"promotion {asset_id!r} references unknown lifecycle identity"
            )
        if record.generation_numbers != available[
            : len(record.generation_numbers)
        ]:
            raise DiscoveryStatePersistenceError(
                f"promotion {asset_id!r} generations are not a lifecycle prefix"
            )


def _stable_item(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _validate_forward(
    previous: PersistedDiscoveryState,
    lifecycle: IdentityLifecycleState,
    promotions: CorePromotionResult,
) -> None:
    previous_lifecycle = _document_data(
        previous.lifecycle, previous.promotions, previous.revision
    )["lifecycle"]
    next_lifecycle = _document_data(
        lifecycle, promotions, previous.revision + 1
    )["lifecycle"]
    assert isinstance(previous_lifecycle, dict)
    assert isinstance(next_lifecycle, dict)
    for field in ("generations", "events"):
        old = {_stable_item(item) for item in previous_lifecycle[field]}
        new = {_stable_item(item) for item in next_lifecycle[field]}
        if not old.issubset(new):
            raise DiscoveryStatePersistenceError(
                f"state update would discard lifecycle {field}"
            )
    if not set(previous.lifecycle.inactive_identity_keys).issubset(
        lifecycle.inactive_identity_keys
    ):
        raise DiscoveryStatePersistenceError(
            "state update would reactivate an inactive identity"
        )

    next_by_asset = {item.core_asset.id: item for item in promotions.records}
    for old in previous.promotions.records:
        new = next_by_asset.get(old.core_asset.id)
        if new is None:
            raise DiscoveryStatePersistenceError(
                f"state update would discard promotion {old.core_asset.id!r}"
            )
        if old.durable_identity_key != new.durable_identity_key:
            raise DiscoveryStatePersistenceError(
                f"state update would rebind promotion {old.core_asset.id!r}"
            )
        if old.generation_numbers != new.generation_numbers[
            : len(old.generation_numbers)
        ]:
            raise DiscoveryStatePersistenceError(
                f"state update would regress promotion {old.core_asset.id!r}"
            )


class DiscoveryStateFileStore:
    """Persist one versioned state document using atomic file replacement."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> PersistedDiscoveryState:
        """Load and validate the document, or return empty revision zero."""
        if not self.path.exists():
            return PersistedDiscoveryState(
                revision=0,
                lifecycle=IdentityLifecycleState(),
                promotions=CorePromotionResult(
                    records=(), unpromoted_identity_keys=()
                ),
            )
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            document = _StateDocument.model_validate(raw)
            lifecycle = _lifecycle(document.lifecycle)
            promotions = _promotions(document.promotions)
            _validate_cross_links(lifecycle, promotions)
            return PersistedDiscoveryState(
                revision=document.revision,
                lifecycle=lifecycle,
                promotions=promotions,
            )
        except (
            OSError,
            json.JSONDecodeError,
            ValidationError,
            TypeError,
            ValueError,
        ) as error:
            if isinstance(error, DiscoveryStatePersistenceError):
                raise
            raise DiscoveryStatePersistenceError(
                f"invalid discovery state document {self.path}: {error}"
            ) from error

    def save(
        self,
        lifecycle: IdentityLifecycleState,
        promotions: CorePromotionResult,
        *,
        expected_revision: int,
    ) -> PersistedDiscoveryState:
        """Validate forward history and atomically replace the document."""
        current = self.load()
        if current.revision != expected_revision:
            raise DiscoveryStatePersistenceError(
                "stale discovery state revision: "
                f"expected {expected_revision}, found {current.revision}"
            )
        _validate_forward(current, lifecycle, promotions)
        _validate_cross_links(lifecycle, promotions)
        next_revision = current.revision + 1
        data = _document_data(lifecycle, promotions, next_revision)
        try:
            _StateDocument.model_validate(data)
        except ValidationError as error:
            raise DiscoveryStatePersistenceError(
                f"discovery state cannot be serialized: {error}"
            ) from error
        if current.revision > 0:
            current_data = _document_data(
                current.lifecycle, current.promotions, current.revision
            )
            comparable = dict(data)
            comparable["revision"] = current.revision
            if comparable == current_data:
                return current
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as stream:
                temporary = Path(stream.name)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        except OSError as error:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            raise DiscoveryStatePersistenceError(
                f"could not persist discovery state {self.path}: {error}"
            ) from error
        return PersistedDiscoveryState(
            revision=next_revision,
            lifecycle=lifecycle,
            promotions=promotions,
        )
