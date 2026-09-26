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


def test_export_diagram_multi_tap_reset_bus_aligns_to_coils_and_stops_at_the_last_tap():
    # Real evidence (sayahali_conveyor_ali_conv.zef, rows 90-97, the
    # ARRET_MOT reset bus): a shortCircuit feeds a chain of rows where each
    # row's own VLink sits immediately next to that row's own resetCoil
    # (VLink at column 2, coil at column 3) -- a genuine tap into that
    # row's own wire, not a pass-through. The user caught two real bugs
    # here: (1) the connector was landing at the row's far-right extent
    # (past a trailing HLink, at the right rail) instead of at the coil's
    # own column, one column over from the VLink's raw position; (2) the
    # bus was drawn one row too far, into the final row (here row 2 /
    # "M4_S2"), which has no VLink of its own at all and isn't part of the
    # bus -- confirming a tap only continues downward if the next row
    # genuinely carries the bus onward.
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
            # The bus's last participating row: still a tap, but nothing
            # below it carries the VLink onward.
            LadderGridRow(row=2, cells=[
                LadderGridCell(column=3, kind="coil", object_index=3),
                LadderGridCell(column=4, kind="hlink", width=7),
            ]),
        ],
    )
    svg = LadderSvgExporter().export_diagram(diagram)
    coil_column_x = 60 + 3 * 70  # the coil's own column (3), not the VLink's raw column (2) or row end (11)
    assert svg.count(f'<line x1="{coil_column_x}" y1="65" x2="{coil_column_x}" y2="135"') == 1  # row 0 -> row 1
    assert 'x1="830"' not in svg  # never lands at the row's far-right extent past the trailing HLink
    # Two junction dots (row 0's shortCircuit tap, row 1's own tap) -- both
    # genuine taps, not pass-throughs.
    assert svg.count(f'<circle cx="{coil_column_x}" cy="65" r="3" fill="blue"/>') == 1
    assert svg.count(f'<circle cx="{coil_column_x}" cy="135" r="3" fill="blue"/>') == 1
    # No line descends from row 1 into row 2 -- row 2 has no VLink of its
    # own, so the bus stops at row 1's own tap.
    assert f'x2="{coil_column_x}" y2="205"' not in svg


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
    # Cross-checked directly against the confirmed real offsets from this
    # project's own ladder-rendering verification session: SR_2 (enEnO=
    # "false", shortCircuit-wrapped) spans exactly 3 rows (header, S1, R);
    # TON_23's IN lands on row 21 (posY 19 + 1 + 1), PT on row 22.
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
