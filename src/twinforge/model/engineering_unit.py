from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EngineeringUnitSource(str, Enum):
    MODULE_CHANNEL = "l5x_module_channel"
    COMPARISON = "rll_comparison"
    TAG_DESCRIPTION = "tag_description"


class EngineeringUnitConfidence(str, Enum):
    EXPLICIT = "explicit"
    DERIVED = "derived"
    INFERRED = "inferred"


@dataclass(frozen=True)
class EngineeringUnitEvidence:
    symbol: str
    source: EngineeringUnitSource
    confidence: EngineeringUnitConfidence
    source_operand: str | None = None
    inherited_from: str | None = None
