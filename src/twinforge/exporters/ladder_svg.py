"""Render vendor-neutral ladder rungs as deterministic SVG markup.

Renders `model/ladder.py`'s `LadderRung`/`LadderSeries`/`LadderInstruction`
directly -- never a source format's raw captured XML -- so this works for
any producer of that model (Control Expert today; CCW/L5X wherever their
own ladder conversion already populates the same types). Text-in/text-out,
like `aoi_plantuml.py`: no image-library dependency, output is plain SVG a
browser renders natively and source control can diff.

Scoped to Milestone 1 of the visualization roadmap
(docs/roadmaps/graphical-diagram-visualization-roadmap.md): a flat
`LadderSeries` of `LadderInstruction` (Control Expert's own parser never
produces anything else today). A `LadderParallel` branch is rendered as an
explicit "not yet supported" placeholder, not guessed at -- silently
skipping it would misrepresent a real branch as absent.
"""

from __future__ import annotations

from dataclasses import dataclass

from twinforge.model import LadderInstruction, LadderOperation, LadderParallel, LadderRung

_CELL_W = 70
_CELL_H = 70
_MARGIN_LEFT = 60
_MARGIN_TOP = 30
_MARGIN_RIGHT = 30
_MARGIN_BOTTOM = 20
_LABEL_OFFSET = 14
_CONTACT_GAP = 8


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
        parts.append(f'<rect x="{left_bar - 6}" y="{top - 6}" width="{2 * _CONTACT_GAP + 12}" '
                      f'height="{bottom - top + 12}" fill="white"/>')
        parts.append(f'<line x1="{left_bar}" y1="{top}" x2="{left_bar}" y2="{bottom}" stroke="black" stroke-width="2"/>')
        parts.append(f'<line x1="{right_bar}" y1="{top}" x2="{right_bar}" y2="{bottom}" stroke="black" stroke-width="2"/>')
        if closed:
            parts.append(f'<line x1="{left_bar - 3}" y1="{bottom + 3}" x2="{right_bar + 3}" y2="{top - 3}" '
                          'stroke="black" stroke-width="2"/>')
        parts.append(f'<text x="{cx}" y="{top - _LABEL_OFFSET}" text-anchor="middle">{_escape(label)}</text>')

    def _render_coil(self, parts: list[str], cx: int, y: int, label: str, mark: str) -> None:
        r = 14
        parts.append(f'<rect x="{cx - r - 4}" y="{y - r - 4}" width="{2 * r + 8}" height="{2 * r + 8}" fill="white"/>')
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
