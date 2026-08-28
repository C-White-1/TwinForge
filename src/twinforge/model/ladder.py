"""Target-neutral ladder-logic topology and instruction evidence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LadderOperation(str, Enum):
    """Portable meaning assigned only when source evidence is sufficient."""

    NORMALLY_OPEN_CONTACT = "normally_open_contact"
    NORMALLY_CLOSED_CONTACT = "normally_closed_contact"
    COIL = "coil"
    SET_COIL = "set_coil"
    RESET_COIL = "reset_coil"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class LadderPosition:
    """Producer-supplied instruction or network grid position."""

    column: int
    row: int


@dataclass(frozen=True)
class LadderInstruction:
    """One source instruction with optional portable semantics."""

    operation: LadderOperation
    source_mnemonic: str
    operand: str | None = None
    alias: str | None = None
    annotations: tuple[str, ...] = ()
    position: LadderPosition | None = None


@dataclass(frozen=True)
class LadderSeries:
    """Elements evaluated serially from left to right."""

    elements: tuple[LadderInstruction | LadderParallel, ...]


@dataclass(frozen=True)
class LadderParallel:
    """Two or more alternative ladder paths retained recursively."""

    branches: tuple[LadderSeries, ...]
