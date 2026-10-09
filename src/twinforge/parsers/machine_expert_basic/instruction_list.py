"""Build a rung's `LadderSeries` network from its Machine Expert - Basic Instruction List.

For rungs written in IL, with no ladder grid (docs/roadmaps/machine-expert-basic-roadmap.md).
The IL is replayed like an interpreter, except that the accumulator holds a
ladder condition (a list of series elements) instead of a boolean:

- `LD`/`AND`/`OR` (and `N`, `R`, `F` forms, `[ comparison ]` operands)
  build contacts, series and parallels; `AND(` ... `)` nests;
- `MPS`/`MRD`/`MPP` save and restore the condition at a branch point;
- `ST`/`STN`/`S`/`R` and `[ assignment ]` record an output whose full
  condition is the current accumulator;
- `BLK x` ... `OUT_BLK` ... `END_BLK` calls a block: a bare pin name
  (`IN`, `CU`) is an input-pin sink, and `LD Q` after `OUT_BLK` reads the
  block output, following the grid conventions in `ladder.py`.

Each output ends up with its full path from the rail. Paths share element
objects wherever the IL shares a condition (an accumulator extended after
`ST`, or restored by `MRD`/`MPP`), so factoring common prefixes by identity
rebuilds the branch structure: shared conditions, then a parallel of output
branches, the shape grid rungs already have.

Anything not listed raises `NetworkUnresolved`; the rung then keeps only its
IL text (`LadderRung.instruction_list`) rather than a guessed network.
"""
from __future__ import annotations

from collections.abc import Mapping
import re

from twinforge.model import LadderInstruction, LadderOperation, LadderParallel, LadderSeries
from twinforge.schema.machine_expert_basic.ladder import LADDER_SPEC, LadderSpec

from .expression import expression_instruction
from .ladder import NetworkUnresolved, declared_name

Element = LadderInstruction | LadderParallel

_CONDITION_FORMS = {
    "": (LadderOperation.NORMALLY_OPEN_CONTACT, "NormalContact"),
    "N": (LadderOperation.NORMALLY_CLOSED_CONTACT, "NegatedContact"),
    "R": (LadderOperation.POSITIVE_TRANSITION_CONTACT, "RisingEdge"),
    "F": (LadderOperation.NEGATIVE_TRANSITION_CONTACT, "FallingEdge"),
}
_OUTPUTS = {
    "ST": (LadderOperation.COIL, "Coil"),
    "STN": (LadderOperation.NEGATED_COIL, "NegativeCoil"),
    "S": (LadderOperation.SET_COIL, "SetCoil"),
    "R": (LadderOperation.RESET_COIL, "ResetCoil"),
}
_LOGIC = re.compile(r"^(LD|AND|OR)(N|R|F)?(\(N?)?$")


def _unresolved(message: str) -> NetworkUnresolved:
    return NetworkUnresolved("instruction_list_not_converted", message)


