"""User-authored, versioned catalog of target-hardware I/O card specs."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from twinforge.model import IODirection, IOSignalType


class IOCardLibraryError(ValueError):
    """Raised when an I/O card library cannot be loaded or validated."""


def io_card_library_schema_text() -> str:
    """Return the packaged I/O card library v1 JSON Schema text."""

    schema = files("twinforge.schemas").joinpath("io-card-library.v1.schema.json")
    return schema.read_text(encoding="utf-8")


class IOCardSpec(BaseModel):
    """Electrical spec for one target-hardware I/O card part number."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    part_number: str = Field(min_length=1)
    vendor: str = Field(min_length=1)
    direction: IODirection
    signal_type: IOSignalType
    channel_count: int = Field(ge=1)
    voltage: str | None = None
    description: str | None = None

    @field_validator("part_number", "vendor", "voltage", "description")
    @classmethod
    def strings_must_not_be_blank(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("io card library strings must not be blank")
        return stripped


class IOCardLibrary(BaseModel):
    """Versioned collection of I/O card specs, unique by part number."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["twinforge.io-card-library.v1"]
    cards: tuple[IOCardSpec, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_part_numbers(self) -> IOCardLibrary:
        numbers = [card.part_number.casefold() for card in self.cards]
        if len(numbers) != len(set(numbers)):
            raise ValueError("io card library part numbers must be unique")
        return self

    def find(self, part_number: str) -> IOCardSpec | None:
        """Return the card spec for one part number, or None if unknown."""
        for card in self.cards:
            if card.part_number.casefold() == part_number.casefold():
                return card
        return None


def load_io_card_library(path: Path) -> IOCardLibrary:
    """Load and validate a versioned I/O card library from disk."""
    try:
        return IOCardLibrary.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise IOCardLibraryError(f"cannot load I/O card library '{path}': {error}") from error
