# src/twinforge/model/tag.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .source_extension import SourceExtension
from .datatype import Datatype
from .engineering_unit import (
    EngineeringRangeEvidence,
    EngineeringUnitEvidence,
)
from .tag_value import TagValue
from .tag_value import CompositeTagValue


@dataclass(frozen=True)
class MessageTagConfiguration:
    """Typed Logix MESSAGE configuration with original lexical evidence."""

    message_type: str | None = None
    requested_length: int | None = None
    connected_flag: int | None = None
    connection_path: str | None = None
    communication_type_code: int | None = None
    service_code: int | None = None
    object_type: int | None = None
    target_object: int | None = None
    attribute_number: int | None = None
    local_index: int | None = None
    local_element: str | None = None
    destination_tag: str | None = None
    large_packet_usage: bool | None = None
    raw_attributes: dict[str, str] = field(default_factory=dict)


@dataclass
class Tag:
    name: str = ""
    tag_type: str | None = None
    data_type: str | None = None
    data_type_definition: Datatype | None = None
    dimensions: str | None = None
    radix: str | None = None
    constant: bool | None = None
    alias_for: str | None = None
    external_access: str | None = None
    permission_set: str | None = None
    description: str | None = None
    initial_value: TagValue | None = None
    composite_initial_value: CompositeTagValue | None = None
    message_configuration: MessageTagConfiguration | None = None
    engineering_unit: EngineeringUnitEvidence | None = None
    engineering_unit_evidence: list[EngineeringUnitEvidence] = field(
        default_factory=list
    )
    engineering_range: EngineeringRangeEvidence | None = None
    source: object | None = None
    target: object | None = None
    protocol: str = ""
    metadata: dict = field(default_factory=dict)
    parent: Any | None = field(default=None, repr=False)
    source_extensions: list[SourceExtension] = field(default_factory=list, repr=False)
