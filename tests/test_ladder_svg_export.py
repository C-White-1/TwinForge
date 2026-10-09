import re
from pathlib import Path

import pytest

from twinforge.exporters import LadderSvgExporter
from twinforge.model import (
    GraphicalDiagram,
    GraphicalObject,
    GraphicalPin,
    LadderGridCell,
    LadderGridRow,
    LadderInstruction,
    LadderOperation,
    LadderParallel,
    LadderPosition,
    LadderRung,
    LadderSeries,
)
from twinforge.parsers.control_expert import capture_file, parse_projects


def _instruction(
    operation: LadderOperation,
    operand: str,
    column: int,
    *,
    mnemonic: str = "CONTACT_P",
) -> LadderInstruction:
    return LadderInstruction(
        operation=operation,
        source_mnemonic=mnemonic,
        operand=operand,
        position=LadderPosition(column=column, row=0),
    )


def _series_rung(number: int, elements: tuple) -> LadderRung:
    return LadderRung(number=number, network=LadderSeries(elements=elements))


def test_renders_series_contacts_and_coil():
    rung = _series_rung(
        0,
        (
            _instruction(LadderOperation.NORMALLY_OPEN_CONTACT, "A", 0),
            _instruction(LadderOperation.NORMALLY_CLOSED_CONTACT, "B", 2),
            _instruction(LadderOperation.COIL, "Out", 11, mnemonic="COIL_P"),
        ),
    )

    svg = LadderSvgExporter().export([rung])

    assert svg.startswith("<svg ")
    assert svg.endswith("</svg>")
    assert ">A<" in svg
    assert ">B<" in svg
    assert ">Out<" in svg
    # Normally-closed contact gets a diagonal slash the open contact lacks.
    assert svg.count('stroke-dasharray') == 0
    assert svg.count("<circle") == 1


def test_renders_set_and_reset_coil_markers():
    rung = _series_rung(
        0,
        (
            _instruction(LadderOperation.SET_COIL, "S1", 0, mnemonic="COIL_S"),
        ),
    )
    other = _series_rung(
        1,
        (
            _instruction(LadderOperation.RESET_COIL, "R1", 0, mnemonic="COIL_R"),
        ),
    )

    svg = LadderSvgExporter().export([rung, other])

    assert '>S<' in svg
    assert '>R<' in svg


def test_renders_block_output_reference_as_dashed_labeled_box():
    rung = _series_rung(
        0,
        (
            _instruction(
                LadderOperation.BLOCK_OUTPUT_REFERENCE,
                "Heating_control.A",
                5,
                mnemonic="SR",
            ),
            _instruction(LadderOperation.COIL, "Out", 11, mnemonic="COIL_P"),
        ),
    )

    svg = LadderSvgExporter().export([rung])

    assert "stroke-dasharray" in svg
    assert "Heating_control.A" in svg


def test_renders_unsupported_operation_with_mnemonic():
    rung = _series_rung(
        0,
        (
            _instruction(
                LadderOperation.UNSUPPORTED,
                "Edge",
                3,
                mnemonic="PContact",
            ),
            _instruction(LadderOperation.COIL, "Out", 11, mnemonic="COIL_P"),
        ),
    )

    svg = LadderSvgExporter().export([rung])

    assert "Edge (PContact)" in svg
    assert 'fill="#a00"' in svg


def test_renders_parallel_branch_as_explicit_placeholder_not_silently_dropped():
    rung = _series_rung(
        0,
        (
            LadderParallel(
                branches=(
                    LadderSeries(elements=(_instruction(LadderOperation.NORMALLY_OPEN_CONTACT, "A", 0),)),
                    LadderSeries(elements=(_instruction(LadderOperation.NORMALLY_OPEN_CONTACT, "B", 0),)),
                )
            ),
        ),
    )

    svg = LadderSvgExporter().export([rung])

    assert "not yet rendered" in svg
    # Neither branch's own contacts are guessed at and drawn.
    assert ">A<" not in svg
    assert ">B<" not in svg


