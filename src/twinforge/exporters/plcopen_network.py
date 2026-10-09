"""Decide how a neutral ladder network maps onto PLCopen LD elements.

`LadderRung.network` (Control Expert, Machine Expert – Basic, CCW) is a
series/parallel tree; PLCopen LD is a connection graph in which each element
lists the localIds feeding it, several references meaning a wired OR. Every
`LadderOperation` in `ENCODINGS` has a direct TC6 encoding on `contact` or
`coil` (attributes `negated`, `edge`, `storage`; tc6_xml_v201.xsd).

`FUNCTION_BLOCK_INPUT` and `BLOCK_OUTPUT_REFERENCE` become a TC6 `block` in
the same graph, but only for instances the caller declares convertible
(`block_types`: IEC TON/TOF/TP with a known PT) and only on their IEC pins.
Anything else, including `UNSUPPORTED`, has no encoding yet, so a rung
containing it is preserved as a comment rather than approximated.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import re

from twinforge.model import LadderInstruction, LadderOperation, LadderParallel, LadderSeries


@dataclass(frozen=True)
class ElementEncoding:
    element: str  # "contact" or "coil"
    negated: bool = False
    edge: str | None = None  # "rising" | "falling"
    storage: str | None = None  # "set" | "reset"


ENCODINGS: dict[LadderOperation, ElementEncoding] = {
    LadderOperation.NORMALLY_OPEN_CONTACT: ElementEncoding("contact"),
    LadderOperation.NORMALLY_CLOSED_CONTACT: ElementEncoding("contact", negated=True),
    LadderOperation.POSITIVE_TRANSITION_CONTACT: ElementEncoding("contact", edge="rising"),
    LadderOperation.NEGATIVE_TRANSITION_CONTACT: ElementEncoding("contact", edge="falling"),
    LadderOperation.COIL: ElementEncoding("coil"),
    LadderOperation.SET_COIL: ElementEncoding("coil", storage="set"),
    LadderOperation.RESET_COIL: ElementEncoding("coil", storage="reset"),
    LadderOperation.NEGATED_COIL: ElementEncoding("coil", negated=True),
}


# IEC 61131-3 standard timers share one interface.
TIMER_INPUT_PINS = frozenset({"IN"})
TIMER_OUTPUT_PINS = frozenset({"Q", "ET"})
_IEC_IDENTIFIER = re.compile(r"[A-Za-z_]\w*")
# A member read such as `%TM2.Q`; a numeric suffix (`%I0.1`) is an address.
_MEMBER = re.compile(r"(.+)\.([A-Za-z_]\w*)")


def split_member(operand: str) -> tuple[str, str] | None:
    """`(root, member)` for a member read whose root is not an IEC identifier."""
    match = _MEMBER.fullmatch(operand)
    if match is None or _IEC_IDENTIFIER.fullmatch(match.group(1)):
        return None
    return match.group(1), match.group(2)


def instructions(series: LadderSeries) -> list[LadderInstruction]:
    found: list[LadderInstruction] = []
    for element in series.elements:
        if isinstance(element, LadderParallel):
            for branch in element.branches:
                found.extend(instructions(branch))
        else:
            found.append(element)
    return found


def unsupported_reason(series: LadderSeries, block_types: Mapping[str, str] | None = None) -> str | None:
    """Why this network cannot be emitted as executable LD, or None.

    `block_types` maps each convertible function block instance to its IEC
    type; block pins and member reads of anything else are unsupported.
    """
    block_types = block_types or {}
    if not instructions(series):
        return "network has no instructions"
    for instruction in instructions(series):
        operand = instruction.operand
        if not operand:
            return f"{instruction.source_mnemonic} has no operand"
        if instruction.operation in (LadderOperation.FUNCTION_BLOCK_INPUT, LadderOperation.BLOCK_OUTPUT_REFERENCE):
            instance, _, pin = operand.rpartition(".")
            if instance not in block_types:
                return f"{instruction.source_mnemonic} {instance} is not a convertible function block instance"
            pins = TIMER_INPUT_PINS if instruction.operation is LadderOperation.FUNCTION_BLOCK_INPUT                 else TIMER_OUTPUT_PINS
            if pin not in pins:
                return f"{instruction.source_mnemonic} pin {pin} has no IEC {block_types[instance]} equivalent"
            continue
        if instruction.operation not in ENCODINGS:
            return f"{instruction.source_mnemonic} ({instruction.operation.value}) has no PLCopen LD encoding"
        member = split_member(operand)
        if member is not None and member[0] not in block_types:
            return f"{operand} reads a member of {member[0]}, which is not a convertible function block instance"
        # Contacts and coils are BOOL; of a timer's members only Q is.
        if member is not None and member[1] != "Q":
            return f"{operand} is not a BOOL member of {block_types[member[0]]}"
    return None


def describe(series: LadderSeries) -> str:
    """A compact, deterministic rendering kept in the comment of an unsupported rung."""
    parts: list[str] = []
    for element in series.elements:
        if isinstance(element, LadderParallel):
            parts.append("[" + " | ".join(describe(branch) for branch in element.branches) + "]")
        else:
            parts.append(f"{element.source_mnemonic}({element.operand or ''})")
    return " ".join(parts)
