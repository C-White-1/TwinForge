"""Render vendor-neutral ladder rungs as deterministic SVG markup.

Renders `model/ladder.py`'s `LadderRung`/`LadderSeries`/`LadderInstruction`
directly -- never a source format's raw captured XML -- so this works for
any producer of that model (Control Expert today; CCW/L5X wherever their
own ladder conversion already populates the same types). Text-in/text-out,
like `aoi_plantuml.py`: no image-library dependency, output is plain SVG a
browser renders natively and source control can diff.

Milestone 1 of the visualization roadmap
(docs/roadmaps/graphical-diagram-visualization-roadmap.md): a flat
`LadderSeries` of `LadderInstruction` (Control Expert's own parser never
produces anything else today). A `LadderParallel` branch is rendered as an
explicit "not yet supported" placeholder, not guessed at -- silently
skipping it would misrepresent a real branch as absent.

Milestone 2 (`export_diagram` below): renders a full `GraphicalDiagram` --
every `FFBBlock` and `shortCircuit`/`VLink`/bare-wire row the model didn't
used to position at all, via `GraphicalDiagram.grid_rows`/`LadderGridCell`
(`model/graphical.py`, `parsers/control_expert/ladder.py::compute_ld_grid`).
Per the roadmap's own explicit non-goal, this does not attempt pixel-perfect
replication of Control Expert's own rendering (exact dogleg corner
placement, bus-tap column geometry): a `shortCircuit`/bare `VLink` draws as
a plain vertical connector through the row, not the precise multi-segment
routing a real ad hoc verification renderer worked out over one long
session (never committed) -- correct and readable, not a vendor UI clone.
Block pin ROW placement, unlike wire routing, is NOT a styling choice: it
reuses the confirmed real offsets (`enEnO`, free-standing vs shortCircuit-
wrapped) from that same session, since getting it wrong would show a pin on
a genuinely incorrect row, not just an uglier one.
"""

from __future__ import annotations

from dataclasses import dataclass

from typing import Callable

from twinforge.model import (
    GraphicalDiagram, GraphicalObject, GraphicalPin, LadderGridCell, LadderInstruction, LadderOperation,
    LadderParallel, LadderRung,
)

_CELL_W = 70
_CELL_H = 70
_MARGIN_LEFT = 60
_MARGIN_TOP = 30
_MARGIN_RIGHT = 30
_MARGIN_BOTTOM = 20
_LABEL_OFFSET = 14
_CONTACT_GAP = 8
# Confirmed real grid fact (docs/architecture/control-expert-exchange-
# capture.md's block-width checkpoint): an FFBBlock is always exactly 2
# grid columns wide, independent of type or pin count.
_BLOCK_WIDTH_COLUMNS = 2
_PIN_STUB = 6


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace('"', "&quot;")
    )


@dataclass(frozen=True)
class _Placement:
    instruction: LadderInstruction
    column: int


def _placements(rung: LadderRung) -> tuple[list[_Placement], bool]:
    """Return (placements, has_unsupported_branch)."""
    if rung.network is None:
        return [], False
    placements: list[_Placement] = []
    has_branch = False
    for index, element in enumerate(rung.network.elements):
        if isinstance(element, LadderParallel):
            has_branch = True
            continue
        column = element.position.column if element.position is not None else index
        placements.append(_Placement(element, column))
    return placements, has_branch