def test_rung_with_no_network_renders_empty_row():
    rung = LadderRung(number=0, network=None)

    svg = LadderSvgExporter().export([rung])

    assert svg.startswith("<svg ")
    assert ">0<" in svg


def test_export_is_deterministic():
    rung = _series_rung(
        0,
        (
            _instruction(LadderOperation.NORMALLY_OPEN_CONTACT, "A", 0),
            _instruction(LadderOperation.COIL, "Out", 11, mnemonic="COIL_P"),
        ),
    )

    first = LadderSvgExporter().export([rung], title="determinism check")
    second = LadderSvgExporter().export([rung], title="determinism check")

    assert first == second


def test_multi_rung_layout_sizes_by_max_row_and_column():
    narrow = _series_rung(
        0,
        (_instruction(LadderOperation.NORMALLY_OPEN_CONTACT, "A", 0),),
    )
    wide = _series_rung(
        3,
        (_instruction(LadderOperation.COIL, "Out", 11, mnemonic="COIL_P"),),
    )

    svg = LadderSvgExporter().export([narrow, wide])

    assert ">0<" in svg
    assert ">3<" in svg
    # Four rows (0..3) tall, twelve columns (0..11) wide.
    width_attr = svg.split('width="', 1)[1].split('"', 1)[0]
    height_attr = svg.split('height="', 1)[1].split('"', 1)[0]
    assert int(width_attr) > int(height_attr)


# --- Milestone 2: export_diagram (GraphicalDiagram, including blocks and ---
# --- shortCircuit/VLink/bare-wire rows the pure-series exporter can't). ---

def _pin(name: str, direction: str, expression: str | None = None) -> GraphicalPin:
    return GraphicalPin(name=name, direction=direction, expression=expression)


def _block(instance: str, type_name: str, pins: list[GraphicalPin], *, en_en_o: bool | None) -> GraphicalObject:
    return GraphicalObject(kind="block", instance_name=instance, type_name=type_name, pins=pins, en_en_o=en_en_o)


def _contact(operand: str, *, closed: bool = False) -> GraphicalObject:
    return GraphicalObject(kind="contact", operand=operand,
                            type_name="closedContact" if closed else "openContact")


def _coil(operand: str, *, kind: str | None = None) -> GraphicalObject:
    return GraphicalObject(kind="coil", operand=operand, type_name=kind)


def test_export_diagram_renders_contact_and_coil_rows():
    diagram = GraphicalDiagram(
        language="LD",
        objects=[_contact("A"), _coil("Out")],
        grid_rows=[LadderGridRow(row=0, cells=[
            LadderGridCell(column=0, kind="contact", object_index=0),
            LadderGridCell(column=3, kind="coil", object_index=1),
        ])],
    )
    svg = LadderSvgExporter().export_diagram(diagram)
    assert svg.startswith("<svg ") and svg.endswith("</svg>")
    assert ">A<" in svg
    assert ">Out<" in svg


def test_export_diagram_marks_pcoil_with_p():
    # Real evidence: sayahali_conveyor_ali_conv.zef's SR_8 network has
    # <coil typeCoil="PCoil" coilVariableName="%M12"/> -- Schneider's own
    # IEC 61131-3 "P" (pulse/rising-edge) coil, distinct from a plain coil
    # and from resetCoil/setCoil, which already get their own mark.
    diagram = GraphicalDiagram(
        language="LD",
        objects=[_coil("%M12", kind="PCoil")],
        grid_rows=[LadderGridRow(row=0, cells=[LadderGridCell(column=0, kind="coil", object_index=0)])],
    )
    svg = LadderSvgExporter().export_diagram(diagram)
    assert '>P</text>' in svg


