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

`resolve_ladder_pin_conditions` below resolves one further, narrower case
from the same grid: a `shortCircuit`-marked vertical bus, continuing through
bare `VLink` at the same column across further rows, that lands cleanly on
an `FFBBlock`'s own anchor row (`objPosition posY`, `enEnO="true"`, nothing
but empty cells between the wire and the block). That always targets the
`EN` pin, since Schneider always lists it first. This is deliberately not
the vendor's documented "Short Circuit Evaluation" bypass-and-passthrough
semantics (product-help.se.com, "Parallel Branch", EIO0000002854.00): no
fixture in the corpus shows that shape (parallel branches where one carries
a block and another only contacts, merging to a shared point). Every real
`shortCircuit` observed instead feeds one pin directly, evidenced by exact
`objPosition` column/row matches recomputed from the grid. A wire that keeps
a `VLink` alive at the same column one row past its candidate landing is
left unresolved: real evidence (Escalier_Mecanique.XEF's escalator and
function15/function2's MBP_MSTR_7 rung) shows this shape exists but its
target is genuinely ambiguous -- it may be a multi-row block's second input,
or merely the block's own border rendered with the same element, and
nothing in the corpus disambiguates the two.
"""
from twinforge.model import (
    LadderInstruction, LadderOperation, LadderPinCondition, LadderPosition, LadderRung, LadderSeries,
)

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


def resolve_ladder_pin_conditions(source: CapturedSection) -> tuple[list[LadderPinCondition], list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    bindings: list[LadderPinCondition] = []

    def report(code: str, message: str, node: CapturedSection) -> None:
        diagnostics.append(Diagnostic(code, message, node.source))

    def cells(node: CapturedSection) -> int | None:
        value = node.raw_attributes.get("nbCells")
        if value is None:
            return 0
        if not value.isascii() or not value.isdecimal():
            return None
        return int(value)

    def contact_instruction(node: CapturedSection, column: int, row: int) -> LadderInstruction:
        attrs = node.raw_attributes
        mnemonic = attrs.get("typeContact", "")
        operand = attrs.get("contactVariableName")
        # Not re-diagnosed here: parse_ladder_rungs already reports this for
        # every contact in the grid (this function only adds a new,
        # narrower diagnostic for the shortCircuit shape itself).
        operation = _CONTACT_OPERATIONS.get(mnemonic, LadderOperation.UNSUPPORTED)
        return LadderInstruction(operation=operation, source_mnemonic=mnemonic, operand=operand,
                                  position=LadderPosition(column=column, row=row))

    for network_index, network in enumerate(c for c in source.ordered_children if c.tag == "networkLD"):
        row = 0
        # column -> condition accumulated so far for a still-alive vertical wire.
        active: dict[int, list[LadderInstruction]] = {}
        # row -> columns carrying a VLink (bare or shortCircuit-originated) in that row.
        row_markers: dict[int, set[int]] = {}
        # (wire_column, landing_row, target_position, condition, pin_name) not yet confirmed.
        pending: list[tuple[int, int, LadderPosition, list[LadderInstruction], str]] = []

        for line in network.ordered_children:
            if line.tag != "typeLine":
                continue
            children = line.ordered_children
            if len(children) == 1 and children[0].tag == "emptyLine":
                skip = children[0].raw_attributes.get("nbRows", "")
                if skip.isascii() and skip.isdecimal():
                    row += int(skip)
                # No evidence a wire survives a blank/skipped span -- nothing
                # is drawn there to carry it. Already-recorded candidates are
                # unaffected; they are confirmed from row_markers, not `active`.
                active.clear()
                continue

            column = 0
            pending_contacts: list[LadderInstruction] = []
            markers: set[int] = set()  # every column with a "real" element, for the clean-gap check
            continued: set[int] = set()  # columns whose wire is carried into the next row
            ffb_column: int | None = None
            target_column: int | None = None

            for child in children:
                if child.tag in {"emptyCell", "HLink"}:
                    width = cells(child)
                    if width is None:
                        # Not re-diagnosed here: parse_ladder_rungs already
                        # reports this for every cell in the grid.
                        break
                    column += width
                elif child.tag == "contact":
                    pending_contacts.append(contact_instruction(child, column, row))
                    markers.add(column)
                    column += 1
                elif child.tag == "coil":
                    markers.add(column)
                    pending_contacts = []
                    column += 1
                elif child.tag == "VLink":
                    markers.add(column)
                    if column in active:
                        continued.add(column)
                    pending_contacts = []
                    column += 1
                elif child.tag == "shortCircuit":
                    grandchildren = child.ordered_children
                    vlinks = [g for g in grandchildren if g.tag == "VLink"]
                    others = [g for g in grandchildren if g.tag != "VLink"]
                    if len(vlinks) == 1 and len(others) == 1 and others[0].tag in {"contact", "HLink"}:
                        real = others[0]
                        width = 1 if real.tag == "contact" else cells(real)
                        if width is not None and width >= 1:
                            tie_column = column + width - 1
                            condition = list(pending_contacts)
                            if real.tag == "contact":
                                condition.append(contact_instruction(real, tie_column, row))
                            active[tie_column] = condition
                            markers.add(tie_column)
                            continued.add(tie_column)
                            column += width
                        else:
                            column += 1
                    else:
                        report("unresolved_ladder_short_circuit",
                               "shortCircuit does not match the evidenced VLink+contact/HLink shape", child)
                        markers.add(column)
                        column += 1
                    pending_contacts = []
                elif child.tag == "FFBBlock":
                    ffb_column = column
                    position_node = next((c for c in child.ordered_children if c.tag == "objPosition"), None)
                    posx = position_node.raw_attributes.get("posX") if position_node is not None else None
                    posy = position_node.raw_attributes.get("posY") if position_node is not None else None
                    description = next((c for c in child.ordered_children if c.tag == "descriptionFFB"), None)
                    first_input = next((c for c in description.ordered_children if c.tag == "inputVariable"), None) \
                        if description is not None else None
                    is_en = (first_input is not None
                             and first_input.raw_attributes.get("formalParameter") == "EN")
                    if (posx is not None and posx.isascii() and posx.isdecimal()
                            and posy is not None and posy.isascii() and posy.isdecimal()
                            and int(posy) == row and child.raw_attributes.get("enEnO") == "true" and is_en):
                        target_column = int(posx)
                        for wire_column in list(active):
                            if wire_column >= target_column:
                                continue
                            clean = not any(wire_column < marker < target_column for marker in markers)
                            if clean:
                                pending.append((
                                    wire_column, row, LadderPosition(column=target_column, row=row),
                                    list(active[wire_column]), "EN",
                                ))
                    break
                else:
                    pending_contacts = []

            # A column not touched by a marker this row has died, unless it
            # sits at or past a block we stopped scanning at -- its own grid
            # width is not tracked, so what lies beyond it is unknown rather
            # than dead (real evidence: the wire beside RESET in the corpus
            # genuinely continues past it to SET two rows later).
            boundary = target_column if target_column is not None else ffb_column
            for wire_column in [c for c in active if c not in continued
                                 and (boundary is None or c < boundary)]:
                del active[wire_column]
            row_markers[row] = markers
            row += 1

        for wire_column, landing_row, position, condition, pin_name in pending:
            if wire_column in row_markers.get(landing_row + 1, set()):
                # The same column carries a vertical wire one row past its
                # candidate landing; real evidence (MBP_MSTR_7 in the
                # corpus) shows this shape exists but its true target stays
                # ambiguous (a second input row, or just the block's own
                # border) -- leave it unresolved rather than guess.
                continue
            bindings.append(LadderPinCondition(
                network_index=network_index, position=position, pin_name=pin_name,
                condition=LadderSeries(elements=tuple(condition)),
            ))

    # Two wires cleanly reaching the same pin in the same row is not
    # evidenced anywhere in the corpus; do not silently pick one.
    seen: dict[tuple[int, LadderPosition, str], int] = {}
    ambiguous: set[tuple[int, LadderPosition, str]] = set()
    for binding in bindings:
        key = (binding.network_index, binding.position, binding.pin_name)
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:
            ambiguous.add(key)
    if ambiguous:
        bindings = [b for b in bindings
                    if (b.network_index, b.position, b.pin_name) not in ambiguous]

    return bindings, diagnostics
