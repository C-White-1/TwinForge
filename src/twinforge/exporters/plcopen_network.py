"""Decide how a neutral ladder network maps onto PLCopen LD elements.

`LadderRung.network` (Control Expert, Machine Expert – Basic, CCW) is a
series/parallel tree; PLCopen LD is a connection graph in which each element
lists the localIds feeding it, several references meaning a wired OR. Every
`LadderOperation` in `ENCODINGS` has a direct TC6 encoding on `contact` or
`coil` (attributes `negated`, `edge`, `storage`; tc6_xml_v201.xsd).

`FUNCTION_BLOCK_INPUT` and `BLOCK_OUTPUT_REFERENCE` become a TC6 `block` in
the same graph, but only for instances the caller declares convertible
(`blocks`: an IEC timer with a known PT, or a TwinForge-generated block) and
only on that block's own pins.
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


# Expression instructions are emitted as IEC standard functions over these types.
EXPRESSION_TYPES = frozenset({"INT", "DINT", "REAL", "BOOL"})
EXPRESSION_OPERATIONS = frozenset({LadderOperation.COMPARISON, LadderOperation.ASSIGNMENT})
# Operations that store something; a network with none of them has no effect.
OUTPUT_OPERATIONS = frozenset({
    LadderOperation.COIL, LadderOperation.SET_COIL, LadderOperation.RESET_COIL, LadderOperation.NEGATED_COIL,
    LadderOperation.FUNCTION_BLOCK_INPUT, LadderOperation.ASSIGNMENT,
})
# A shift acts on a bit string: the integer is converted to the bit string of
# its width, shifted, and converted back. IEC conversions between an integer
# and a bit string copy the bits, so this is the source's word operation.
BIT_STRING_TYPES = {"INT": "WORD", "DINT": "DWORD"}
# IEC 61131-3 standard function per operator.
FUNCTION_BLOCK_TYPES = {
    "+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV",
    "=": "EQ", "<>": "NE", "<": "LT", ">": "GT", "<=": "LE", ">=": "GE",
}

@dataclass(frozen=True)
class BlockInterface:
    """How one convertible function block instance appears in LD.

    `inputs`/`outputs` are the block's pins in declaration order; `constants`
    are inputs fed from a literal (a timer's PT, a counter's PV) rather than
    the rung; `bool_outputs` are the outputs a contact may read. `in_outs`
    binds each in-out parameter to the variable it writes in place (a
    drum's outputs). `standard` marks an IEC standard library block
    (CODESYS `Standard.`), as opposed to a TwinForge-generated one.
    """

    type_name: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    bool_outputs: frozenset[str]
    constants: tuple[tuple[str, str], ...] = ()
    standard: bool = True
    in_outs: tuple[tuple[str, str], ...] = ()

    @property
    def wired_inputs(self) -> frozenset[str]:
        constant = {pin for pin, _ in self.constants}
        return frozenset(pin for pin in self.inputs if pin not in constant)


def timer_interface(type_name: str, preset: str) -> BlockInterface:
    """IEC 61131-3 TON/TOF/TP: IN, PT -> Q, ET."""
    return BlockInterface(type_name, ("IN", "PT"), ("Q", "ET"), frozenset({"Q"}), (("PT", preset),))


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


def unsupported_reason(series: LadderSeries, blocks: Mapping[str, BlockInterface] | None = None) -> str | None:
    """Why this network cannot be emitted as executable LD, or None.

    `blocks` maps each convertible function block instance to its interface;
    block pins and member reads of anything else are unsupported.
    """
    blocks = blocks or {}
    if not instructions(series):
        return "network has no instructions"
    for instruction in instructions(series):
        operand = instruction.operand
        if instruction.operation in EXPRESSION_OPERATIONS:
            expression = instruction.expression
            if expression is None:
                return f"{instruction.source_mnemonic} has no expression"
            untyped = [node.text or node.operator for node in expression.iter_nodes()
                       if node.data_type not in EXPRESSION_TYPES]
            if untyped:
                return f"{instruction.source_mnemonic} expression has untyped parts {untyped}"
            continue
        if not operand:
            return f"{instruction.source_mnemonic} has no operand"
        if instruction.operation in (LadderOperation.FUNCTION_BLOCK_INPUT, LadderOperation.BLOCK_OUTPUT_REFERENCE):
            instance, _, pin = operand.rpartition(".")
            if instance not in blocks:
                return f"{instruction.source_mnemonic} {instance} is not a convertible function block instance"
            interface = blocks[instance]
            pins = interface.wired_inputs if instruction.operation is LadderOperation.FUNCTION_BLOCK_INPUT \
                else frozenset(interface.outputs)
            if pin not in pins:
                return f"{instruction.source_mnemonic} pin {pin} has no {interface.type_name} equivalent"
            continue
        if instruction.operation not in ENCODINGS:
            return f"{instruction.source_mnemonic} ({instruction.operation.value}) has no PLCopen LD encoding"
        member = split_member(operand)
        if member is not None and member[0] not in blocks:
            return f"{operand} reads a member of {member[0]}, which is not a convertible function block instance"
        # Contacts and coils are BOOL; only a block's BOOL outputs can be read.
        if member is not None and member[1] not in blocks[member[0]].bool_outputs:
            return f"{operand} is not a BOOL output of {blocks[member[0]].type_name}"
    if not any(instruction.operation in OUTPUT_OPERATIONS for instruction in instructions(series)):
        # Emitted, it would be a rung ending in a right rail nothing reaches.
        return "network has no output"
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