def test_export_diagram_contact_and_coil_wires_reach_the_symbol_edge():
    # The background rect behind a contact/coil symbol erases the row's own
    # wire line under its whole footprint (deliberately, so an open
    # contact's gap stays blank) -- but without a stub reconnecting the
    # rect's own edge to the symbol's own edge, the wire visibly stops short
    # of the device instead of meeting it.
    diagram = GraphicalDiagram(
        language="LD",
        objects=[_contact("A"), _coil("Out")],
        grid_rows=[LadderGridRow(row=0, cells=[
            LadderGridCell(column=0, kind="contact", object_index=0),
            LadderGridCell(column=1, kind="coil", object_index=1),
        ])],
    )
    svg = LadderSvgExporter().export_diagram(diagram)
    yc = 30 + 35
    contact_cx = 60 + 35
    coil_cx = 60 + 70 + 35
    # Contact: stub from the rect's own left/right edge to its own bars
    # (cx +/- _CONTACT_GAP == 8).
    assert f'<line x1="{contact_cx - 8 - 6}" y1="{yc}" x2="{contact_cx - 8}" y2="{yc}"' in svg
    assert f'<line x1="{contact_cx + 8}" y1="{yc}" x2="{contact_cx + 8 + 6}" y2="{yc}"' in svg
    # Coil: stub from the rect's own left/right edge to the circle's own
    # edge (cx +/- r == 14).
    assert f'<line x1="{coil_cx - 14 - 4}" y1="{yc}" x2="{coil_cx - 14}" y2="{yc}"' in svg
    assert f'<line x1="{coil_cx + 14}" y1="{yc}" x2="{coil_cx + 14 + 4}" y2="{yc}"' in svg


def test_export_diagram_positions_ton_like_block_pins_at_posy_plus_1_plus_i():
    # Real evidence: TON_23's IN (declared index 1) lands one row below its
    # own EN, ET one row below that -- the confirmed enEnO="true" offset
    # (block's own top row is a blank header; EN/ENO share row+1, IN/Q
    # row+2, PT/ET row+3), independent of shortCircuit wrapping.
    block = _block("B1", "TON", [
        _pin("EN", "input"), _pin("IN", "input"), _pin("PT", "input", "t#3s"),
        _pin("ENO", "output"), _pin("Q", "output"), _pin("ET", "output"),
    ], en_en_o=True)
    diagram = GraphicalDiagram(
        language="LD", objects=[block],
        grid_rows=[LadderGridRow(row=5, cells=[LadderGridCell(column=2, kind="block", width=2, object_index=0)])],
    )
    svg = LadderSvgExporter().export_diagram(diagram)
    # Row 5 is the header (blank); EN/ENO at row 6, IN/Q at row 7, PT/ET at
    # row 8. Only row 5 appears in grid_rows, so min_row == 5; Y is
    # _MARGIN_TOP + (row - min_row) * _CELL_H, matching the exporter itself.
    def y_for(row: int) -> int:
        return 30 + (row - 5) * 70

    assert f'y="{y_for(6) + 35 + 4}">EN</text>' in svg
    assert f'y="{y_for(7) + 35 + 4}">IN</text>' in svg
    assert f'y="{y_for(8) + 35 + 4}">PT</text>' in svg
    assert "t#3s" in svg


def test_export_diagram_hides_en_eno_for_en_en_o_false_block():
    block = _block("SR_1", "SR", [
        _pin("EN", "input"), _pin("S1", "input"), _pin("R", "input"),
        _pin("ENO", "output"), _pin("Q1", "output"),
    ], en_en_o=False)
    diagram = GraphicalDiagram(
        language="LD", objects=[block],
        grid_rows=[LadderGridRow(row=0, cells=[LadderGridCell(column=0, kind="block", width=2, object_index=0)])],
    )
    svg = LadderSvgExporter().export_diagram(diagram)
    assert ">S1<" in svg
    assert ">R<" in svg
    assert ">Q1<" in svg
    assert ">EN<" not in svg
    assert ">ENO<" not in svg
    assert "no EN/ENO" in svg