def build_network_from_instruction_list(
    lines: list[str], symbols: Mapping[str, str] | None = None, spec: LadderSpec = LADDER_SPEC,
) -> LadderSeries:
    symbols = symbols or {}

    def named(address: str) -> tuple[str, tuple[str, ...]]:
        name, annotations = declared_name(address, symbols)
        return name or address, annotations

    def instruction(operation: LadderOperation, mnemonic: str, operand: str | None,
                    annotations: tuple[str, ...] = ()) -> LadderInstruction:
        if operand is not None and operand.startswith("%"):
            operand, address = named(operand)
            annotations = annotations + address
        return LadderInstruction(operation=operation, source_mnemonic=mnemonic, operand=operand,
                                 annotations=annotations)

    def block_type(address: str) -> str:
        for prefix in sorted(spec.block_prefixes, key=len, reverse=True):
            if address.startswith(prefix):
                return spec.block_prefixes[prefix]
        raise _unresolved(f"block {address!r} has no known type")

    def operand_element(form: str, operand: str) -> list[Element]:
        """The series elements one condition operand contributes."""
        if operand == "1" and form == "":
            return []  # always true: a bare wire
        if operand.startswith("["):
            if form:
                raise _unresolved(f"comparison with modifier {form!r} is not supported")
            return [expression_instruction(_bracketed(operand), "Comparison", symbols, spec=spec)]
        if block is not None and after_out and not operand.startswith("%"):
            block_name, address = named(block)
            return [LadderInstruction(operation=LadderOperation.BLOCK_OUTPUT_REFERENCE,
                                      source_mnemonic=block_type(block), operand=f"{block_name}.{operand}",
                                      annotations=address)]
        if not operand.startswith("%"):
            raise _unresolved(f"operand {operand!r} is not an address")
        operation, mnemonic = _CONDITION_FORMS[form]
        return [instruction(operation, mnemonic, operand)]

    acc: list[Element] = []
    parens: list[tuple[list[Element], str]] = []
    branch_points: list[list[Element]] = []
    outputs: list[list[Element]] = []
    block: str | None = None
    after_out = False

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("[") or line.startswith("OPER"):
            text = _bracketed(line[4:] if line.startswith("OPER") else line)
            outputs.append(acc + [expression_instruction(text, "Operation", symbols, spec=spec)])
            continue
        if line == ")":
            if not parens:
                raise _unresolved("unbalanced ')'")
            previous, kind = parens.pop()
            acc = previous + acc if kind == "AND" else [_or(previous, acc)]
            continue
        parts = line.split(None, 1)
        op, arg = parts[0], (parts[1].strip() if len(parts) > 1 else "")
        if op == "BLK":
            block, after_out = arg, False
            block_type(arg)
            continue
        if op == "OUT_BLK" and block is not None:
            after_out = True
            continue
        if op == "END_BLK" and block is not None:
            block = None
            continue
        if block is not None and not after_out and not arg and op not in ("MPS", "MRD", "MPP", "N"):
            block_name, address = named(block)
            outputs.append(acc + [LadderInstruction(
                operation=LadderOperation.FUNCTION_BLOCK_INPUT, source_mnemonic=block_type(block),
                operand=f"{block_name}.{op}", annotations=address)])
            continue
        if op == "MPS":
            branch_points.append(list(acc))
            continue
        if op in ("MRD", "MPP"):
            if not branch_points:
                raise _unresolved(f"{op} without MPS")
            acc = list(branch_points[-1] if op == "MRD" else branch_points.pop())
            continue
        if op == "N" and not arg:
            acc = acc + [instruction(LadderOperation.UNSUPPORTED, "Not", None)]
            continue
        if op == "XOR" and arg.startswith("%"):
            acc = acc + [instruction(LadderOperation.UNSUPPORTED, "Xor", arg)]
            continue
        if op in _OUTPUTS and arg.startswith("%"):
            operation, mnemonic = _OUTPUTS[op]
            outputs.append(acc + [instruction(operation, mnemonic, arg)])
            continue
        if op.startswith("AND(N"):
            op, arg = "AND(", "N " + arg
        match = _LOGIC.match(op)
        if not match:
            raise _unresolved(f"instruction {line!r} is not supported")
        base, form, paren = match.group(1), match.group(2) or "", match.group(3)
        if arg.startswith("N "):
            form, arg = "N", arg[2:].strip()
        operand = operand_element(form, arg)
        if paren:
            if base == "LD":
                raise _unresolved(f"instruction {line!r} is not supported")
            parens.append((acc, base))
            acc = operand
        elif base == "LD":
            acc = operand
        elif base == "AND":
            acc = acc + operand
        else:
            acc = [_or(acc, operand)]

    if parens or branch_points or block is not None:
        raise _unresolved("Instruction List ends inside a bracket, branch or block")
    if not outputs:
        raise _unresolved("Instruction List has no output")
    return LadderSeries(tuple(_factor(outputs)))


def _bracketed(text: str) -> str:
    """The text inside an IL `[ ... ]` box."""
    return text.strip().removeprefix("[").removesuffix("]").strip()



def _or(first: list[Element], second: list[Element]) -> LadderParallel:
    return LadderParallel((LadderSeries(tuple(first)), LadderSeries(tuple(second))))


def _factor(paths: list[list[Element]]) -> list[Element]:
    """Merge output paths that share leading elements (by identity) into branches."""
    elements: list[Element] = []
    while all(paths) and len(paths) > 1 and all(path[0] is paths[0][0] for path in paths):
        elements.append(paths[0][0])
        paths = [path[1:] for path in paths]
    if len(paths) == 1:
        return elements + paths[0]
    groups: list[list[list[Element]]] = []
    for path in paths:
        for group in groups:
            if group[0] and path and group[0][0] is path[0]:
                group.append(path)
                break
        else:
            groups.append([path])
    branches = tuple(LadderSeries(tuple(_factor(group))) for group in groups)
    return elements + [LadderParallel(branches)]
