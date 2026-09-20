# src/twinforge/model/routine.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .source_extension import SourceExtension
from .ladder import LadderPosition, LadderSeries
from .graphical import GraphicalDiagram
from .sequential import SequentialChart


@dataclass
class LadderRung:
    number: int | None = None
    rung_type: str | None = None
    comment: str | None = None
    text: str | None = None
    position: LadderPosition | None = None
    network: LadderSeries | None = None
    source_sha256: str | None = None
    source_extensions: list[SourceExtension] = field(default_factory=list, repr=False)


@dataclass
class StructuredTextLine:
    """One numbered source line from an IEC 61131-3 Structured Text body."""

    number: int | None = None
    text: str = ""
    source_extensions: list[SourceExtension] = field(
        default_factory=list, repr=False
    )


@dataclass
class Routine:
    name: str = ""
    description: str | None = None
    source: object | None = None
    target: object | None = None
    protocol: str = ""
    language: str | None = None
    ladder_rungs: list[LadderRung] = field(default_factory=list)
    structured_text_lines: list[StructuredTextLine] = field(
        default_factory=list
    )
    metadata: dict = field(default_factory=dict)
    parent: Any | None = field(default=None, repr=False)
    source_extensions: list[SourceExtension] = field(default_factory=list, repr=False)
    graphical_diagrams: list[GraphicalDiagram] = field(default_factory=list)

    sequential_charts: list[SequentialChart] = field(default_factory=list)

    @property
    def structured_text(self) -> str:
        """Return the source body while preserving captured line whitespace."""

        return "\n".join(line.text for line in self.structured_text_lines)