def test_export_diagram_en_en_o_false_block_offset_is_identical_free_standing_or_wrapped():
    # Explicit product decision, not a vendor-accuracy claim: every
    # enEnO=False block renders at the SAME offset (2), so SR_8 (free-
    # standing) and SR_2 (shortCircuit-wrapped) -- the same block type,
    # identical pin counts -- render at the SAME size. Two reference
    # renderings from the original ad hoc PIL verification session
    # (rows_0_19.png/nocollapse_rows_17_39.png) actually showed SR_2 one
    # row shorter than SR_8/SR_9 for this exact pin count; the user
    # directly rejected matching that ("All SR blocks should be the same
    # heights as per SR_8"), overriding vendor-rendering fidelity in favor
    # of consistent block sizing -- this exporter's own roadmap already
    # disclaims pixel-perfect replication as a goal.
    pins = [
        _pin("EN", "input"), _pin("S1", "input"), _pin("R", "input"),
        _pin("ENO", "output"), _pin("Q1", "output"),
    ]
    free_standing = _block("SR_8", "SR", pins, en_en_o=False)
    wrapped = _block("SR_2", "SR", pins, en_en_o=False)
    diagram = GraphicalDiagram(
        language="LD",
        objects=[free_standing, wrapped],
        grid_rows=[
            LadderGridRow(row=0, cells=[LadderGridCell(column=0, kind="block", width=2, object_index=0)]),
            LadderGridRow(row=5, cells=[
                LadderGridCell(column=0, kind="short_circuit", width=2, wraps="block",
                               wrapped_width=2, wrapped_object_index=1),
            ]),
        ],
    )
    svg = LadderSvgExporter().export_diagram(diagram)
    heights = re.findall(r'<rect x="\d+" y="\d+" width="136" height="(\d+)" fill="white" stroke="black"', svg)
    assert len(heights) == 2
    assert heights[0] == heights[1]


def test_export_diagram_short_circuit_wraps_contact_hlink_and_block():
    contact_block = _block("B1", "TON", [_pin("EN", "input")], en_en_o=True)
    diagram = GraphicalDiagram(
        language="LD",
        objects=[_contact("Gate"), contact_block],
        grid_rows=[
            LadderGridRow(row=0, cells=[
                LadderGridCell(column=0, kind="short_circuit", wraps="contact",
                                wrapped_width=1, wrapped_object_index=0),
            ]),
            LadderGridRow(row=1, cells=[
                LadderGridCell(column=0, kind="short_circuit", wraps="hlink", width=3, wrapped_width=3),
            ]),
            LadderGridRow(row=2, cells=[
                LadderGridCell(column=0, kind="short_circuit", width=2, wraps="block",
                                wrapped_width=2, wrapped_object_index=1),
            ]),
        ],
    )
    svg = LadderSvgExporter().export_diagram(diagram)
    assert ">Gate<" in svg
    assert "B1 (TON)" in svg
    # Three vertical connectors, one per shortCircuit row.
    assert svg.count('stroke="blue" stroke-width="2"') == 3


def test_export_diagram_short_circuit_wraps_block_draws_output_dogleg():
    # Real evidence (SR_2.Q1 -> TON_23.IN, confirmed against the original
    # PIL verification session's own reference render, sr2_ton23_zoom.png):
    # the continuing HLink after a shortCircuit-wraps-block shape sits on
    # the block's own ANCHOR row (it is a sibling of the shortCircuit in
    # the same source row), but the block's first shown output pin renders
    # `offset` rows below that anchor -- an explicit dogleg (horizontal,
    # vertical, horizontal) bridges them, not a straight line, since they
    # are genuinely on different rows. The corner sits at the MIDDLE of
    # the gap between the block's own right edge and what it continues
    # into, not flush against the block's own edge -- user-confirmed
    # against the real fixture.
    block = _block("SR_2", "SR", [
        _pin("EN", "input"), _pin("S1", "input"), _pin("R", "input"),
        _pin("ENO", "output"), _pin("Q1", "output"),
    ], en_en_o=False)
    diagram = GraphicalDiagram(
        language="LD", objects=[block],
        grid_rows=[LadderGridRow(row=0, cells=[
            LadderGridCell(column=0, kind="short_circuit", width=2, wraps="block",
                           wrapped_width=2, wrapped_object_index=0),
        ])],
    )
    svg = LadderSvgExporter().export_diagram(diagram)
    box_right = 60 + 2 * 70  # block's right edge (column 2)
    corner_x = box_right + 35  # the middle of the one-cell gap past the block
    anchor_yc = 30 + 35  # row 0's own center
    output_yc = 30 + 2 * 70 + 35  # row 2's center (offset 2, every enEnO=false block)
    assert f'<line x1="{box_right + 6}" y1="{output_yc}" x2="{corner_x}" y2="{output_yc}" stroke="black" stroke-width="2"/>' in svg
    assert f'<line x1="{corner_x}" y1="{anchor_yc}" x2="{corner_x}" y2="{output_yc}" stroke="black" stroke-width="2"/>' in svg