class LadderSvgExporter:
    """Render one or more `LadderRung`s (one `networkLD`'s worth) as SVG."""

    def export(self, rungs: list[LadderRung], *, title: str | None = None) -> str:
        rows = [rung.number for rung in rungs if rung.number is not None]
        max_column = 0
        rendered: list[tuple[LadderRung, list[_Placement], bool]] = []
        for rung in rungs:
            placements, has_branch = _placements(rung)
            rendered.append((rung, placements, has_branch))
            for placement in placements:
                max_column = max(max_column, placement.column)

        min_row = min(rows) if rows else 0
        max_row = max(rows) if rows else 0
        right_rail_x = _MARGIN_LEFT + (max_column + 1) * _CELL_W
        width = right_rail_x + _MARGIN_RIGHT
        height = _MARGIN_TOP + (max_row - min_row + 1) * _CELL_H + _MARGIN_BOTTOM

        parts: list[str] = []
        parts.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" font-family="monospace" font-size="12">'
        )
        if title:
            parts.append(f'<title>{_escape(title)}</title>')
        parts.append('<rect x="0" y="0" width="100%" height="100%" fill="white"/>')

        for rung, placements, has_branch in rendered:
            row = rung.number if rung.number is not None else min_row
            y = _MARGIN_TOP + (row - min_row) * _CELL_H + _CELL_H // 2
            parts.append(f'<text x="8" y="{y + 4}" fill="#666">{row}</text>')
            if has_branch:
                parts.append(
                    f'<text x="{_MARGIN_LEFT}" y="{y + 4}" fill="#a00">'
                    "[parallel branch not yet rendered]</text>"
                )
                continue
            self._render_rung_wire(parts, placements, y, right_rail_x)
            for placement in placements:
                self._render_element(parts, placement, y)

        parts.append("</svg>")
        return "\n".join(parts)

    def _render_rung_wire(
        self, parts: list[str], placements: list[_Placement], y: int, right_rail_x: int,
    ) -> None:
        # One continuous wire for the whole row; each symbol is drawn over it
        # below, with its own white background clearing a gap so it reads
        # clearly rather than needing per-segment line breaks computed here.
        parts.append(f'<line x1="{_MARGIN_LEFT}" y1="{y}" x2="{right_rail_x}" y2="{y}" stroke="black"/>')

    def _element_center(self, placement: _Placement) -> int:
        return _MARGIN_LEFT + placement.column * _CELL_W + _CELL_W // 2

    def _render_element(self, parts: list[str], placement: _Placement, y: int) -> None:
        instruction = placement.instruction
        cx = self._element_center(placement)
        label = instruction.operand or "?"
        op = instruction.operation
        if op in (LadderOperation.NORMALLY_OPEN_CONTACT, LadderOperation.NORMALLY_CLOSED_CONTACT):
            self._render_contact(parts, cx, y, label, closed=op == LadderOperation.NORMALLY_CLOSED_CONTACT)
        elif op in (LadderOperation.COIL, LadderOperation.SET_COIL, LadderOperation.RESET_COIL):
            mark = {LadderOperation.SET_COIL: "S", LadderOperation.RESET_COIL: "R"}.get(op, "")
            self._render_coil(parts, cx, y, label, mark)
        elif op == LadderOperation.BLOCK_OUTPUT_REFERENCE:
            self._render_block_output_reference(parts, cx, y, label)
        else:
            self._render_unsupported(parts, cx, y, label, instruction.source_mnemonic)

    def _render_contact(self, parts: list[str], cx: int, y: int, label: str, *, closed: bool) -> None:
        top, bottom = y - 14, y + 14
        left_bar, right_bar = cx - _CONTACT_GAP, cx + _CONTACT_GAP
        box_left, box_right = left_bar - 6, right_bar + 6
        parts.append(f'<rect x="{box_left}" y="{top - 6}" width="{box_right - box_left}" '
                      f'height="{bottom - top + 12}" fill="white"/>')
        # The background rect above erases the row's own wire line under the
        # whole symbol footprint (deliberately -- an open contact's own gap
        # must stay blank, not look like a solid connected wire). Without
        # these stubs, the wire visibly stops at the rect's edge instead of
        # reaching the contact's own bars, looking disconnected from the
        # device it represents.
        parts.append(f'<line x1="{box_left}" y1="{y}" x2="{left_bar}" y2="{y}" stroke="black" stroke-width="2"/>')
        parts.append(f'<line x1="{right_bar}" y1="{y}" x2="{box_right}" y2="{y}" stroke="black" stroke-width="2"/>')
        parts.append(f'<line x1="{left_bar}" y1="{top}" x2="{left_bar}" y2="{bottom}" stroke="black" stroke-width="2"/>')
        parts.append(f'<line x1="{right_bar}" y1="{top}" x2="{right_bar}" y2="{bottom}" stroke="black" stroke-width="2"/>')
        if closed:
            parts.append(f'<line x1="{left_bar - 3}" y1="{bottom + 3}" x2="{right_bar + 3}" y2="{top - 3}" '
                          'stroke="black" stroke-width="2"/>')
        parts.append(f'<text x="{cx}" y="{top - _LABEL_OFFSET}" text-anchor="middle">{_escape(label)}</text>')

    def _render_coil(self, parts: list[str], cx: int, y: int, label: str, mark: str) -> None:
        r = 14
        box_left, box_right = cx - r - 4, cx + r + 4
        parts.append(f'<rect x="{box_left}" y="{y - r - 4}" width="{box_right - box_left}" '
                      f'height="{2 * r + 8}" fill="white"/>')
        # Same reconnection as _render_contact: the rect erases the wire
        # under the whole circle footprint, so a stub is needed to bridge
        # the rect's own edge back to the circle's own edge.
        parts.append(f'<line x1="{box_left}" y1="{y}" x2="{cx - r}" y2="{y}" stroke="black" stroke-width="2"/>')
        parts.append(f'<line x1="{cx + r}" y1="{y}" x2="{box_right}" y2="{y}" stroke="black" stroke-width="2"/>')
        parts.append(f'<circle cx="{cx}" cy="{y}" r="{r}" fill="none" stroke="black" stroke-width="2"/>')
        if mark:
            parts.append(f'<text x="{cx}" y="{y + 4}" text-anchor="middle">{mark}</text>')
        parts.append(f'<text x="{cx}" y="{y - r - _LABEL_OFFSET}" text-anchor="middle">{_escape(label)}</text>')

    def _render_block_output_reference(self, parts: list[str], cx: int, y: int, label: str) -> None:
        w, h = 2 * _CONTACT_GAP + 20, 24
        parts.append(f'<rect x="{cx - w // 2}" y="{y - h // 2}" width="{w}" height="{h}" '
                      'fill="white" stroke="black" stroke-width="1" stroke-dasharray="4,2"/>')
        parts.append(f'<text x="{cx}" y="{y - h // 2 - _LABEL_OFFSET // 2}" text-anchor="middle" '
                      f'fill="#006">{_escape(label)}</text>')

    def _render_unsupported(self, parts: list[str], cx: int, y: int, label: str, mnemonic: str) -> None:
        w, h = 2 * _CONTACT_GAP + 20, 24
        parts.append(f'<rect x="{cx - w // 2}" y="{y - h // 2}" width="{w}" height="{h}" '
                      'fill="#fee" stroke="#a00" stroke-width="1"/>')
        parts.append(f'<text x="{cx}" y="{y + 4}" text-anchor="middle" fill="#a00">?</text>')
        parts.append(f'<text x="{cx}" y="{y - h // 2 - _LABEL_OFFSET // 2}" text-anchor="middle">'
                      f'{_escape(label)} ({_escape(mnemonic)})</text>')

    # --- Milestone 2: a full GraphicalDiagram, including blocks and ------
    # --- shortCircuit/VLink/bare-wire rows Milestone 1 leaves unpositioned.

    def export_diagram(self, diagram: GraphicalDiagram, *, title: str | None = None) -> str:
        """Render every `grid_rows` row of one LD `GraphicalDiagram` as SVG.

        Row Y position is a direct linear function of the row's own real
        number (`row - min_row`), never a compacted index -- a skipped
        `emptyLine` span genuinely has no `grid_rows` entry, but the row
        NUMBERS on either side of it already differ by the right amount, so
        no separate "visible row" lookup table is needed the way an earlier
        ad hoc verification script (never committed) required before it
        correctly stopped collapsing bare-`VLink` rows.
        """
        objects = diagram.objects
        rows = sorted(diagram.grid_rows, key=lambda r: r.row)
        min_row = min((r.row for r in rows), default=0)
        max_row = min_row
        max_column = 0
        # A shortCircuit's own vertical connector needs to land at whatever
        # column the TARGET row's own wire genuinely presents at -- three
        # real shapes confirmed so far, each needing a different answer:
        # (1) a row with real wire content and no `VLink` of its own (the
        # fixture's ARRET_MOT/row 5) presents at its rightmost extent, one
        # column past its last cell. (2) a row that is itself just a lone
        # bare `VLink` pass-through (row 13, an intermediate hop of a
        # taller bus with no wire of its own) presents wherever the chain
        # of such rows eventually reaches real wire content (row 14) -- its
        # own raw grid column only positions its own glyph, not a wire's
        # end. (3) a row where a `VLink` sits alongside a real element it
        # feeds directly on the SAME row (the fixture's ARRET_MOT reset bus,
        # rows 90-96: each row's `VLink` is immediately followed by that
        # row's own resetCoil, one column over) presents at the `VLink`'s
        # own column plus its width -- i.e. touching the very next cell,
        # not the row's far-right extent past a trailing `HLink` (a real
        # regression the user caught: the connector was landing at the
        # right rail instead of at each coil's own column).
        rows_by_number = {grid_row.row: grid_row for grid_row in rows}

        def _resolve_row_end_column(start_row: int) -> int:
            current = start_row
            visited: set[int] = set()
            while True:
                grid_row = rows_by_number.get(current)
                if grid_row is None:
                    return 0
                cells = grid_row.cells
                if len(cells) == 1 and cells[0].kind == "vlink" and current not in visited:
                    visited.add(current)
                    current += 1
                    continue
                vlink_cell = next((c for c in cells if c.kind == "vlink"), None)
                if vlink_cell is not None:
                    return vlink_cell.column + vlink_cell.width
                return max((c.column + c.width for c in cells), default=0)

        row_end_columns: dict[int, int] = {grid_row.row: _resolve_row_end_column(grid_row.row) for grid_row in rows}
        for grid_row in rows:
            for cell in grid_row.cells:
                max_column = max(max_column, cell.column + cell.width)
                if cell.kind == "block" and cell.object_index is not None:
                    span, *_ = self._block_span(objects[cell.object_index], shortcircuit_wrapped=False)
                    max_row = max(max_row, grid_row.row + span - 1)
                elif cell.kind == "short_circuit" and cell.wraps == "block" and cell.wrapped_object_index is not None:
                    span, *_ = self._block_span(objects[cell.wrapped_object_index], shortcircuit_wrapped=True)
                    max_row = max(max_row, grid_row.row + span - 1)
                else:
                    max_row = max(max_row, grid_row.row)

        width = _MARGIN_LEFT + max_column * _CELL_W + _MARGIN_RIGHT
        height = _MARGIN_TOP + (max_row - min_row + 1) * _CELL_H + _MARGIN_BOTTOM
        parts: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" font-family="monospace" font-size="12">'
        ]
        if title:
            parts.append(f'<title>{_escape(title)}</title>')
        parts.append('<rect x="0" y="0" width="100%" height="100%" fill="white"/>')

        def row_y(row: int) -> int:
            return _MARGIN_TOP + (row - min_row) * _CELL_H

        for grid_row in rows:
            y_top = row_y(grid_row.row)
            parts.append(f'<text x="8" y="{y_top + _CELL_H // 2 + 4}" fill="#666">{grid_row.row}</text>')
            row_dots: list[str] = []
            for cell in grid_row.cells:
                x = _MARGIN_LEFT + cell.column * _CELL_W
                if cell.kind == "contact" and cell.object_index is not None:
                    obj = objects[cell.object_index]
                    yc = y_top + _CELL_H // 2
                    # A contact/coil symbol only draws its own narrow glyph
                    # (see _render_contact/_render_coil, shared with
                    # Milestone 1's export(), which draws one whole-row
                    # background wire itself and relies on it for this) --
                    # export_diagram has no such whole-row wire, so without
                    # this, adjacent series contacts render with no visible
                    # connection between them at all. Real bug, caught on
                    # the user's own first look at real output.
                    parts.append(f'<line x1="{x}" y1="{yc}" x2="{x + _CELL_W}" y2="{yc}" stroke="black"/>')
                    self._render_contact(parts, x + _CELL_W // 2, yc, obj.operand or "?",
                                          closed=obj.type_name == "closedContact")
                elif cell.kind == "coil" and cell.object_index is not None:
                    obj = objects[cell.object_index]
                    yc = y_top + _CELL_H // 2
                    parts.append(f'<line x1="{x}" y1="{yc}" x2="{x + _CELL_W}" y2="{yc}" stroke="black"/>')
                    mark = {"resetCoil": "R", "setCoil": "S", "PCoil": "P"}.get(obj.type_name or "", "")
                    self._render_coil(parts, x + _CELL_W // 2, yc, obj.operand or "?", mark)
                elif cell.kind == "hlink":
                    yc = y_top + _CELL_H // 2
                    parts.append(f'<line x1="{x}" y1="{yc}" x2="{x + cell.width * _CELL_W}" y2="{yc}" '
                                  'stroke="black"/>')
                elif cell.kind == "vlink":
                    # A lone VLink (nothing else on its row) is an
                    # intermediate hop of a taller bus, not a wire of its
                    # own -- draw it at the resolved chain-end column (see
                    # row_end_columns above), not its own raw grid column,
                    # so it lines up with the shortCircuit above it and the
                    # real wire it ultimately reaches below. A VLink mixed
                    # with a real element on its own row (the ARRET_MOT
                    # reset bus and the mode_auto/capteur_livraison reset
                    # bus: each row's VLink feeds that row's own resetCoil
                    # directly) is a genuine tap, not a pass-through --
                    # row_end_columns already resolves that shape to the
                    # VLink's own column plus its width (touching the coil
                    # it feeds). Every VLink, lone or mixed, always
                    # continues one row down: a real, evidenced shape has
                    # the LAST coil in such a chain (M4_S1 in the
                    # mode_auto/capteur_livraison bus, M4_S2 in the
                    # ARRET_MOT bus) fed by the PREVIOUS row's own VLink
                    # with no VLink declared in its own row at all -- an
                    # earlier attempt to stop the line whenever the next
                    # row had no VLink of its own broke exactly this shape,
                    # caught directly by the user ("the vlink is missing
                    # from line 96 to line 97 ... same case ... line 80 to
                    # line 81").
                    is_lone = len(grid_row.cells) == 1
                    vlink_x = _MARGIN_LEFT + row_end_columns[grid_row.row] * _CELL_W
                    self._render_vlink(parts, vlink_x, y_top, dot=not is_lone, dots=row_dots)
                elif cell.kind == "block" and cell.object_index is not None:
                    self._render_block(parts, objects[cell.object_index], x, grid_row.row, row_y,
                                       shortcircuit_wrapped=False)
                elif cell.kind == "short_circuit":
                    self._render_short_circuit(parts, cell, objects, x, grid_row.row, y_top, row_y,
                                               row_end_columns, row_dots)
            parts.extend(row_dots)

        parts.append("</svg>")
        return "\n".join(parts)

    def _block_span(
        self, obj: GraphicalObject, *, shortcircuit_wrapped: bool,
    ) -> tuple[int, list[GraphicalPin], list[GraphicalPin], int]:
        """(span, shown_inputs, shown_outputs, row_offset).

        `enEnO=False` hides EN/ENO's OWN label entirely (not merely
        unwired). Every `enEnO=False` block renders at the SAME offset (2)
        and therefore the SAME height for the same pin count, regardless
        of whether it is shortCircuit-wrapped or free-standing -- explicit
        product decision, not a vendor-accuracy claim: this exporter's own
        roadmap already disclaims pixel-perfect replication of Control
        Expert's own rendering, and a same-session attempt to match two
        reference renderings that showed `SR_2` (wrapped) one row shorter
        than `SR_8`/`SR_9` (free-standing) for the identical block type was
        rejected directly by the user ("All SR blocks should be the same
        heights as per SR_8"). `shortcircuit_wrapped` is kept as a
        parameter (every call site still passes it) in case a future,
        different block shape genuinely needs to distinguish the two, but
        it no longer changes this offset.
        """
        inputs = [p for p in obj.pins if p.direction == "input"]
        outputs = [p for p in obj.pins if p.direction == "output"]
        if obj.en_en_o is False:
            shown_inputs, shown_outputs = inputs[1:], outputs[1:]
            offset = 2
        else:
            shown_inputs, shown_outputs = inputs, outputs
            offset = 1
        if not shown_inputs and not shown_outputs:
            span = 1
        else:
            span = max(offset + len(shown_inputs), offset + len(shown_outputs))
        return span, shown_inputs, shown_outputs, offset

    def _render_block(
        self, parts: list[str], obj: GraphicalObject, x: int, anchor_row: int, row_y: Callable[[int], int],
        *, shortcircuit_wrapped: bool,
    ) -> None:
        span, shown_inputs, shown_outputs, offset = self._block_span(obj, shortcircuit_wrapped=shortcircuit_wrapped)
        box_w = _BLOCK_WIDTH_COLUMNS * _CELL_W
        y_top = row_y(anchor_row)
        y_bottom = row_y(anchor_row + span - 1) + _CELL_H
        parts.append(f'<rect x="{x + 2}" y="{y_top + 2}" width="{box_w - 4}" height="{y_bottom - y_top - 4}" '
                      'fill="white" stroke="black" stroke-width="2"/>')
        title = f"{obj.instance_name or '?'} ({obj.type_name or '?'})"
        parts.append(f'<text x="{x + box_w // 2}" y="{y_top + 16}" text-anchor="middle">{_escape(title)}</text>')
        for i, pin in enumerate(shown_inputs):
            yc = row_y(anchor_row + offset + i) + _CELL_H // 2
            parts.append(f'<line x1="{x - _PIN_STUB}" y1="{yc}" x2="{x}" y2="{yc}" stroke="black" stroke-width="2"/>')
            parts.append(f'<text x="{x + 4}" y="{yc + 4}">{_escape(pin.name or "?")}</text>')
            if pin.expression:
                parts.append(f'<text x="{x - _PIN_STUB - 4}" y="{yc + 4}" text-anchor="end" fill="#555">'
                              f'{_escape(pin.expression)}</text>')
        for i, pin in enumerate(shown_outputs):
            yc = row_y(anchor_row + offset + i) + _CELL_H // 2
            parts.append(f'<line x1="{x + box_w}" y1="{yc}" x2="{x + box_w + _PIN_STUB}" y2="{yc}" '
                          'stroke="black" stroke-width="2"/>')
            parts.append(f'<text x="{x + box_w - 4}" y="{yc + 4}" text-anchor="end">{_escape(pin.name or "?")}</text>')
            if pin.expression:
                parts.append(f'<text x="{x + box_w + _PIN_STUB + 4}" y="{yc + 4}" fill="#555">'
                              f'{_escape(pin.expression)}</text>')
        if obj.en_en_o is False:
            parts.append(f'<text x="{x + box_w // 2}" y="{y_bottom - 8}" text-anchor="middle" fill="#a00">'
                          'no EN/ENO</text>')

    def _render_vlink(
        self, parts: list[str], x: int, y_top: int, *, dot: bool = False, dots: list[str] | None = None,
    ) -> None:
        """Bridge THIS row's own center to the NEXT row's center -- not this

        row's own top-to-bottom, which undershoots by half a row. Real bug,
        caught against this exact real fixture (SR_8's own R input, fed by
        selec_auto ORed with ARRET_MOT one row below): a connector spanning
        only its own row's height visually stops at the row boundary,
        never reaching the row below's own wire at its own vertical
        center, where every contact/coil/hlink in this exporter is drawn.
        This is the same fix an earlier, independent ad hoc PIL verification
        script (never committed) already needed and made, for the identical
        reason -- reintroduced here because this SVG exporter was written
        from scratch rather than by reusing that script's own logic.

        `dots`, when given, collects the junction dot's own markup instead
        of appending it to `parts` immediately: a dot drawn inline can end
        up UNDER a same-row element rendered right after it in document
        order (a coil's own lead-in line, drawn flush across its whole
        cell, passes directly through a tap sitting at that coil's own
        left edge) -- real bug, caught on the user's own screenshot of the
        real fixture's ARRET_MOT reset bus, where a terminal tap's dot
        (with no reinforcing vertical line to keep it visible) all but
        disappeared under the coil's own black line. Deferring every dot to
        the end of its own row's rendering keeps them on top of everything
        else in that row.
        """
        top = y_top + _CELL_H // 2
        bottom = y_top + _CELL_H + _CELL_H // 2
        parts.append(f'<line x1="{x}" y1="{top}" x2="{x}" y2="{bottom}" stroke="blue" stroke-width="2"/>')
        if dot:
            circle = f'<circle cx="{x}" cy="{top}" r="3" fill="blue"/>'
            (dots if dots is not None else parts).append(circle)

    def _render_short_circuit(
        self, parts: list[str], cell: LadderGridCell, objects: list[GraphicalObject], x: int, row: int,
        y_top: int, row_y: Callable[[int], int], row_end_columns: dict[int, int], dots: list[str],
    ) -> None:
        yc = y_top + _CELL_H // 2
        if cell.wraps == "contact" and cell.wrapped_object_index is not None:
            # Real evidence: the connector's own column is wherever the
            # TARGET row (row + 1, the row this wire continues down into)
            # genuinely ends -- not a fixed offset from this row's own
            # wrapped width, which only coincidentally matches when the
            # gap happens to equal the wrapped width (already found and
            # fixed once: a 2-cell-wide wrapped HLink whose real target
            # row actually ended 3 columns over, not 2). Falls back to the
            # wrapped width only when the next row's own extent isn't
            # known (e.g. it's the diagram's last row).
            target_col = row_end_columns.get(row + 1)
            connector_x = _MARGIN_LEFT + target_col * _CELL_W if target_col is not None else x + _CELL_W
            self._render_vlink(parts, connector_x, y_top, dot=True, dots=dots)
            obj = objects[cell.wrapped_object_index]
            parts.append(f'<line x1="{x}" y1="{yc}" x2="{x + _CELL_W}" y2="{yc}" stroke="black"/>')
            self._render_contact(parts, x + _CELL_W // 2, yc, obj.operand or "?",
                                  closed=obj.type_name == "closedContact")
        elif cell.wraps == "hlink":
            target_col = row_end_columns.get(row + 1)
            width = (cell.wrapped_width or 1) * _CELL_W
            connector_x = _MARGIN_LEFT + target_col * _CELL_W if target_col is not None else x + width
            self._render_vlink(parts, connector_x, y_top, dot=True, dots=dots)
            parts.append(f'<line x1="{x}" y1="{yc}" x2="{x + width}" y2="{yc}" stroke="black"/>')
        elif cell.wraps == "block" and cell.wrapped_object_index is not None:
            # Different shape, real evidence (SR_2.Q1 -> TON_23.IN): this is
            # the block's own OUTPUT continuing onward via a sibling HLink
            # on THIS same row, not a wire landing on some row below -- the
            # connector belongs flush with the block's own right edge, no
            # row_end_columns lookup, and no dot (a plain elbow, not a
            # junction where multiple wires actually meet).
            self._render_vlink(parts, x, y_top, dot=False)
            obj = objects[cell.wrapped_object_index]
            self._render_block(parts, obj, x, row, row_y, shortcircuit_wrapped=True)
            # The continuing HLink sits on the block's own ANCHOR row (it
            # is declared as a sibling of the shortCircuit in the same
            # source row), but the block's own first shown output pin is
            # rendered `offset` rows below that anchor -- confirmed by the
            # original PIL verification session's own reference render
            # (sr2_ton23_zoom.png): an explicit dogleg bridges the two, not
            # a straight horizontal line. Drawn only when they are
            # genuinely on different rows (offset != 0) and the block
            # actually has a shown output to dogleg from. The corner sits
            # at the MIDDLE of the gap between the block's own right edge
            # and whatever it continues into (SR_2 -> TON_23: a single
            # HLink nbCells="1", one cell wide) -- user-confirmed against
            # the real fixture, not flush against the block's own edge.
            _, _, shown_outputs, offset = self._block_span(obj, shortcircuit_wrapped=True)
            if shown_outputs and offset != 0:
                box_w = _BLOCK_WIDTH_COLUMNS * _CELL_W
                corner_x = x + box_w + _CELL_W // 2
                anchor_yc = y_top + _CELL_H // 2
                output_yc = row_y(row + offset) + _CELL_H // 2
                # The pin's own short stub only reaches box_w + _PIN_STUB;
                # extend it to the corner before turning, so the dogleg is
                # one continuous path (horizontal, vertical, horizontal),
                # not a vertical line floating past the stub's own end.
                parts.append(f'<line x1="{x + box_w + _PIN_STUB}" y1="{output_yc}" x2="{corner_x}" '
                              f'y2="{output_yc}" stroke="black" stroke-width="2"/>')
                parts.append(f'<line x1="{corner_x}" y1="{anchor_yc}" x2="{corner_x}" y2="{output_yc}" '
                              'stroke="black" stroke-width="2"/>')
        else:
            self._render_unsupported(parts, x + _CELL_W // 2, yc, "shortCircuit", "unresolved")
