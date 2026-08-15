"""Apply explicit engineering review without replacing source evidence."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from importlib.resources import files
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .alarm_candidates import (
    AlarmTripCandidateReport,
    AlarmTripReviewProvenance,
)


class AlarmReviewError(ValueError):
    """Raised when a review document cannot be safely applied."""


def alarm_review_schema_text() -> str:
    """Return the packaged alarm-review v1 JSON Schema text."""

    schema = files("twinforge.schemas").joinpath("alarm-review.v1.schema.json")
    return schema.read_text(encoding="utf-8")


class AlarmReviewItem(BaseModel):
    """Engineer-asserted fields for one exact candidate key."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tag_key: str = Field(min_length=1)
    priority: str | None = None
    setpoint: str | None = None
    engineering_unit: str | None = None
    delay: str | None = None
    latching: str | None = None
    acknowledgement: str | None = None
    suppression: str | None = None
    shutdown_action: str | None = None
    applicability: str | None = None

    @field_validator("*")
    @classmethod
    def strings_must_not_be_blank(cls, value: object) -> object:
        """Reject whitespace-only assertions and normalize outer whitespace."""
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("review strings must not be blank")
        return stripped

    @model_validator(mode="after")
    def must_assert_at_least_one_review_field(self) -> AlarmReviewItem:
        asserted = self.model_fields_set - {"tag_key"}
        if not asserted or all(getattr(self, name) is None for name in asserted):
            raise ValueError("each review item must assert at least one field")
        return self


class AlarmReviewDocument(BaseModel):
    """Versioned, attributable review overlay for one controller report."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["twinforge.alarm-review.v1"]
    controller_name: str = Field(min_length=1)
    reviewed_by: str = Field(min_length=1)
    reviewed_at: datetime
    authority_reference: str = Field(min_length=1)
    source_reference: str = Field(min_length=1)
    items: tuple[AlarmReviewItem, ...] = Field(min_length=1)

    @field_validator(
        "controller_name",
        "reviewed_by",
        "authority_reference",
        "source_reference",
    )
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("required review text must not be blank")
        return stripped

    @field_validator("reviewed_at")
    @classmethod
    def reviewed_at_must_include_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("reviewed_at must include a timezone")
        return value

    @field_validator("items")
    @classmethod
    def item_keys_must_be_unique(
        cls, value: tuple[AlarmReviewItem, ...]
    ) -> tuple[AlarmReviewItem, ...]:
        keys = [item.tag_key for item in value]
        if len(keys) != len(set(keys)):
            raise ValueError("alarm review tag_key values must be unique")
        return value


def load_alarm_review(path: Path) -> AlarmReviewDocument:
    """Load and validate a versioned review document from disk."""
    try:
        return AlarmReviewDocument.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise AlarmReviewError(f"cannot load alarm review '{path}': {error}") from error


def apply_alarm_review(
    report: AlarmTripCandidateReport,
    review: AlarmReviewDocument,
) -> AlarmTripCandidateReport:
    """Return a reviewed copy while retaining all candidate evidence."""
    if review.controller_name != report.controller_name:
        raise AlarmReviewError(
            "alarm review controller_name does not match the parsed controller"
        )
    candidates = {candidate.tag_key: candidate for candidate in report.candidates}
    unknown = sorted(
        item.tag_key for item in review.items if item.tag_key not in candidates
    )
    if unknown:
        raise AlarmReviewError(
            "alarm review references unknown candidate tag_key values: "
            + ", ".join(unknown)
        )
    replacements = {}
    for item in review.items:
        fields = {
            name: getattr(item, name) for name in item.model_fields_set - {"tag_key"}
        }
        replacements[item.tag_key] = replace(candidates[item.tag_key], **fields)
    reviewed_candidates = tuple(
        replacements.get(candidate.tag_key, candidate)
        for candidate in report.candidates
    )
    return AlarmTripCandidateReport(
        controller_name=report.controller_name,
        candidates=reviewed_candidates,
        review=AlarmTripReviewProvenance(
            reviewed_by=review.reviewed_by,
            reviewed_at=review.reviewed_at,
            authority_reference=review.authority_reference,
            source_reference=review.source_reference,
            applied_tag_keys=tuple(sorted(replacements)),
        ),
    )