def test_export_diagram_short_circuit_wraps_block_inputs_align_with_same_row_conditions():
    # User-confirmed real evidence (SR_2, this fixture): with every
    # enEnO=False block now sharing the same offset (2), S1 and R land on
    # the SAME rows as capteur_2 and capteur_3 respectively (rows 23 and
    # 24 of the real fixture) -- ordinary same-row wiring connects them,
    # exactly like any other plain contact-to-pin connection, with no
    # separate vertical tap needed.
    block = _block("SR_2", "SR", [
        _pin("EN", "input"), _pin("S1", "input"), _pin("R", "input"),
        _pin("ENO", "output"), _pin("Q1", "output"),
    ], en_en_o=False)
    diagram = GraphicalDiagram(
        language="LD",
        objects=[block, _contact("capteur_2"), _contact("capteur_3")],
        grid_rows=[
            LadderGridRow(row=0, cells=[
                LadderGridCell(column=2, kind="short_circuit", width=2, wraps="block",
                               wrapped_width=2, wrapped_object_index=0),
            ]),
            LadderGridRow(row=2, cells=[
                LadderGridCell(column=0, kind="hlink", width=1),
                LadderGridCell(column=1, kind="contact", object_index=1),
            ]),
            LadderGridRow(row=3, cells=[
                LadderGridCell(column=0, kind="hlink", width=1),
                LadderGridCell(column=1, kind="contact", object_index=2),
            ]),
        ],
    )
    svg = LadderSvgExporter().export_diagram(diagram)
    pin_x = 60 + 2 * 70  # S1/R's own column (2), matching capteur_2/capteur_3's own row end
    s1_yc = 30 + 2 * 70 + 35  # row 2's center (offset 2, i=0)
    r_yc = 30 + 3 * 70 + 35  # row 3's center (offset 2, i=1)
    assert f'<line x1="{pin_x - 6}" y1="{s1_yc}" x2="{pin_x}" y2="{s1_yc}" stroke="black" stroke-width="2"/>' in svg
    assert f'<line x1="60" y1="{s1_yc}" x2="{pin_x - 70}" y2="{s1_yc}" stroke="black"/>' in svg
    assert f'<line x1="{pin_x - 6}" y1="{r_yc}" x2="{pin_x}" y2="{r_yc}" stroke="black" stroke-width="2"/>' in svg
    assert f'<line x1="60" y1="{r_yc}" x2="{pin_x - 70}" y2="{r_yc}" stroke="black"/>' in svg
    # No separate vertical tap between S1's row and R's row is needed --
    # they land directly on their own real conditions' rows now.
    assert not re.search(rf'<line x1="{pin_x}" y1="{s1_yc}" x2="{pin_x}" y2="{r_yc}" stroke="blue"', svg)


