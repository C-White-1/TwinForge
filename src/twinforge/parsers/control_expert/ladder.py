"""Resolve pure-series Ladder rungs from grid evidence; branches stay diagnosed.

Each `typeLine` under a `networkLD` is one grid row (`emptyLine[nbRows]`
advances the row counter without occupying one -- verified against real
`FFBBlock`/`objPosition` row values in the corpus). Column position is the
cumulative cell width consumed left to right (`emptyCell`/`HLink` by their
`nbCells`, a contact or coil by exactly one cell -- neither carries its own
coordinate). A row resolves only when it contains nothing but contacts,
optionally an `HLink`/`emptyCell`, and exactly one coil as its last
cell-bearing element: that is an unambiguous series-AND rung. Any row
touching `shortCircuit`, `VLink`, `FFBBlock` or `textBox` involves vertical
wiring whose destination can span many rows to a distant block (observed in
the corpus) or a branch merge -- neither rule is evidenced yet, so such rows
are diagnosed by name and never guessed at.
"""
from twinforge.model import LadderInstruction, LadderOperation, LadderPosition, LadderRung, LadderSeries

from .capture import CapturedSection, Diagnostic
from .evidence import source_extension as _extension

_CONTACT_OPERATIONS = {
    "openContact": LadderOperation.NORMALLY_OPEN_CONTACT,
    "closedContact": LadderOperation.NORMALLY_CLOSED_CONTACT,
}
_COIL_OPERATIONS = {
    "coil": LadderOperation.COIL,
    "resetCoil": LadderOperation.RESET_COIL,
}


def parse_ladder_rungs(source: CapturedSection) -> tuple[list[LadderRung], list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    rungs: list[LadderRung] = []

    def report(code: str, message: str, node: CapturedSection) -> None:
        diagnostics.append(Diagnostic(code, message, node.source))

    def cells(node: CapturedSection) -> int | None:
        value = node.raw_attributes.get("nbCells")
        if value is None:
            return 0
        if not value.isascii() or not value.isdecimal():
            report("invalid_ladder_number", f"nbCells={value!r} is not a nonnegative integer", node)
            return None
        return int(value)

    for network in source.ordered_children:
        if network.tag != "networkLD":
            continue
        row = 0
        for line in network.ordered_children:
            if line.tag == "textBox":
                continue
            if line.tag != "typeLine":
                report("unclassified_ladder_content", "Unknown network content retained", line)
                continue
            children = line.ordered_children
            if len(children) == 1 and children[0].tag == "emptyLine":
                skip = children[0].raw_attributes.get("nbRows", "")
                if skip.isascii() and skip.isdecimal():
                    row += int(skip)
                else:
                    report("invalid_ladder_number", f"nbRows={skip!r} is not a nonnegative integer", children[0])
                continue
            column = 0
            elements: list[tuple[CapturedSection, int]] = []
            resolvable = True
            for child in children:
                if child.tag in {"emptyCell", "HLink"}:
                    width = cells(child)
                    if width is None:
                        resolvable = False
                    else:
                        column += width
                elif child.tag in {"contact", "coil"}:
                    elements.append((child, column))
                    column += 1
                else:
                    # shortCircuit, VLink, FFBBlock, textBox or unknown: vertical
                    # wiring or a block whose connection rule is not evidenced.
                    resolvable = False
            if not resolvable:
                report("unresolved_ladder_row",
                       "Row involves branch/link/block wiring; connectivity not evidenced", line)
            elif elements:
                coil_positions = [i for i, (node, _) in enumerate(elements) if node.tag == "coil"]
                if not coil_positions:
                    report("ladder_series_missing_coil", "Series row has no coil; not a complete rung", line)
                elif coil_positions != [len(elements) - 1]:
                    report("ladder_series_unexpected_coil_position",
                           "Row must have exactly one coil, as its last element", line)
                else:
                    instructions = []
                    for node, node_column in elements:
                        attrs = node.raw_attributes
                        if node.tag == "contact":
                            mnemonic = attrs.get("typeContact", "")
                            operand = attrs.get("contactVariableName")
                            operation = _CONTACT_OPERATIONS.get(mnemonic)
                        else:
                            mnemonic = attrs.get("typeCoil", "")
                            operand = attrs.get("coilVariableName")
                            operation = _COIL_OPERATIONS.get(mnemonic)
                        if operation is None:
                            operation = LadderOperation.UNSUPPORTED
                            report("unresolved_ladder_instruction",
                                   f"{node.tag} type {mnemonic!r} has no portable meaning; retained as evidence", node)
                        instructions.append(LadderInstruction(
                            operation=operation, source_mnemonic=mnemonic, operand=operand,
                            position=LadderPosition(column=node_column, row=row),
                        ))
                    rungs.append(LadderRung(
                        number=row, position=LadderPosition(column=0, row=row),
                        network=LadderSeries(elements=tuple(instructions)),
                        source_extensions=[_extension(line)],
                    ))
            row += 1
    return rungs, diagnostics
