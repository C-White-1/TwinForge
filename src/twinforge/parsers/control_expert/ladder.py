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
an `FFBBlock`'s own anchor row (`objPosition posY`, nothing but empty cells
between the wire and the block). That always targets the block's first
*wireable* input: `EN` when `enEnO="true"` (Schneider always lists it
first); when `enEnO="false"`, `EN`/`ENO` are declared but never rendered at
all, so the anchor row instead lands on the second declared input (e.g.
`S1` for an `SR` block) -- confirmed against the vendor's own PDF rendering
of a real `SR` block (`S1`/`Q1` share the block's top row; no separate
`EN`/`ENO` row exists when they are hidden). This is deliberately not the
vendor's documented "Short Circuit Evaluation" bypass-and-passthrough
semantics (product-help.se.com, "Parallel Branch", EIO0000002854.00): no
fixture in the corpus shows that shape (parallel branches where one carries
a block and another only contacts, merging to a shared point). Every real
`shortCircuit` observed instead feeds one pin directly, evidenced by exact
`objPosition` column/row matches recomputed from the grid.

A `shortCircuit` can also wrap an `FFBBlock` directly
(`<shortCircuit><VLink/><FFBBlock/></shortCircuit>`) instead of a
contact/`HLink`: the wire terminates on the block right there, in the same
element, with no "does it continue past" ambiguity to confirm (unlike the
far-arriving case above). Real evidence distinguishes this cleanly from an
unconnected block: a bare, unwrapped `FFBBlock` (no `shortCircuit` at all)
never binds (`sayahali_conveyor_ali_conv.zef`'s `SR_8`/`SR_9`), while every
`shortCircuit`-wrapped one does (`SR_2`/`SR_3`/`SR_4`/`SR_5`/`SR_7`).

A wire that keeps a `VLink` alive at the same column one row past its
candidate landing is left unresolved: real evidence (Escalier_Mecanique.XEF's
escalator and function15/function2's MBP_MSTR_7 rung) shows this shape
exists but its target is genuinely ambiguous -- it may be a multi-row
block's second input, or merely the block's own border rendered with the
same element, and nothing in the corpus disambiguates the two.

An `FFBBlock` always occupies exactly two grid columns regardless of its
type or pin count (pin count instead grows its row span, already handled
via `objPosition posY`). Confirmed by measuring every real ladder network
across six independent projects (Escalier_Mecanique.XEF, its ZEF sibling,
MultiGrafcet_Coordination_V1_2026.XEF and its sibling, function15.zip and
function2.zip): every row's leading-plus-trailing cell count around an
`FFBBlock` sums to exactly `nbColumns - 2` for that network's declared
`LDSource nbColumns`, for every block type observed (TON, SET, RESET, ADD,
MBP_MSTR) and every pin count from 1 to 6. `nbColumns="11"` itself is
identical across the whole corpus.
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
# Real evidence: see the module docstring. Constant across every block type
# and pin count observed; pin count grows row span, not column width.
_FFB_BLOCK_WIDTH = 2

_COIL_OPERATIONS = {
    "coil": LadderOperation.COIL,
    "resetCoil": LadderOperation.RESET_COIL,
    # Real evidence: github.com/sayahali/conveyor-automation's real M340
    # export uses "setCoil" (4 occurrences), the natural counterpart to the
    # already-evidenced "resetCoil" -- LadderOperation.SET_COIL already
    # existed in the model but this mnemonic was simply missing here.
    "setCoil": LadderOperation.SET_COIL,
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

    def landing_pin_name(block: CapturedSection) -> str | None:
        # Real evidence: an enEnO="true" block's own anchor row always lands
        # on EN, since it is always listed first (already evidenced). New
        # evidence (real corpus SR instances, cross-checked against the
        # vendor's own PDF rendering of SR_4: S1 and Q1 share the block's
        # top row, no separate EN/ENO row at all): when enEnO="false", EN
        # is declared but never rendered, so the block's anchor row instead
        # lands on the second declared input -- S1 for an SR block.
        description = next((c for c in block.ordered_children if c.tag == "descriptionFFB"), None)
        inputs = [c for c in description.ordered_children if c.tag == "inputVariable"] \
            if description is not None else []
        if not inputs or inputs[0].raw_attributes.get("formalParameter") != "EN":
            return None
        if block.raw_attributes.get("enEnO") == "true":
            return "EN"
        if block.raw_attributes.get("enEnO") == "false" and len(inputs) >= 2:
            return inputs[1].raw_attributes.get("formalParameter")
        return None

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
                    elif len(vlinks) == 1 and len(others) == 1 and others[0].tag == "FFBBlock":
                        # Real evidence: the wire terminates on the block
                        # directly, wrapped in the same element -- not a
                        # separate continuation to confirm past this row,
                        # unlike the far-arriving VLink-chain case below.
                        block = others[0]
                        position_node = next((c for c in block.ordered_children if c.tag == "objPosition"), None)
                        posx = position_node.raw_attributes.get("posX") if position_node is not None else None
                        posy = position_node.raw_attributes.get("posY") if position_node is not None else None
                        pin_name = landing_pin_name(block)
                        if (pin_name is not None and posx is not None and posx.isascii() and posx.isdecimal()
                                and posy is not None and posy.isascii() and posy.isdecimal() and int(posy) == row):
                            bindings.append(LadderPinCondition(
                                network_index=network_index,
                                position=LadderPosition(column=int(posx), row=row),
                                pin_name=pin_name, condition=LadderSeries(elements=tuple(pending_contacts)),
                            ))
                        markers.add(column)
                        column += _FFB_BLOCK_WIDTH
                    else:
                        report("unresolved_ladder_short_circuit",
                               "shortCircuit does not match the evidenced VLink+contact/HLink/FFBBlock shape", child)
                        markers.add(column)
                        column += 1
                    pending_contacts = []
                elif child.tag == "FFBBlock":
                    block_start = column
                    position_node = next((c for c in child.ordered_children if c.tag == "objPosition"), None)
                    posx = position_node.raw_attributes.get("posX") if position_node is not None else None
                    posy = position_node.raw_attributes.get("posY") if position_node is not None else None
                    pin_name = landing_pin_name(child)
                    if (pin_name is not None and posx is not None and posx.isascii() and posx.isdecimal()
                            and posy is not None and posy.isascii() and posy.isdecimal() and int(posy) == row):
                        target_column = int(posx)
                        for wire_column in list(active):
                            if wire_column >= target_column:
                                continue
                            clean = not any(wire_column < marker < target_column for marker in markers)
                            if clean:
                                pending.append((
                                    wire_column, row, LadderPosition(column=target_column, row=row),
                                    list(active[wire_column]), pin_name,
                                ))
                    # Real evidence (module docstring): a block always spans
                    # exactly two columns, so scanning can continue past it
                    # instead of abandoning the rest of the row. Its own
                    # footprint is marked so a later element's clean-gap
                    # check cannot jump across it.
                    markers.add(block_start)
                    pending_contacts = []
                    column = block_start + _FFB_BLOCK_WIDTH
                else:
                    pending_contacts = []

            # A column not touched by a marker this row (including one
            # carried through an FFBBlock's now-known footprint) has died.
            for wire_column in [c for c in active if c not in continued]:
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