def test_export_diagram_short_circuit_wraps_block_no_dogleg_without_a_shown_output():
    # The dogleg above is specific to a block with a shown output pin to
    # bridge from -- a block with none (e.g. only EN shown) has nothing to
    # dogleg, so none should be drawn.
    block = _block("B1", "TON", [_pin("EN", "input")], en_en_o=True)
    diagram = GraphicalDiagram(
        language="LD", objects=[block],
        grid_rows=[LadderGridRow(row=0, cells=[
            LadderGridCell(column=0, kind="short_circuit", width=2, wraps="block",
                           wrapped_width=2, wrapped_object_index=0),
        ])],
    )
    svg = LadderSvgExporter().export_diagram(diagram)
    # A vertical dogleg line would have identical x1/x2; none should exist
    # beyond the block's own rect border (a closed loop, not a line).
    assert not re.search(r'<line x1="(\d+)" y1="\d+" x2="\1" y2="\d+" stroke="black"', svg)


def test_export_diagram_short_circuit_connector_resolves_through_a_lone_vlink_chain():
    # Real evidence (sayahali_conveyor_ali_conv.zef, rows 12-14, confirmed
    # against the user's own rendered screenshot): a shortCircuit's target
    # row can itself be just a lone bare `VLink` pass-through (an
    # intermediate hop of a taller bus, here row 1), not a row with real
    # wire content -- its own raw grid column positions ITS OWN glyph in
    # the source grid but is not itself where the bus's wire actually
    # ends. Both the shortCircuit above the chain (row 0) and the lone
    # VLink row within it (row 1) must resolve all the way through to the
    # real wire-bearing row's own end column (row 2, ending at column 4),
    # landing as one continuous straight line -- not stopping at row 1's
    # own raw column (3), which only produces a shorter zigzag.
    diagram = GraphicalDiagram(
        language="LD", objects=[_contact("Gate")],
        grid_rows=[
            LadderGridRow(row=0, cells=[
                LadderGridCell(column=2, kind="short_circuit", width=2, wraps="hlink", wrapped_width=2),
            ]),
            LadderGridRow(row=1, cells=[LadderGridCell(column=3, kind="vlink")]),
            LadderGridRow(row=2, cells=[
                LadderGridCell(column=0, kind="hlink", width=3),
                LadderGridCell(column=3, kind="contact", object_index=0),
            ]),
        ],
    )
    svg = LadderSvgExporter().export_diagram(diagram)
    target_x = 60 + 4 * 70  # row 2's real wire end (column 4), not row 1's own raw column (3)
    assert svg.count(f'<line x1="{target_x}" y1="65" x2="{target_x}" y2="135"') == 1  # row 0 -> row 1
    assert svg.count(f'<line x1="{target_x}" y1="135" x2="{target_x}" y2="205"') == 1  # row 1 -> row 2
    assert f'<line x1="{60 + 3 * 70}" y1="135"' not in svg


