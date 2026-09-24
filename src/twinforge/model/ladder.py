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


@dataclass(frozen=True)
class LadderPinCondition:
    """A grid-position-resolved vertical-wire condition feeding one block pin.

    Evidenced only for a block's own anchor row (`objPosition posY`): a
    `shortCircuit`-originated vertical bus (continuing through bare `VLink`
    rows at the same column, or wrapping the block directly) that lands
    cleanly there -- nothing but empty cells between the wire and the block,
    with no further `VLink` continuing past it -- unambiguously targets the
    block's first *wireable* input. That is `EN` when `enEnO="true"`
    (Schneider always lists it first); when `enEnO="false"`, `EN`/`ENO` are
    declared but never rendered, so the anchor row instead targets the
    second declared input (e.g. `S1` for an `SR` block). Multi-row blocks
    where the wire keeps a `VLink` alive past the anchor row are not
    resolved by this rule; the row-to-pin mapping for additional input rows
    is not evidenced.
    """

    network_index: int
    position: LadderPosition
    pin_name: str
    condition: LadderSeries
