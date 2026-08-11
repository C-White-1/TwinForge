from __future__ import annotations

from dataclasses import dataclass, field


ScalarTagValue = bool | int | float | str


@dataclass(frozen=True)
class TagValue:
    """A typed scalar value promoted from a preserved source representation."""

    value: ScalarTagValue
    data_type: str
    lexical_value: str
    radix: str | None = None
    source_format: str = "Decorated"


@dataclass(frozen=True)
class CompositeTagValueNode:
    """One ordered structure member, array member, element, or scalar leaf."""

    source_kind: str
    name: str | None = None
    index: str | None = None
    data_type: str | None = None
    dimensions: str | None = None
    radix: str | None = None
    lexical_value: str | None = None
    value: ScalarTagValue | None = None
    children: tuple["CompositeTagValueNode", ...] = ()
    raw_attributes: dict[str, str] = field(default_factory=dict, repr=False)


@dataclass(frozen=True)
class CompositeTagValue:
    """A typed, recursively navigable non-scalar tag initial value."""

    root: CompositeTagValueNode
    source_format: str = "Decorated"