def test_export_diagram_multi_tap_reset_bus_aligns_to_coils_and_reaches_the_last_one():
    # Real evidence (sayahali_conveyor_ali_conv.zef, rows 90-97 and again at
    # rows 78-81): a shortCircuit feeds a chain of rows where each row's
    # own VLink sits immediately next to that row's own resetCoil (VLink at
    # column 2, coil at column 3) -- a genuine tap into that row's own
    # wire, not a pass-through. The user caught two real bugs: (1) the
    # connector was landing at the row's far-right extent (past a trailing
    # HLink, at the right rail) instead of at the coil's own column, one
    # column over from the VLink's raw position. (2) An earlier attempt at
    # this fix stopped the bus one row short whenever the FINAL row had no
    # VLink of its own -- but that is exactly the evidenced shape of the
    # bus's own last coil in both real occurrences (row 97 / "M4_S2" here,
    # and again at row 81 / "M4_S1"): the previous row's own VLink feeds it
    # directly, with no VLink declared in the final row's own grid data at
    # all. The user caught this directly ("the vlink is missing from line
    # 96 to line 97 ... same case ... line 80 to line 81") -- a VLink
    # always continues exactly one row down, whether or not that row
    # happens to declare a VLink of its own.
    diagram = GraphicalDiagram(
        language="LD",
        objects=[_contact("ARRET_MOT"), _coil("M1_S1", kind="resetCoil"),
                 _coil("M1_S2", kind="resetCoil"), _coil("M4_S2", kind="resetCoil")],
        grid_rows=[
            LadderGridRow(row=0, cells=[
                LadderGridCell(column=1, kind="contact", object_index=0),
                LadderGridCell(column=2, kind="short_circuit", wraps="hlink", wrapped_width=1),
                LadderGridCell(column=3, kind="coil", object_index=1),
                LadderGridCell(column=4, kind="hlink", width=7),
            ]),
            LadderGridRow(row=1, cells=[
                LadderGridCell(column=2, kind="vlink"),
                LadderGridCell(column=3, kind="coil", object_index=2),
                LadderGridCell(column=4, kind="hlink", width=7),
            ]),
            # The bus's last coil: fed by row 1's own VLink, but declares
            # no VLink of its own -- the real evidenced final-row shape.
            LadderGridRow(row=2, cells=[
                LadderGridCell(column=3, kind="coil", object_index=3),
                LadderGridCell(column=4, kind="hlink", width=7),
            ]),
        ],
    )
    svg = LadderSvgExporter().export_diagram(diagram)
    coil_column_x = 60 + 3 * 70  # the coil's own column (3), not the VLink's raw column (2) or row end (11)
    assert svg.count(f'<line x1="{coil_column_x}" y1="65" x2="{coil_column_x}" y2="135"') == 1  # row 0 -> row 1
    assert svg.count(f'<line x1="{coil_column_x}" y1="135" x2="{coil_column_x}" y2="205"') == 1  # row 1 -> row 2
    assert 'x1="830"' not in svg  # never lands at the row's far-right extent past the trailing HLink
    # Two junction dots (row 0's shortCircuit tap, row 1's own tap) -- the
    # bus's own last coil (row 2) gets no dot of its own, since it declares
    # no VLink -- the line simply reaches it, matching the real fixture.
    assert svg.count(f'<circle cx="{coil_column_x}" cy="65" r="3" fill="blue"/>') == 1
    assert svg.count(f'<circle cx="{coil_column_x}" cy="135" r="3" fill="blue"/>') == 1
    assert f'<circle cx="{coil_column_x}" cy="205" r="3" fill="blue"/>' not in svg
    # A tap's dot sits at the SAME column as the coil it feeds on its own
    # row (real bug: a dot drawn BEFORE that coil's own lead-in line --
    # which spans its whole cell, starting at that same column -- gets
    # painted over and all but disappears). The dot must come after the
    # coil's own lead-in line in document order so it paints on top.
    coil_lead_in = f'<line x1="{coil_column_x}" y1="135" x2="{coil_column_x + 70}" y2="135" stroke="black"/>'
    tap_dot = f'<circle cx="{coil_column_x}" cy="135" r="3" fill="blue"/>'
    assert svg.index(coil_lead_in) < svg.index(tap_dot)


def test_export_diagram_unresolved_short_circuit_shape_renders_placeholder():
    diagram = GraphicalDiagram(
        language="LD", objects=[],
        grid_rows=[LadderGridRow(row=0, cells=[LadderGridCell(column=0, kind="short_circuit")])],
    )
    svg = LadderSvgExporter().export_diagram(diagram)
    assert "shortCircuit" in svg
    assert 'fill="#a00"' in svg


def test_export_diagram_is_deterministic():
    diagram = GraphicalDiagram(
        language="LD", objects=[_contact("A"), _coil("Out")],
        grid_rows=[LadderGridRow(row=0, cells=[
            LadderGridCell(column=0, kind="contact", object_index=0),
            LadderGridCell(column=3, kind="coil", object_index=1),
        ])],
    )
    exporter = LadderSvgExporter()
    assert exporter.export_diagram(diagram, title="x") == exporter.export_diagram(diagram, title="x")


