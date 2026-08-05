from datetime import datetime, timedelta, timezone

import pytest

from twinforge.discovery import (
    AcceptanceResult,
    AcceptedIdentityRecord,
    CandidateDisposition,
    CandidateReview,
    IdentityLifecycleError,
    IdentityLifecycleEventType,
    IdentityLifecycleState,
    IdentityTransition,
    IdentityTransitionDirective,
    TopologyEvidenceReference,
    advance_identity_lifecycle,
    identity_lifecycle_json,
)


T0 = datetime(2026, 8, 5, tzinfo=timezone.utc)


def _accepted(key: str, when: datetime) -> AcceptedIdentityRecord:
    candidate = f"candidate:{key}:{when.isoformat()}"
    review = CandidateReview(
        candidate_key=candidate,
        disposition=CandidateDisposition.ACCEPT,
        reviewed_by="operator@example.test",
        reviewed_at=when,
        rationale="Accepted after authorized evidence review.",
        durable_identity_key=key,
    )
    return AcceptedIdentityRecord(
        key=key,
        candidate_keys=(candidate,),
        target_keys=(f"target:{key}",),
        reviews=(review,),
        evidence=(
            TopologyEvidenceReference(
                protocol="fixture",
                observation_target=f"target:{key}",
                identifier=candidate,
                description="fixture lifecycle evidence",
            ),
        ),
        conflict_overridden=False,
    )


def _acceptance(*records: AcceptedIdentityRecord) -> AcceptanceResult:
    return AcceptanceResult(
        accepted_identities=records,
        rejected_candidate_keys=(),
        deferred_candidate_keys=(),
        unreviewed_candidate_keys=(),
    )


def test_repeated_acceptance_creates_generations_without_retiring_absent_assets() -> None:
    first = advance_identity_lifecycle(
        IdentityLifecycleState(),
        _acceptance(_accepted("asset:a", T0), _accepted("asset:b", T0)),
    )
    second = advance_identity_lifecycle(
        first,
        _acceptance(_accepted("asset:a", T0 + timedelta(days=1))),
    )

    assert [(item.identity_key, item.generation) for item in second.generations] == [
        ("asset:a", 1),
        ("asset:a", 2),
        ("asset:b", 1),
    ]
    assert second.active_identity_keys == ("asset:a", "asset:b")
    assert [item.event_type for item in second.events] == [
        IdentityLifecycleEventType.CREATED,
        IdentityLifecycleEventType.CREATED,
        IdentityLifecycleEventType.OBSERVED,
    ]


def test_merge_requires_explicit_directive_and_currently_accepted_target() -> None:
    previous = advance_identity_lifecycle(
        IdentityLifecycleState(),
        _acceptance(_accepted("asset:a", T0), _accepted("asset:b", T0)),
    )
    directive = IdentityTransitionDirective(
        transition=IdentityTransition.MERGE,
        source_keys=("asset:a", "asset:b"),
        target_keys=("asset:ab",),
        directed_by="operator@example.test",
        directed_at=T0 + timedelta(days=1),
        rationale="Records were confirmed to describe one physical asset.",
    )

    merged = advance_identity_lifecycle(
        previous,
        _acceptance(_accepted("asset:ab", T0 + timedelta(days=1))),
        (directive,),
    )

    assert merged.active_identity_keys == ("asset:ab",)
    assert merged.inactive_identity_keys == ("asset:a", "asset:b")
    assert merged.events[-1].event_type is IdentityLifecycleEventType.MERGED


def test_transition_target_must_be_accepted_in_current_capture() -> None:
    previous = advance_identity_lifecycle(
        IdentityLifecycleState(),
        _acceptance(_accepted("asset:a", T0)),
    )
    directive = IdentityTransitionDirective(
        transition=IdentityTransition.SUPERSEDE,
        source_keys=("asset:a",),
        target_keys=("asset:b",),
        directed_by="operator@example.test",
        directed_at=T0 + timedelta(days=1),
        rationale="Equipment identity was replaced after manual review.",
    )

    with pytest.raises(IdentityLifecycleError, match="current capture"):
        advance_identity_lifecycle(previous, _acceptance(), (directive,))


def test_transition_cannot_predate_target_acceptance() -> None:
    previous = advance_identity_lifecycle(
        IdentityLifecycleState(),
        _acceptance(_accepted("asset:a", T0)),
    )
    target_time = T0 + timedelta(days=2)
    directive = IdentityTransitionDirective(
        transition=IdentityTransition.SUPERSEDE,
        source_keys=("asset:a",),
        target_keys=("asset:b",),
        directed_by="operator@example.test",
        directed_at=T0 + timedelta(days=1),
        rationale="Equipment identity was replaced after manual review.",
    )

    with pytest.raises(IdentityLifecycleError, match="target acceptance"):
        advance_identity_lifecycle(
            previous,
            _acceptance(_accepted("asset:b", target_time)),
            (directive,),
        )


def test_inactive_identity_key_cannot_be_silently_reused() -> None:
    previous = IdentityLifecycleState(inactive_identity_keys=("asset:a",))
    with pytest.raises(IdentityLifecycleError, match="cannot be observed again"):
        advance_identity_lifecycle(
            previous,
            _acceptance(_accepted("asset:a", T0)),
        )


def test_lifecycle_serialization_is_deterministic() -> None:
    state = advance_identity_lifecycle(
        IdentityLifecycleState(),
        _acceptance(_accepted("asset:a", T0)),
    )

    assert identity_lifecycle_json(state) == identity_lifecycle_json(state)
    assert identity_lifecycle_json(state).endswith("\n")
