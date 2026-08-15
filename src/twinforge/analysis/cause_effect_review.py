"""Apply attributable review to exact cause-and-effect relationships."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from importlib.resources import files
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .cause_effect import (
    CauseEvidence,
    CauseEffectCandidateReport,
    CauseEffectReviewProvenance,
    UnresolvedCauseEvidence,
)


class CauseEffectReviewError(ValueError):
    """Raised when a cause-and-effect review cannot be safely applied."""


def cause_effect_review_schema_text() -> str:
    """Return the packaged cause-and-effect review v1 JSON Schema."""

    schema = files("twinforge.schemas").joinpath(
        "cause-effect-review.v1.schema.json"
    )
    return schema.read_text(encoding="utf-8")


class CauseEffectReviewItem(BaseModel):
    """Engineering disposition for one exact relationship key."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    relationship_key: str = Field(pattern=r"^ce:[0-9a-f]{24}$")
    status: Literal["verified", "rejected"]
    polarity: str | None = None
    voting: str | None = None
    delay: str | None = None
    operating_modes: str | None = None
    shutdown_action: str | None = None

    @field_validator("*")
    @classmethod
    def strings_must_not_be_blank(cls, value: object) -> object:
        """Normalize asserted text and reject empty assertions."""
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("cause-and-effect review strings must not be blank")
        return stripped

    @model_validator(mode="after")
    def asserted_fields_must_not_be_null(self) -> CauseEffectReviewItem:
        asserted = self.model_fields_set - {"relationship_key", "status"}
        null_fields = sorted(
            name for name in asserted if getattr(self, name) is None
        )
        if null_fields:
            raise ValueError(
                "explicit relationship review fields must not be null: "
                + ", ".join(null_fields)
            )
        return self


class CauseEffectReviewDocument(BaseModel):
    """Versioned review overlay for one controller relationship matrix."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["twinforge.cause-effect-review.v1"]
    controller_name: str = Field(min_length=1)
    reviewed_by: str = Field(min_length=1)
    reviewed_at: datetime
    authority_reference: str = Field(min_length=1)
    source_reference: str = Field(min_length=1)
    items: tuple[CauseEffectReviewItem, ...] = Field(min_length=1)

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
    def relationship_keys_must_be_unique(
        cls,
        value: tuple[CauseEffectReviewItem, ...],
    ) -> tuple[CauseEffectReviewItem, ...]:
        keys = [item.relationship_key for item in value]
        if len(keys) != len(set(keys)):
            raise ValueError("cause-and-effect relationship_key values must be unique")
        return value


def load_cause_effect_review(path: Path) -> CauseEffectReviewDocument:
    """Load and validate one cause-and-effect review document."""

    try:
        return CauseEffectReviewDocument.model_validate_json(
            path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as error:
        raise CauseEffectReviewError(
            f"cannot load cause-and-effect review '{path}': {error}"
        ) from error


def apply_cause_effect_review(
    report: CauseEffectCandidateReport,
    review: CauseEffectReviewDocument,
) -> CauseEffectCandidateReport:
    """Return a reviewed copy while preserving every inferred relationship."""

    if review.controller_name != report.controller_name:
        raise CauseEffectReviewError(
            "cause-and-effect review controller_name does not match the parsed controller"
        )
    resolved = {
        cause.relationship_key: cause
        for candidate in report.candidates
        for cause in candidate.causes
    }
    unresolved = {
        cause.relationship_key: cause
        for candidate in report.candidates
        for cause in candidate.unresolved_causes
    }
    known = resolved.keys() | unresolved.keys()
    unknown = sorted(
        item.relationship_key
        for item in review.items
        if item.relationship_key not in known
    )
    if unknown:
        raise CauseEffectReviewError(
            "cause-and-effect review references unknown relationship keys: "
            + ", ".join(unknown)
        )
    invalid = sorted(
        item.relationship_key
        for item in review.items
        if item.status == "verified" and item.relationship_key in unresolved
    )
    if invalid:
        raise CauseEffectReviewError(
            "unresolved relationships cannot be verified: " + ", ".join(invalid)
        )

    assertions = {item.relationship_key: item for item in review.items}
    candidates = []
    for candidate in report.candidates:
        reviewed_causes = tuple(
            _apply_item(cause, assertions.get(cause.relationship_key))
            for cause in candidate.causes
        )
        reviewed_unresolved = tuple(
            _apply_item(cause, assertions.get(cause.relationship_key))
            for cause in candidate.unresolved_causes
        )
        candidates.append(
            replace(
                candidate,
                causes=reviewed_causes,
                unresolved_causes=reviewed_unresolved,
                causal_relationship_verified=any(
                    cause.review_status == "verified" for cause in reviewed_causes
                ),
            )
        )
    return CauseEffectCandidateReport(
        controller_name=report.controller_name,
        candidates=tuple(candidates),
        review=CauseEffectReviewProvenance(
            reviewed_by=review.reviewed_by,
            reviewed_at=review.reviewed_at,
            authority_reference=review.authority_reference,
            source_reference=review.source_reference,
            applied_relationship_keys=tuple(sorted(assertions)),
        ),
    )


def _apply_item(
    cause: CauseEvidence | UnresolvedCauseEvidence,
    item: CauseEffectReviewItem | None,
) -> CauseEvidence | UnresolvedCauseEvidence:
    if item is None:
        return cause
    fields = {
        name: getattr(item, name)
        for name in item.model_fields_set - {"relationship_key", "status"}
    }
    return replace(cause, review_status=item.status, **fields)