def test_optional_real_sayahali_export_diagram_matches_confirmed_positions():
    # SR_2 (enEnO="false", shortCircuit-wrapped, real posY 21) renders at
    # the SAME offset (2) as every other enEnO=False block (SR_8/SR_9,
    # free-standing) -- an explicit product decision (see
    # test_export_diagram_en_en_o_false_block_offset_is_identical_free_
    # standing_or_wrapped), not a claim about the vendor's own rendering:
    # two reference renderings from the original PIL verification session
    # showed SR_2 one row shorter than SR_8/SR_9 for the identical block
    # type, and the user directly rejected that inconsistency. S1 and Q1
    # share row 23 (offset 2, i=0); R is on row 24 (i=1) -- one row below
    # the blank spacer row 22. capteur_2 (row 23) and capteur_3 (row 24)
    # now land on the SAME rows as S1 and R respectively, connecting via
    # ordinary same-row wiring, no separate vertical tap needed.
    # TON_23's IN lands on row 21 (posY 19 + 1 + 1), PT on row 22 --
    # enEnO="true" uses a different, unaffected offset. The SR_2.Q1 ->
    # TON_23.IN dogleg (corner in the middle of the one-cell gap) is
    # user-confirmed against this exact real fixture.
    path = Path("reference/control-expert/sayahali_conveyor_ali_conv.zef")
    if not path.exists():
        pytest.skip("Local sayahali/conveyor-automation reference unavailable")
    result, = parse_projects(capture_file(path))
    routine = result.controller.programs["prog"].main_routine
    assert routine is not None
    diagram = routine.graphical_diagrams[0]
    svg = LadderSvgExporter().export_diagram(diagram, title="prog")
    assert svg.startswith("<svg ") and svg.endswith("</svg>")
    assert "SR_2 (SR)" in svg
    assert "TON_23 (TON)" in svg
    assert "t#3s" in svg
    row_labels = {row: f'>{row}</text>' for row in (19, 20, 21, 22)}
    for row, marker in row_labels.items():
        assert marker in svg, f"row {row} label missing"

    def row_y(row: int) -> int:
        return 30 + (row - 1) * 70  # min_row is 1 (SR_8's own row)

    row21_center, row23_center, row24_center = (row_y(r) + 35 for r in (21, 23, 24))
    assert f'<text x="344" y="{row23_center + 4}">S1</text>' in svg
    assert f'<text x="476" y="{row23_center + 4}" text-anchor="end">Q1</text>' in svg
    assert f'<text x="344" y="{row24_center + 4}">R</text>' in svg

    sr2_left_edge = 60 + 4 * 70  # SR_2's own column (4)
    # No vertical tap needed -- S1/R land directly on capteur_2/capteur_3's
    # own rows.
    assert not re.search(
        rf'<line x1="{sr2_left_edge}" y1="{row23_center}" x2="{sr2_left_edge}" y2="{row24_center}" stroke="blue"',
        svg,
    )

    ton23_left_edge = 60 + 7 * 70  # TON_23's own column (7)
    corner_x = sr2_left_edge + 2 * 70 + 35  # SR_2's right edge (2 columns wide) + half the 1-cell gap
    assert f'<line x1="{corner_x}" y1="{row21_center}" x2="{corner_x}" y2="{row23_center}" ' \
           'stroke="black" stroke-width="2"/>' in svg
    assert f'<line x1="{sr2_left_edge + 2 * 70}" y1="{row21_center}" x2="{ton23_left_edge}" y2="{row21_center}" ' \
           'stroke="black"/>' in svg


def test_renders_iec_transition_contacts_and_negated_coil_with_their_marks():
    rung = _series_rung(
        0,
        (
            _instruction(LadderOperation.POSITIVE_TRANSITION_CONTACT, "Rise", 0, mnemonic="RisingEdge"),
            _instruction(LadderOperation.NEGATIVE_TRANSITION_CONTACT, "Fall", 2, mnemonic="FallingEdge"),
            _instruction(LadderOperation.NEGATED_COIL, "Out", 11, mnemonic="NegativeCoil"),
        ),
    )

    svg = LadderSvgExporter().export([rung])

    marks = re.findall(r'text-anchor="middle">([PN/])</text>', svg)
    assert marks == ["P", "N", "/"]
    # Drawn as real contacts and a coil, not the unsupported placeholder.
    assert 'fill="#a00"' not in svg
