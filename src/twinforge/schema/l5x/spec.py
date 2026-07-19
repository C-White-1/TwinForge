from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .reference import ReferenceType


@dataclass(frozen=True)
class AttributeSpec:
    name: str
    description: str

    xml_type: type = str
    datatype: type = str

    # Semantic validation
    target_type: ReferenceType | None = None

    required: bool = False
    l5x_only: bool = False

    applicability: frozenset[str] = frozenset({"standard", "safety"})

    # Attribute values on the same element that make this attribute applicable.
    # Each condition is (attribute_name, accepted_values).
    applicable_when: tuple[tuple[str, tuple[Any, ...]], ...] = ()

    valid_values: tuple[Any, ...] | None = None
    value_labels: tuple[tuple[Any, str], ...] = ()
    minimum: int | float | None = None
    maximum: int | float | None = None

    manual_ref: str = ""
    notes: str = ""


@dataclass(frozen=True)
class ElementSpec:
    name: str
    description: str = ""
    attributes: dict[str, AttributeSpec] = field(default_factory=dict)
    elements: dict[str, "ElementSpec"] = field(default_factory=dict)
    required: bool = False
    repeatable: bool = False
    content_type: str | None = None
    manual_ref: str = ""
