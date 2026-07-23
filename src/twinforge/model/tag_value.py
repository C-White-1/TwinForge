from __future__ import annotations

from dataclasses import dataclass


ScalarTagValue = bool | int | float | str


@dataclass(frozen=True)
class TagValue:
    """A typed scalar value promoted from a preserved source representation."""

    value: ScalarTagValue
    data_type: str
    lexical_value: str
    radix: str | None = None
    source_format: str = "Decorated"
