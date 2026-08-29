"""Apply an attributable physical I/O mapping review without guessing it."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from importlib.resources import files
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from twinforge.knowledge.io_card_catalog import IOCardLibrary, IOCardSpec
from twinforge.model import IODirection, IOSignalType


class IOMappingReviewError(ValueError):
    """Raised when an I/O mapping review cannot be safely applied."""


def io_mapping_review_schema_text() -> str:
    """Return the packaged io-mapping-review v1 JSON Schema text."""

    schema = files("twinforge.schemas").joinpath("io-mapping-review.v1.schema.json")
    return schema.read_text(encoding="utf-8")


class IOMappingReviewItem(BaseModel):
    """One engineer-attested binding of a physical point to a card channel."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    physical_address: str = Field(min_length=1)
    card_part_number: str = Field(min_length=1)
    card_instance: str = Field(min_length=1)
    channel: int = Field(ge=0)

    @field_validator("physical_address", "card_part_number", "card_instance")
    @classmethod
    def strings_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("io-mapping review strings must not be blank")
        return stripped


class IOMappingReviewDocument(BaseModel):
    """Versioned, attributable physical I/O mapping overlay."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["twinforge.io-mapping-review.v1"]
    controller_name: str = Field(min_length=1)
    reviewed_by: str = Field(min_length=1)
    reviewed_at: datetime
    authority_reference: str = Field(min_length=1)
    source_reference: str = Field(min_length=1)
    items: tuple[IOMappingReviewItem, ...] = Field(min_length=1)

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
    def item_addresses_must_be_unique(
        cls, value: tuple[IOMappingReviewItem, ...]
    ) -> tuple[IOMappingReviewItem, ...]:
        addresses = [item.physical_address for item in value]
        if len(addresses) != len(set(addresses)):
            raise ValueError("io-mapping review physical_address values must be unique")
        return value


def load_io_mapping_review(path: Path) -> IOMappingReviewDocument:
    """Load and validate a versioned io-mapping review document from disk."""
    try:
        return IOMappingReviewDocument.model_validate_json(
            path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as error:
        raise IOMappingReviewError(
            f"cannot load io-mapping review '{path}': {error}"
        ) from error


@dataclass(frozen=True)
class IOMappingReviewProvenance:
    """Who attested a resolved I/O mapping, and against what evidence."""

    reviewed_by: str
    reviewed_at: datetime
    authority_reference: str
    source_reference: str


@dataclass(frozen=True)
class IOMappingResolution:
    """One physical point resolved onto a target card channel."""

    physical_address: str
    card_part_number: str
    card_instance: str
    channel: int
    direction: IODirection
    signal_type: IOSignalType
    compatibility_confirmed: bool


@dataclass(frozen=True)
class IOMappingReport:
    """Every known physical point, resolved or explicitly left unmapped."""

    controller_name: str
    resolved: tuple[IOMappingResolution, ...]
    unmapped: tuple[str, ...]
    review: IOMappingReviewProvenance


def apply_io_mapping_review(
    controller_name: str,
    points: list[dict[str, object]],
    library: IOCardLibrary,
    review: IOMappingReviewDocument,
) -> IOMappingReport:
    """Resolve a reviewed I/O mapping without inventing any binding."""

    if review.controller_name != controller_name:
        raise IOMappingReviewError(
            "io-mapping review controller_name does not match the CCW controller"
        )

    known: dict[str, dict[str, object]] = {
        str(point["physical_address"]): point for point in points
    }
    unknown_addresses = sorted(
        {
            item.physical_address
            for item in review.items
            if item.physical_address not in known
        }
    )
    if unknown_addresses:
        raise IOMappingReviewError(
            "io-mapping review references unknown physical_address values: "
            + ", ".join(unknown_addresses)
        )

    cards: dict[str, IOCardSpec] = {}
    unknown_parts: set[str] = set()
    for item in review.items:
        if item.card_part_number in cards:
            continue
        card = library.find(item.card_part_number)
        if card is None:
            unknown_parts.add(item.card_part_number)
        else:
            cards[item.card_part_number] = card
    if unknown_parts:
        raise IOMappingReviewError(
            "io-mapping review references unknown card_part_number values: "
            + ", ".join(sorted(unknown_parts))
        )

    out_of_range = [
        f"{item.physical_address} channel {item.channel} on {item.card_part_number} "
        f"(channel_count={cards[item.card_part_number].channel_count})"
        for item in review.items
        if item.channel >= cards[item.card_part_number].channel_count
    ]
    if out_of_range:
        raise IOMappingReviewError(
            "io-mapping review assigns a channel outside the card's "
            "channel_count: " + "; ".join(out_of_range)
        )

    incompatible: list[str] = []
    for item in review.items:
        card = cards[item.card_part_number]
        point = known[item.physical_address]
        point_direction = point.get("direction")
        point_signal_type = point.get("signal_type")
        if point_direction is not None and point_direction != card.direction.value:
            incompatible.append(
                f"{item.physical_address} is {point_direction} but "
                f"{item.card_part_number} is {card.direction.value}"
            )
        if point_signal_type is not None and point_signal_type != card.signal_type.value:
            incompatible.append(
                f"{item.physical_address} is {point_signal_type} but "
                f"{item.card_part_number} is {card.signal_type.value}"
            )
    if incompatible:
        raise IOMappingReviewError(
            "io-mapping review assigns an incompatible direction or signal "
            "type: " + "; ".join(incompatible)
        )

    channel_assignments: dict[tuple[str, str, int], list[str]] = {}
    for item in review.items:
        key = (
            item.card_part_number.casefold(),
            item.card_instance.casefold(),
            item.channel,
        )
        channel_assignments.setdefault(key, []).append(item.physical_address)
    duplicates = {
        key: addresses
        for key, addresses in channel_assignments.items()
        if len(addresses) > 1
    }
    if duplicates:
        details = "; ".join(
            f"{part}/{instance} channel {channel}: {', '.join(addresses)}"
            for (part, instance, channel), addresses in sorted(duplicates.items())
        )
        raise IOMappingReviewError(
            "io-mapping review assigns the same card channel to multiple "
            "physical addresses: " + details
        )

    resolved: list[IOMappingResolution] = []
    for item in review.items:
        card = cards[item.card_part_number]
        point = known[item.physical_address]
        compatibility_confirmed = (
            point.get("direction") is not None and point.get("signal_type") is not None
        )
        resolved.append(
            IOMappingResolution(
                physical_address=item.physical_address,
                card_part_number=item.card_part_number,
                card_instance=item.card_instance,
                channel=item.channel,
                direction=card.direction,
                signal_type=card.signal_type,
                compatibility_confirmed=compatibility_confirmed,
            )
        )

    mapped_addresses = {item.physical_address for item in review.items}
    unmapped = tuple(sorted(set(known) - mapped_addresses))

    return IOMappingReport(
        controller_name=controller_name,
        resolved=tuple(resolved),
        unmapped=unmapped,
        review=IOMappingReviewProvenance(
            reviewed_by=review.reviewed_by,
            reviewed_at=review.reviewed_at,
            authority_reference=review.authority_reference,
            source_reference=review.source_reference,
        ),
    )
