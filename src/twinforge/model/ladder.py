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
    # A condition element whose value comes from a named function block's own
    # output pin (a drawn ladder wire from the block's own grid position),
    # not a declared tag read the way a contact is. See LadderInstruction.
    BLOCK_OUTPUT_REFERENCE = "block_output_reference"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class LadderPosition:
    """Producer-supplied instruction or network grid position."""

    column: int
    row: int


@dataclass(frozen=True)
class LadderInstruction:
    """One source instruction with optional portable semantics.

    `operand` is a declared tag/variable name for every operation except
    `BLOCK_OUTPUT_REFERENCE`, where it is instead `"{instance_name}.
    {pin_name}"` -- there is no declared tag to name, since the value comes
    from another block's own output pin, not project data. `source_mnemonic`
    holds that block's `typeName` in that case, not a vendor XML keyword.
    """

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
    second declared input (e.g. `S1` for an `SR` block).

    A block's later declared inputs (index >= 1, `enEnO="true"` only) are
    also resolved, at row `posY+1+i` -- mirroring the already-evidenced
    output-side formula (`posY+1+i`) applied to inputs instead (real
    evidence: `sayahali_conveyor_ali_conv.zef`'s `SR_2.Q1 -> TON_23.IN`).
    `position` is always the TARGET block's own anchor (`posX`, `posY`),
    never the row the wire actually lands on -- those differ for this
    later-input case, unlike every other rule here.
    """

    network_index: int
    position: LadderPosition
    pin_name: str
    condition: LadderSeries
