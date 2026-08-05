"""Event-driven lifecycle for accepted discovery staging identities."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from .acceptance import AcceptanceResult, AcceptedIdentityRecord, CandidateReview
from .topology import TopologyEvidenceReference


class IdentityTransition(str, Enum):
    """Operator-directed relationship between durable staging identities."""

    SUPERSEDE = "supersede"
    MERGE = "merge"
    SPLIT = "split"


class IdentityLifecycleEventType(str, Enum):
    """Immutable event types recorded in the lifecycle ledger."""

    CREATED = "created"
    OBSERVED = "observed"
    SUPERSEDED = "superseded"
    MERGED = "merged"
    SPLIT = "split"


class IdentityLifecycleError(ValueError):
    """A proposed lifecycle change violates explicit transition rules."""


@dataclass(frozen=True)
class IdentityTransitionDirective:
    """Attributable operator instruction for a non-observation transition."""

    transition: IdentityTransition
    source_keys: tuple[str, ...]
    target_keys: tuple[str, ...]
    directed_by: str
    directed_at: datetime
    rationale: str


@dataclass(frozen=True)
class DurableIdentityGeneration:
    """One accepted observation generation of a durable staging identity."""

    identity_key: str
    generation: int
    observed_at: datetime
    candidate_keys: tuple[str, ...]
    target_keys: tuple[str, ...]
    acceptance_reviews: tuple[CandidateReview, ...]
    evidence: tuple[TopologyEvidenceReference, ...]
    conflict_overridden: bool


@dataclass(frozen=True)
class IdentityLifecycleEvent:
    """One immutable creation, observation, or operator transition event."""

    event_type: IdentityLifecycleEventType
    occurred_at: datetime
    source_keys: tuple[str, ...]
    target_keys: tuple[str, ...]
    actor: str
    rationale: str


@dataclass(frozen=True)
class IdentityLifecycleState:
    """Append-only generations and events with an explicit active-key view."""

    generations: tuple[DurableIdentityGeneration, ...] = ()
    events: tuple[IdentityLifecycleEvent, ...] = ()
    inactive_identity_keys: tuple[str, ...] = ()

    @property
    def active_identity_keys(self) -> tuple[str, ...]:
        """Return identities observed at least once and not transitioned out."""
        observed = {item.identity_key for item in self.generations}
        return tuple(sorted(observed - set(self.inactive_identity_keys)))


def _review_time(record: AcceptedIdentityRecord) -> datetime:
    if not record.reviews:
        raise IdentityLifecycleError(
            f"accepted identity {record.key!r} has no review timestamp"
        )
    times = [review.reviewed_at for review in record.reviews]
    if any(item.tzinfo is None for item in times):
        raise IdentityLifecycleError("accepted review timestamps must be timezone-aware")
    return max(times)


def _generation(
    record: AcceptedIdentityRecord,
    generation: int,
) -> DurableIdentityGeneration:
    return DurableIdentityGeneration(
        identity_key=record.key,
        generation=generation,
        observed_at=_review_time(record),
        candidate_keys=record.candidate_keys,
        target_keys=record.target_keys,
        acceptance_reviews=record.reviews,
        evidence=record.evidence,
        conflict_overridden=record.conflict_overridden,
    )


def _validate_text(value: str, field: str) -> None:
    if not value.strip():
        raise IdentityLifecycleError(f"{field} must not be blank")
    if value != value.strip():
        raise IdentityLifecycleError(f"{field} must be trimmed")


def _validate_directive(directive: IdentityTransitionDirective) -> None:
    if directive.directed_at.tzinfo is None:
        raise IdentityLifecycleError("directed_at must include a timezone")
    _validate_text(directive.directed_by, "directed_by")
    _validate_text(directive.rationale, "rationale")
    if len(set(directive.source_keys)) != len(directive.source_keys):
        raise IdentityLifecycleError("transition source keys must be unique")
    if len(set(directive.target_keys)) != len(directive.target_keys):
        raise IdentityLifecycleError("transition target keys must be unique")
    if set(directive.source_keys) & set(directive.target_keys):
        raise IdentityLifecycleError("transition sources and targets must not overlap")
    expected = {
        IdentityTransition.SUPERSEDE: (1, 1),
        IdentityTransition.MERGE: (2, 1),
        IdentityTransition.SPLIT: (1, 2),
    }[directive.transition]
    if len(directive.source_keys) < expected[0]:
        raise IdentityLifecycleError(
            f"{directive.transition.value} requires at least {expected[0]} source(s)"
        )
    if len(directive.target_keys) < expected[1]:
        raise IdentityLifecycleError(
            f"{directive.transition.value} requires at least {expected[1]} target(s)"
        )
    if directive.transition is IdentityTransition.SUPERSEDE and (
        len(directive.source_keys) != 1 or len(directive.target_keys) != 1
    ):
        raise IdentityLifecycleError("supersede requires exactly one source and target")
    if directive.transition is IdentityTransition.MERGE and len(
        directive.target_keys
    ) != 1:
        raise IdentityLifecycleError("merge requires exactly one target")
    if directive.transition is IdentityTransition.SPLIT and len(
        directive.source_keys
    ) != 1:
        raise IdentityLifecycleError("split requires exactly one source")


def advance_identity_lifecycle(
    previous: IdentityLifecycleState,
    acceptance: AcceptanceResult,
    directives: tuple[IdentityTransitionDirective, ...] = (),
) -> IdentityLifecycleState:
    """Append accepted observations and explicit lifecycle transitions."""
    accepted = {item.key: item for item in acceptance.accepted_identities}
    if len(accepted) != len(acceptance.accepted_identities):
        raise IdentityLifecycleError("accepted identity keys must be unique")

    generations = list(previous.generations)
    events = list(previous.events)
    inactive = set(previous.inactive_identity_keys)
    known_generations: dict[str, int] = {}
    for item in generations:
        known_generations[item.identity_key] = max(
            known_generations.get(item.identity_key, 0), item.generation
        )

    for key in sorted(accepted):
        if key in inactive:
            raise IdentityLifecycleError(
                f"inactive identity {key!r} cannot be observed again under the same key"
            )
        record = accepted[key]
        number = known_generations.get(key, 0) + 1
        generation = _generation(record, number)
        generations.append(generation)
        known_generations[key] = number
        created = number == 1
        events.append(
            IdentityLifecycleEvent(
                event_type=(
                    IdentityLifecycleEventType.CREATED
                    if created
                    else IdentityLifecycleEventType.OBSERVED
                ),
                occurred_at=generation.observed_at,
                source_keys=(),
                target_keys=(key,),
                actor=", ".join(
                    sorted({review.reviewed_by for review in record.reviews})
                ),
                rationale=(
                    "Durable staging identity created from accepted candidates."
                    if created
                    else "Durable staging identity observed in a later acceptance."
                ),
            )
        )

    active = set(known_generations) - inactive
    transitioned_sources: set[str] = set()
    current_targets = set(accepted)
    for directive in directives:
        _validate_directive(directive)
        missing_sources = set(directive.source_keys) - active
        if missing_sources:
            raise IdentityLifecycleError(
                "transition sources are not active: "
                + ", ".join(sorted(missing_sources))
            )
        repeated = set(directive.source_keys) & transitioned_sources
        if repeated:
            raise IdentityLifecycleError(
                "identity transitioned more than once: "
                + ", ".join(sorted(repeated))
            )
        missing_targets = set(directive.target_keys) - current_targets
        if missing_targets:
            raise IdentityLifecycleError(
                "transition targets require acceptance in the current capture: "
                + ", ".join(sorted(missing_targets))
            )
        latest_source_time = max(
            item.observed_at
            for item in generations
            if item.identity_key in directive.source_keys
        )
        target_acceptance_time = max(
            _review_time(accepted[key]) for key in directive.target_keys
        )
        if directive.directed_at < latest_source_time:
            raise IdentityLifecycleError(
                "transition cannot predate its latest source observation"
            )
        if directive.directed_at < target_acceptance_time:
            raise IdentityLifecycleError(
                "transition cannot predate its target acceptance"
            )
        transitioned_sources.update(directive.source_keys)
        inactive.update(directive.source_keys)
        active.difference_update(directive.source_keys)
        active.update(directive.target_keys)
        event_type = {
            IdentityTransition.SUPERSEDE: IdentityLifecycleEventType.SUPERSEDED,
            IdentityTransition.MERGE: IdentityLifecycleEventType.MERGED,
            IdentityTransition.SPLIT: IdentityLifecycleEventType.SPLIT,
        }[directive.transition]
        events.append(
            IdentityLifecycleEvent(
                event_type=event_type,
                occurred_at=directive.directed_at,
                source_keys=tuple(sorted(directive.source_keys)),
                target_keys=tuple(sorted(directive.target_keys)),
                actor=directive.directed_by,
                rationale=directive.rationale,
            )
        )

    return IdentityLifecycleState(
        generations=tuple(
            sorted(generations, key=lambda item: (item.identity_key, item.generation))
        ),
        events=tuple(
            sorted(
                events,
                key=lambda item: (
                    item.occurred_at,
                    item.event_type.value,
                    item.source_keys,
                    item.target_keys,
                ),
            )
        ),
        inactive_identity_keys=tuple(sorted(inactive)),
    )


def identity_lifecycle_data(state: IdentityLifecycleState) -> dict[str, Any]:
    """Return a stable JSON-compatible lifecycle ledger."""
    return {
        "active_identity_keys": list(state.active_identity_keys),
        "inactive_identity_keys": list(state.inactive_identity_keys),
        "generations": [
            {
                "identity_key": item.identity_key,
                "generation": item.generation,
                "observed_at": item.observed_at.isoformat(),
                "candidate_keys": list(item.candidate_keys),
                "target_keys": list(item.target_keys),
                "acceptance_reviews": [
                    {
                        "candidate_key": review.candidate_key,
                        "disposition": review.disposition.value,
                        "reviewed_by": review.reviewed_by,
                        "reviewed_at": review.reviewed_at.isoformat(),
                        "rationale": review.rationale,
                        "durable_identity_key": review.durable_identity_key,
                        "override_conflict": review.override_conflict,
                    }
                    for review in item.acceptance_reviews
                ],
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
            for item in state.generations
        ],
        "events": [
            {
                "event_type": item.event_type.value,
                "occurred_at": item.occurred_at.isoformat(),
                "source_keys": list(item.source_keys),
                "target_keys": list(item.target_keys),
                "actor": item.actor,
                "rationale": item.rationale,
            }
            for item in state.events
        ],
    }


def identity_lifecycle_json(state: IdentityLifecycleState) -> str:
    """Serialize the lifecycle ledger deterministically with a final newline."""
    return json.dumps(
        identity_lifecycle_data(state), indent=2, ensure_ascii=False
    ) + "\n"
