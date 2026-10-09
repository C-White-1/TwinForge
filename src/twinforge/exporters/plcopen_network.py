"""Decide how a neutral ladder network maps onto PLCopen LD elements.

`LadderRung.network` (Control Expert, Machine Expert – Basic, CCW) is a
series/parallel tree; PLCopen LD is a connection graph in which each element
lists the localIds feeding it, several references meaning a wired OR. Every
`LadderOperation` below has a direct TC6 encoding on `contact` or `coil`
(attributes `negated`, `edge`, `storage`; tc6_xml_v201.xsd). Anything else,
including `UNSUPPORTED` and `BLOCK_OUTPUT_REFERENCE`, has none yet, so a
rung containing it is preserved as a comment rather than approximated.
"""

from __future__ import annotations

from dataclasses import dataclass

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


def instructions(series: LadderSeries) -> list[LadderInstruction]:
    found: list[LadderInstruction] = []
    for element in series.elements:
        if isinstance(element, LadderParallel):
            for branch in element.branches:
                found.extend(instructions(branch))
        else:
            found.append(element)
    return found


def unsupported_reason(series: LadderSeries) -> str | None:
    """Why this network cannot be emitted as executable LD, or None."""
    if not instructions(series):
        return "network has no instructions"
    for instruction in instructions(series):
        if instruction.operation not in ENCODINGS:
            return f"{instruction.source_mnemonic} ({instruction.operation.value}) has no PLCopen LD encoding"
        if not instruction.operand:
            return f"{instruction.source_mnemonic} has no operand"
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
