"""Summarize engineering-review coverage without implying approval."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from .alarm_candidates import AlarmTripCandidateReport
from .cause_effect import CauseEffectCandidateReport


_ALARM_REVIEW_FIELDS = (
    "priority",
    "setpoint",
    "engineering_unit",
    "delay",
    "latching",
    "acknowledgement",
    "suppression",
    "shutdown_action",
    "applicability",
)


@dataclass(frozen=True)
class AlarmReviewCoverageItem:
    """Review state and absent philosophy fields for one alarm candidate."""

    tag_key: str
    reviewed: bool
    missing_fields: tuple[str, ...]


@dataclass(frozen=True)
class CauseEffectReviewCoverageItem:
    """Disposition state for one exact cause-and-effect relationship."""

    relationship_key: str
    cause_status: str
    review_status: str


@dataclass(frozen=True)
class EngineeringReviewCoverage:
    """Deterministic review coverage across alarm and relationship reports."""

    controller_name: str
    alarm_candidates: tuple[AlarmReviewCoverageItem, ...]
    cause_effect_relationships: tuple[CauseEffectReviewCoverageItem, ...]

    @property
    def reviewed_alarm_count(self) -> int:
        """Return the number of candidates explicitly present in a review."""

        return sum(item.reviewed for item in self.alarm_candidates)

    @property
    def complete_alarm_count(self) -> int:
        """Return candidates for which every tracked field is populated."""

        return sum(not item.missing_fields for item in self.alarm_candidates)

    @property
    def verified_relationship_count(self) -> int:
        """Return exact relationships carrying a verified disposition."""

        return sum(
            item.review_status == "verified"
            for item in self.cause_effect_relationships
        )

    @property
    def rejected_relationship_count(self) -> int:
        """Return exact relationships carrying a rejected disposition."""

        return sum(
            item.review_status == "rejected"
            for item in self.cause_effect_relationships
        )


def build_engineering_review_coverage(
    alarms: AlarmTripCandidateReport,
    cause_effect: CauseEffectCandidateReport,
) -> EngineeringReviewCoverage:
    """Build a coverage summary from already-derived and reviewed evidence."""

    if alarms.controller_name != cause_effect.controller_name:
        raise ValueError("review coverage reports must describe the same controller")
    reviewed_keys = (
        frozenset(alarms.review.applied_tag_keys)
        if alarms.review is not None
        else frozenset()
    )
    alarm_items = tuple(
        AlarmReviewCoverageItem(
            tag_key=candidate.tag_key,
            reviewed=candidate.tag_key in reviewed_keys,
            missing_fields=tuple(
                field
                for field in _ALARM_REVIEW_FIELDS
                if getattr(candidate, field) is None
            ),
        )
        for candidate in alarms.candidates
    )
    relationship_items = tuple(
        CauseEffectReviewCoverageItem(
            relationship_key=cause.relationship_key,
            cause_status=cause_status,
            review_status=cause.review_status,
        )
        for candidate in cause_effect.candidates
        for cause_status, causes in (
            ("resolved", candidate.causes),
            ("unresolved", candidate.unresolved_causes),
        )
        for cause in causes
    )
    return EngineeringReviewCoverage(
        controller_name=alarms.controller_name,
        alarm_candidates=alarm_items,
        cause_effect_relationships=relationship_items,
    )


def engineering_review_coverage_data(
    coverage: EngineeringReviewCoverage,
) -> dict[str, object]:
    """Return deterministic JSON-compatible review coverage data."""

    relationships = coverage.cause_effect_relationships
    return {
        "controller_name": coverage.controller_name,
        "summary": {
            "alarm_candidate_count": len(coverage.alarm_candidates),
            "reviewed_alarm_count": coverage.reviewed_alarm_count,
            "complete_alarm_count": coverage.complete_alarm_count,
            "relationship_count": len(relationships),
            "verified_relationship_count": coverage.verified_relationship_count,
            "rejected_relationship_count": coverage.rejected_relationship_count,
            "unreviewed_relationship_count": sum(
                item.review_status == "unreviewed" for item in relationships
            ),
            "unresolved_relationship_count": sum(
                item.cause_status == "unresolved" for item in relationships
            ),
        },
        "alarm_candidates": [asdict(item) for item in coverage.alarm_candidates],
        "cause_effect_relationships": [
            asdict(item) for item in coverage.cause_effect_relationships
        ],
    }


def engineering_review_coverage_json(
    coverage: EngineeringReviewCoverage,
) -> str:
    """Serialize review coverage deterministically."""

    return json.dumps(engineering_review_coverage_data(coverage), indent=2) + "\n"
